#!/usr/bin/env python3
"""Extract the visible body of a Blizzard legal document from archived HTML."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path


class LegalDocumentParser(HTMLParser):
    BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "h4", "li", "ol", "p", "section", "ul"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = dict(attrs).get("class", "") or ""
        if self.depth == 0 and "legalDocContent" in classes.split():
            self.depth = 1
            return
        if self.depth:
            self.depth += 1
            if tag in self.BLOCK_TAGS:
                self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")
        self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.parts.append(data)

    def text(self) -> str:
        lines = []
        for line in "".join(self.parts).replace("\xa0", " ").splitlines():
            normalized = " ".join(line.split())
            if normalized and (not lines or normalized != lines[-1]):
                lines.append(normalized)
        return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    document = LegalDocumentParser()
    document.feed(args.input.read_text(encoding="utf-8"))
    text = document.text()
    if not text.strip():
        raise SystemExit("legalDocContent was not found or was empty")
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"Extracted {len(text)} characters to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
