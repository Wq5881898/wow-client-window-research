"""Syntax and evidence inventory only: never imports or executes game drivers."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def decode(raw):
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')


def main():
    syntax_errors = []
    scripts = list((ROOT / 'scripts').glob('*.py'))
    for path in scripts:
        try:
            ast.parse(decode(path.read_bytes()), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            syntax_errors.append({'file': path.name, 'error': str(exc)})
    invalid = []
    count = 0
    for path in (ROOT / 'results').glob('*.json'):
        count += 1
        try:
            json.loads(decode(path.read_bytes()))
        except (ValueError, UnicodeError) as exc:
            invalid.append({'file': path.name, 'error': str(exc)})
    print(json.dumps({'python_files': len(scripts), 'syntax_errors': syntax_errors,
                      'json_files': count, 'invalid_json': invalid,
                      'scope': 'offline syntax; no game imports; evidence errors reported, not repaired'},
                     ensure_ascii=False, indent=2))
    return 1 if syntax_errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
