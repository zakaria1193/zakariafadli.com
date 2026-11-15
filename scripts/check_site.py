#!/usr/bin/env python3
"""Stdlib-only checker for the site/ folder: run by `make test`. Needs the network.

Checks, for every .html file under site/:
- it has a non-empty <title>;
- it has a viewport meta tag;
- every internal link (a/link href, img/script src) resolves to a real file;
- every external http/https link, stylesheet, image and script across the
  whole site (de-duplicated, preconnect/dns-prefetch hints excluded) fetches
  with a final 2xx response;
- titles and descriptions are unique across pages, each page has exactly one
  canonical/og:url/h1, OG/Twitter images are absolute and exist on disk, and
  every <img> has a non-empty alt;
- the home pages' JSON-LD holds a Person + ProfilePage whose facts are
  visible on the site;
- sitemap.xml, robots.txt and llms.txt / fr/llms.txt are valid and
  consistent with the pages on disk;
- _headers scopes its noindex rule to pages.dev hosts only.

Exits 1 and prints every problem found; exits 0 when the site is clean.
"""
import socket
import sys
import urllib.error
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SEARCH_CRAWLERS = [
    "Googlebot",
    "Bingbot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "Claude-SearchBot",
    "Claude-User",
]
TRAINING_CRAWLERS = ["GPTBot", "ClaudeBot", "Google-Extended", "CCBot", "Applebot-Extended"]
SITEMAP_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "xhtml": "http://www.w3.org/1999/xhtml"}

SITE = Path(__file__).resolve().parent.parent / "site"
LINK_ATTRS = {"a": "href", "link": "href", "img": "src", "script": "src"}
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel"}
SKIP_LINK_RELS = {"preconnect", "dns-prefetch"}
INTERNAL_HOSTS = {"zakariafadli.com", "www.zakariafadli.com"}
SITE_DOMAIN = "https://zakariafadli.com"
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
        self.html_lang = None
        self.alternates = {}  # hreflang -> href
        self.description = None
        self.canonicals = []
        self.og_url = None
        self.og_image = None
        self.twitter_image = None
        self.h1_count = 0
        self.img_alts = []  # list of alt values (possibly empty)
        self.json_ld = []  # list of raw <script type="application/ld+json"> text
        self.text_parts = []
        self._in_title = False
        self._in_json_ld = False
        self._skip_text_tags = {"script", "style"}
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.html_lang = attrs.get("lang")
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "img":
            self.img_alts.append(attrs.get("alt"))
        if tag == "meta" and attrs.get("name") == "viewport" and attrs.get("content"):
            self.has_viewport = True
        if tag == "meta" and attrs.get("name") == "description":
            self.description = attrs.get("content")
        if tag == "meta" and attrs.get("property") == "og:url":
            self.og_url = attrs.get("content")
        if tag == "meta" and attrs.get("property") == "og:image":
            self.og_image = attrs.get("content")
        if tag == "meta" and attrs.get("name") == "twitter:image":
            self.twitter_image = attrs.get("content")
        rels = (attrs.get("rel") or "").lower().split()
        if tag == "link" and "canonical" in rels and attrs.get("href"):
            self.canonicals.append(attrs["href"])
        if tag == "link" and "alternate" in rels and attrs.get("hreflang") and attrs.get("href"):
            self.alternates[attrs["hreflang"]] = attrs["href"]
        attr = LINK_ATTRS.get(tag)
        if attr and attrs.get(attr):
            skip_external = tag == "link" and any(r in SKIP_LINK_RELS for r in rels)
            self.links.append((attrs[attr], skip_external))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._in_json_ld = True
            self.json_ld.append("")
        if tag in self._skip_text_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_json_ld = False
        if tag in self._skip_text_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data
        if self._in_json_ld and self.json_ld:
            self.json_ld[-1] += data
        if self._skip_depth == 0:
            self.text_parts.append(data)


