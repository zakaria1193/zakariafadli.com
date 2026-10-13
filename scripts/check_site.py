#!/usr/bin/env python3
"""Stdlib-only checker for the site/ folder: run by `make test`.

Checks, for every .html file under site/:
- it has a non-empty <title>;
- it has a viewport meta tag;
- every internal link (a/link href, img/script src) resolves to a real file.

Exits 1 and prints every problem found; exits 0 when the site is clean.
"""
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

SITE = Path(__file__).resolve().parent.parent / "site"
LINK_ATTRS = {"a": "href", "link": "href", "img": "src", "script": "src"}
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel"}


class PageScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self.has_viewport = False
        self.links = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta" and attrs.get("name") == "viewport" and attrs.get("content"):
            self.has_viewport = True
        attr = LINK_ATTRS.get(tag)
        if attr and attrs.get(attr):
            self.links.append(attrs[attr])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data


def resolve(link, page):
    """Return the file an internal link points to, or None if it is external/anchor-only."""
    split = urlsplit(link)
    if split.scheme in EXTERNAL_SCHEMES or link.startswith("//"):
        return None
    path = split.path
    if not path:
        return None  # same-page anchor or query only
    if path.startswith("/"):
        target = SITE / path.lstrip("/")
    else:
        target = page.parent / path
    if target.is_dir() or path.endswith("/"):
        target = target / "index.html"
    return target


def main():
    problems = []
    pages = sorted(SITE.rglob("*.html"))
    if not pages:
        problems.append("no .html files found under site/")
    for page in pages:
        scan = PageScan()
        scan.feed(page.read_text(encoding="utf-8"))
        rel = page.relative_to(SITE)
        if not scan.title or not scan.title.strip():
            problems.append(f"{rel}: missing or empty <title>")
        if not scan.has_viewport:
            problems.append(f"{rel}: missing viewport meta tag")
        for link in scan.links:
            target = resolve(link, page)
            if target is not None and not target.exists():
                problems.append(f"{rel}: broken link '{link}' -> {target}")

    if problems:
        print("site check failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"site check passed ({len(pages)} page(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
