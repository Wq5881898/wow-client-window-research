"""Read-only validation of the Markdown client knowledge base. No game imports."""
import re
import argparse
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / 'docs' / 'client-kb'
ISSUE = r'(?:OBS|ACT|CTL|NAV|NPC|TXN|REC|ACC|VER)-\d{2}'
LINK = re.compile(r'\[[^\]\n]*\]\(([^)\n]+)\)')


def body(text):
    """Ignore code examples when checking real links and issue definitions."""
    return re.sub(r'^```.*?^```[^\n]*$', '', text, flags=re.M | re.S)


def anchors(text):
    explicit = re.findall(r'<a\s+id=["\x27]([^"\x27]+)["\x27]', text)
    # GFM fallback anchors for headings. Current KB issue links use explicit IDs.
    headings = []
    counts = Counter()
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', body(text), re.M):
        slug = re.sub(r'[^\w\s\-\u4e00-\u9fff]', '', title.lower()).replace(' ', '-')
        count = counts[slug]
        counts[slug] += 1
        headings.append(slug if not count else f'{slug}-{count}')
    return set(explicit + headings)


def find(query):
    """Search the symptom index with literal, case-insensitive keywords."""
    terms = [term.casefold() for term in re.split(r'[\s|]+', query) if term]
    if not terms:
        print('Empty query: provide an issue ID or symptom keyword.')
        return 2
    matches = []
    for row in (KB / 'README.md').read_text(encoding='utf-8').splitlines():
        if not re.match(r'^\| ' + ISSUE + r' \|', row):
            continue
        fields = row.split('|')
        searchable = (fields[1] + ' ' + fields[2]).casefold()
        if any(term in searchable for term in terms):
            matches.append(row)
    print(f'Index matches: {len(matches)}')
    for row in matches:
        print(row)
    if not matches:
        print('No index match. Try fewer keywords, or search the topic Markdown files.')
    return 0 if matches else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--find', metavar='QUERY', help='Search symptom index; words separated by spaces or | use OR')
    args = parser.parse_args()
    if args.find is not None:
        return find(args.find)
    errors = []
    files = sorted(KB.glob('*.md'))
    if not (KB / 'README.md').is_file():
        print('FAIL: missing knowledge-base README')
        return 1
    index = (KB / 'README.md').read_text(encoding='utf-8')
    indexed = re.findall(r'^\| (' + ISSUE + r') \|', index, re.M)
    definitions = []
    checked = 0
    for source in files:
        text = source.read_text(encoding='utf-8')
        active = body(text)
        explicit = re.findall(r'<a\s+id=["\x27]([^"\x27]+)["\x27]', active)
        if len(explicit) != len(set(explicit)):
            errors.append(f'{source.name}: duplicate explicit anchors')
        for issue in re.findall(r'^## (' + ISSUE + r')[：:]', active, re.M):
            definitions.append(issue)
            if issue.lower() not in explicit:
                errors.append(f'{source.name}: missing issue anchor {issue}')
        for raw in LINK.findall(active):
            target = raw.strip('<>')
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            path = (source.parent / unquote(url.path)).resolve() if url.path else source
            checked += 1
            if not path.is_file():
                errors.append(f'{source.name}: missing target {target}')
            elif url.fragment:
                if path.suffix == '.md' and unquote(url.fragment) not in anchors(
                    path.read_text(encoding='utf-8')):
                    errors.append(f'{source.name}: missing anchor {target}')
    if not indexed or Counter(indexed) != Counter(definitions):
        errors.append('issue index and definitions differ')
    if len(indexed) != len(set(indexed)) or len(definitions) != len(set(definitions)):
        errors.append('duplicate issue IDs')
    for entry in ('README.md', '00_交接索引.md', 'docs/客户端实验指导手册.md', 'AGENTS.md'):
        if 'client-kb/README.md' not in (ROOT / entry).read_text(encoding='utf-8'):
            errors.append(f'missing entry link: {entry}')
    print(f'KB files: {len(files)}; unique issues: {len(set(indexed))}; local links: {checked}')
    for error in errors:
        print('ERROR:', error)
    print('FAIL' if errors else 'PASS (offline structure and local targets only)')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
