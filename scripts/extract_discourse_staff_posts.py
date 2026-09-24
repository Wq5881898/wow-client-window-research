#!/usr/bin/env python3
"""Extract staff-authored posts from an archived Discourse topic JSON file."""

from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class VisibleTextParser(HTMLParser):
    BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "h4", "li", "ol", "p", "section", "ul"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return "\n".join(
            line for raw in "".join(self.parts).replace("\xa0", " ").splitlines()
            if (line := " ".join(raw.split()))
        )


def staff_posts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        post for post in payload["post_stream"]["posts"]
        if post.get("staff") is True
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    sections = [
        f"Topic: {payload.get('title', '')}",
        f"Topic created: {payload.get('created_at', '')}",
        f"Staff posts extracted: {len(staff_posts(payload))}",
    ]
    for post in staff_posts(payload):
        document = VisibleTextParser()
        document.feed(post["cooked"])
        sections.extend(
            [
                "",
                f"--- post {post['post_number']} | {post['username']} | {post['created_at']} ---",
                document.text(),
            ]
        )
    text = "\n".join(sections).rstrip() + "\n"
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"Extracted {len(staff_posts(payload))} staff posts to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