def resolve(link, page):
    """Return the file an internal link points to, or None if it is external/anchor-only.

    A link onto SITE_DOMAIN (e.g. hreflang alternates) is treated as internal too,
    resolved against site/ like a root-relative link, since those URLs are not live
    yet (see ## Edge cases in zakariafadli-com-0003).
    """
    split = urlsplit(link)
    if split.scheme in ("mailto", "tel") or link.startswith("//"):
        return None
    if split.netloc and split.netloc not in INTERNAL_HOSTS:
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


def twin_rel(rel):
    """Return the expected English<->French twin path for a page's path relative to SITE."""
    parts = rel.parts
    if parts[0] == "fr":
        return Path(*parts[1:])
    return Path("fr", *parts)


def url_of(rel):
    """Return the site-root-relative URL for a page's path relative to SITE."""
    parent = rel.parent
    if parent == Path("."):
        return "/"
    return "/" + parent.as_posix() + "/"


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


def check_jsonld(scan, rel, visible_text, problems):
    """Check the @graph JSON-LD on a home page: Person + ProfilePage, facts visible."""
    import json

    if not scan.json_ld:
        problems.append(f"{rel}: no JSON-LD script found")
        return
    try:
        data = json.loads(scan.json_ld[0])
    except json.JSONDecodeError as e:
        problems.append(f"{rel}: JSON-LD does not parse: {e}")
        return
    graph = data.get("@graph", [])
    person = next((n for n in graph if n.get("@type") == "Person"), None)
    profile = next((n for n in graph if n.get("@type") == "ProfilePage"), None)
    if person is None:
        problems.append(f"{rel}: JSON-LD @graph has no Person")
        return
    if profile is None:
        problems.append(f"{rel}: JSON-LD @graph has no ProfilePage")
        return
    if profile.get("mainEntity", {}).get("@id") != person.get("@id"):
        problems.append(f"{rel}: ProfilePage.mainEntity.@id does not match Person.@id")

    for field, value in (
        ("name", person.get("name")),
        ("worksFor.name", person.get("worksFor", {}).get("name")),
    ):
        if value and value not in visible_text:
            problems.append(f"{rel}: JSON-LD Person.{field} ({value!r}) not found in visible text")
    for school in person.get("alumniOf", []):
        name = school.get("name")
        if name and name not in visible_text:
            problems.append(f"{rel}: JSON-LD Person.alumniOf name ({name!r}) not found in visible text")


def check_sitemap(pages, problems):
    path = SITE / "sitemap.xml"
    if not path.exists():
        problems.append("sitemap.xml: missing")
        return
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        problems.append(f"sitemap.xml: does not parse as XML: {e}")
        return

    expected_canonicals = {SITE_DOMAIN + url_of(page.relative_to(SITE)) for page in pages}
    locs = set()
    for url_el in root.findall("s:url", SITEMAP_NS):
        loc_el = url_el.find("s:loc", SITEMAP_NS)
        if loc_el is None or not loc_el.text:
            problems.append("sitemap.xml: <url> with no <loc>")
            continue
        loc = loc_el.text.strip()
        locs.add(loc)
        split = urlsplit(loc)
        target = SITE / split.path.lstrip("/")
        if target.is_dir() or split.path.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            problems.append(f"sitemap.xml: <loc>{loc}</loc> does not resolve to a real file")
            continue
        rel = target.relative_to(SITE)
        is_fr = rel.parts[0] == "fr"
        twin = twin_rel(rel)
        en_rel, fr_rel = (twin, rel) if is_fr else (rel, twin)
        expected_alternates = {
            "en": SITE_DOMAIN + url_of(en_rel),
            "fr": SITE_DOMAIN + url_of(fr_rel),
            "x-default": SITE_DOMAIN + url_of(en_rel),
        }
        alternates = {
            link_el.get("hreflang"): link_el.get("href")
            for link_el in url_el.findall("xhtml:link", SITEMAP_NS)
            if link_el.get("hreflang") and link_el.get("href")
        }
        if alternates != expected_alternates:
            problems.append(
                f"sitemap.xml: {loc} hreflang alternates are {alternates}, expected {expected_alternates}"
            )

    if locs != expected_canonicals:
        problems.append(
            f"sitemap.xml: <loc> set {locs} does not equal canonical URL set {expected_canonicals}"
        )


