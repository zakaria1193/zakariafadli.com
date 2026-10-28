#!/usr/bin/env python3
"""Stdlib-only checker for the site/ folder: run by `make test`. Needs the network.

Checks, for every .html file under site/:
- it has a non-empty <title>;
- it has a viewport meta tag;
- every internal link (a/link href, img/script src) resolves to a real file;
- every external http/https link, stylesheet, image and script across the
  whole site (de-duplicated, preconnect/dns-prefetch hints excluded) fetches
  with a final 2xx response.

Exits 1 and prints every problem found; exits 0 when the site is clean.
"""
import socket
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SITE = Path(__file__).resolve().parent.parent / "site"
LINK_ATTRS = {"a": "href", "link": "href", "img": "src", "script": "src"}
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel"}
SKIP_LINK_RELS = {"preconnect", "dns-prefetch"}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 15
RETRY_STATUSES = {403, 405, 501}

# Every page the old zakaria1193.github.io site served (its React router paths),
# mapped to where it now lives under site/. See README.md's page map.
OLD_PAGES = {
    "/": "index.html",
    "/cv": "cv/index.html",
    "/learning": "learning/index.html",
}


class PageScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self.has_viewport = False
        self.links = []  # list of (link, skip_external)
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta" and attrs.get("name") == "viewport" and attrs.get("content"):
            self.has_viewport = True
        attr = LINK_ATTRS.get(tag)
        if attr and attrs.get(attr):
            rels = (attrs.get("rel") or "").lower().split()
            skip_external = tag == "link" and any(r in SKIP_LINK_RELS for r in rels)
            self.links.append((attrs[attr], skip_external))

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


def strip_fragment(url):
    split = urlsplit(url)
    return urlunsplit((split.scheme, split.netloc, split.path, split.query, ""))


def _request(url, method):
    """Return (status, error). error is None on a response, even a non-2xx one."""
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        return None, str(e)


def _request_with_retry(url, method):
    """One retry of the same method on timeout/connection error."""
    status, err = _request(url, method)
    if err is not None:
        status, err = _request(url, method)
    return status, err


def check_url(url):
    """Return None if url's final response is 2xx, else an error string."""
    status, err = _request_with_retry(url, "HEAD")
    if err is not None:
        return err
    if status in RETRY_STATUSES:
        status, err = _request_with_retry(url, "GET")
        if err is not None:
            return err
    if status is not None and 200 <= status < 300:
        return None
    return f"HTTP {status}"


def check_external_links(url_pages):
    """url_pages: {url: {page_rel, ...}}. Returns a list of problem strings."""
    problems = []
    if not url_pages:
        return problems
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(url_pages, pool.map(check_url, url_pages)))
    for url, error in results.items():
        if error is None:
            continue
        for rel in sorted(url_pages[url]):
            problems.append(f"{rel}: broken external link '{url}' -> {error}")
    return problems


def main():
    problems = []
    pages = sorted(SITE.rglob("*.html"))
    if not pages:
        problems.append("no .html files found under site/")

    for old_path, new_path in OLD_PAGES.items():
        if not (SITE / new_path).exists():
            problems.append(f"old page '{old_path}' has no new page at site/{new_path}")

    url_pages = {}
    for page in pages:
        scan = PageScan()
        scan.feed(page.read_text(encoding="utf-8"))
        rel = page.relative_to(SITE)
        if not scan.title or not scan.title.strip():
            problems.append(f"{rel}: missing or empty <title>")
        if not scan.has_viewport:
            problems.append(f"{rel}: missing viewport meta tag")
        for link, skip_external in scan.links:
            target = resolve(link, page)
            if target is not None and not target.exists():
                problems.append(f"{rel}: broken link '{link}' -> {target}")
            if target is None and not skip_external:
                split = urlsplit(link)
                if split.scheme in ("http", "https"):
                    url_pages.setdefault(strip_fragment(link), set()).add(str(rel))

    problems.extend(check_external_links(url_pages))

    if problems:
        print("site check failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"site check passed ({len(pages)} page(s), {len(url_pages)} external link(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