def check_robots(problems):
    path = SITE / "robots.txt"
    if not path.exists():
        problems.append("robots.txt: missing")
        return
    text = path.read_text(encoding="utf-8")
    sitemap_line = f"Sitemap: {SITE_DOMAIN}/sitemap.xml"
    if sitemap_line not in text:
        problems.append(f"robots.txt: missing '{sitemap_line}'")

    rp = urllib.robotparser.RobotFileParser()
    rp.parse(text.splitlines())
    sitemap_url = f"{SITE_DOMAIN}/sitemap.xml"
    for agent in SEARCH_CRAWLERS:
        if not rp.can_fetch(agent, sitemap_url):
            problems.append(f"robots.txt: {agent} may not fetch the sitemap")

    allowed = {agent: rp.can_fetch(agent, SITE_DOMAIN + "/") for agent in TRAINING_CRAWLERS}
    if len(set(allowed.values())) != 1:
        problems.append(f"robots.txt: training crawlers are not uniformly allowed/disallowed: {allowed}")

    marker = "# AI training crawlers."
    marker_pos = text.find(marker)
    if marker_pos == -1:
        problems.append("robots.txt: missing the 'AI training crawlers' flag comment")
        return
    lines = text.splitlines()
    marker_line = next(i for i, line in enumerate(lines) if marker in line)
    directive_line = next(i for i in range(marker_line, len(lines)) if lines[i].strip() == "Allow: /")
    lines[directive_line] = "Disallow: /"
    flipped = "\n".join(lines)
    rp2 = urllib.robotparser.RobotFileParser()
    rp2.parse(flipped.splitlines())
    if not all(not rp2.can_fetch(agent, SITE_DOMAIN + "/") for agent in TRAINING_CRAWLERS):
        problems.append("robots.txt: flipping the first Allow:/Disallow: line does not disallow all training crawlers")
    if not all(rp2.can_fetch(agent, sitemap_url) for agent in SEARCH_CRAWLERS):
        problems.append("robots.txt: flipping the training flag also blocks a search/citation crawler")


def check_llms_txt(path, problems):
    if not path.exists():
        problems.append(f"{path.relative_to(SITE)}: missing")
        return
    text = path.read_text(encoding="utf-8")
    if not text.startswith("# "):
        problems.append(f"{path.relative_to(SITE)}: does not start with '# '")
    import re

    for link in re.findall(r"https://zakariafadli\.com/[^\s\)\]]*", text):
        split = urlsplit(link)
        target = SITE / split.path.lstrip("/")
        if target.is_dir() or split.path.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            problems.append(f"{path.relative_to(SITE)}: link '{link}' does not resolve to a real page")


def check_headers_file(problems):
    path = SITE / "_headers"
    if not path.exists():
        problems.append("_headers: missing")
        return
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("#")]
    host_lines = [line.strip() for line in lines if line.strip() and not line.startswith((" ", "\t"))]
    if not host_lines:
        problems.append("_headers: no rule host lines found")
    for host_line in host_lines:
        if "pages.dev" not in host_line:
            problems.append(f"_headers: rule host {host_line!r} is not scoped to pages.dev")
        if "zakariafadli.com" in host_line and "pages.dev" not in host_line:
            problems.append(f"_headers: rule host {host_line!r} targets the apex, not pages.dev")


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
    titles = {}
    descriptions = {}
    page_text = {}
    home_scans = {}
    for page in pages:
        scan = PageScan()
        scan.feed(page.read_text(encoding="utf-8"))
        rel = page.relative_to(SITE)
        if not scan.title or not scan.title.strip():
            problems.append(f"{rel}: missing or empty <title>")
        else:
            titles.setdefault(scan.title.strip(), []).append(rel)
        if not scan.has_viewport:
            problems.append(f"{rel}: missing viewport meta tag")

        if not scan.description or not scan.description.strip():
            problems.append(f"{rel}: missing or empty meta description")
        else:
            descriptions.setdefault(scan.description.strip(), []).append(rel)

        own_canonical = SITE_DOMAIN + url_of(rel)
        if len(scan.canonicals) != 1:
            problems.append(f"{rel}: expected exactly one canonical, found {len(scan.canonicals)}")
        elif scan.canonicals[0] != own_canonical:
            problems.append(f"{rel}: canonical is {scan.canonicals[0]!r}, expected {own_canonical!r}")
        if scan.og_url != own_canonical:
            problems.append(f"{rel}: og:url is {scan.og_url!r}, expected {own_canonical!r}")
        for label, image in (("og:image", scan.og_image), ("twitter:image", scan.twitter_image)):
            if not image or not image.startswith(SITE_DOMAIN + "/"):
                problems.append(f"{rel}: {label} ({image!r}) is not an absolute {SITE_DOMAIN}/... URL")
                continue
            image_path = SITE / urlsplit(image).path.lstrip("/")
            if not image_path.exists():
                problems.append(f"{rel}: {label} points at {image_path}, which does not exist")

        if scan.h1_count != 1:
            problems.append(f"{rel}: expected exactly one <h1>, found {scan.h1_count}")
        for alt in scan.img_alts:
            if not alt or not alt.strip():
                problems.append(f"{rel}: <img> with missing or empty alt text")

        page_text[rel] = "".join(scan.text_parts)
        if rel in (Path("index.html"), Path("fr/index.html")):
            home_scans[rel] = scan

        is_fr = rel.parts[0] == "fr"
        expected_lang = "fr" if is_fr else "en"
        if scan.html_lang != expected_lang:
            problems.append(f"{rel}: <html lang> is {scan.html_lang!r}, expected {expected_lang!r}")

        twin = twin_rel(rel)
        if not (SITE / twin).exists():
            problems.append(f"{rel}: no {'English' if is_fr else 'French'} twin at site/{twin}")

        en_rel, fr_rel = (twin, rel) if is_fr else (rel, twin)
        en_url = SITE_DOMAIN + url_of(en_rel)
        fr_url = SITE_DOMAIN + url_of(fr_rel)
        expected_alternates = {"en": en_url, "fr": fr_url, "x-default": en_url}
        if scan.alternates != expected_alternates:
            problems.append(
                f"{rel}: hreflang alternates are {scan.alternates}, expected {expected_alternates}"
            )

        for link, skip_external in scan.links:
            target = resolve(link, page)
            if target is not None and not target.exists():
                problems.append(f"{rel}: broken link '{link}' -> {target}")
            if target is None and not skip_external:
                split = urlsplit(link)
                if split.scheme in ("http", "https"):
                    url_pages.setdefault(strip_fragment(link), set()).add(str(rel))

    for home_rel, scan in home_scans.items():
        cv_rel = Path("fr/cv/index.html") if home_rel.parts[0] == "fr" else Path("cv/index.html")
        combined_text = page_text.get(home_rel, "") + page_text.get(cv_rel, "")
        check_jsonld(scan, home_rel, combined_text, problems)

    for title, rels in titles.items():
        if len(rels) > 1:
            problems.append(f"title {title!r} is reused by {rels}")
    for desc, rels in descriptions.items():
        if len(rels) > 1:
            problems.append(f"meta description {desc!r} is reused by {rels}")

    check_sitemap(pages, problems)
    check_robots(problems)
    check_llms_txt(SITE / "llms.txt", problems)
    check_llms_txt(SITE / "fr" / "llms.txt", problems)
    check_headers_file(problems)

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
