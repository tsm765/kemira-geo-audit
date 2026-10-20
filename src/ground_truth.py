"""S2: ground truth capture.

Fetches every source in sources.yaml and stores, under data/ground_truth/<id>/:

    raw.html   unmodified response body
    text.md    readable main-content text (nav, header, footer stripped)
    meta.json  fetch metadata plus page-structure signals for the S7 page-gap check

Sources with a local PDF named data/ground_truth/<id>_*.pdf also get their PDF
extracted with page markers. For those, text.md is the PDF text and the HTML
landing page's text goes to page.md.

Sources whose url is itself a PDF are not downloaded when the local copy exists;
the local file is extracted and its hash recorded.

Run before any assistant answers exist:

    python -m src.ground_truth          # all sources; sets captured_at
    python -m src.ground_truth S22      # only the listed sources

Behaviour on kemira.com: honest user agent, robots.txt respected, one request
at a time with a fixed delay, no retries, no links followed beyond sources.yaml.
"""

import hashlib
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from pypdf import PdfReader

from src import config

GROUND_TRUTH_DIR = config.ROOT / "data" / "ground_truth"

USER_AGENT = (
    "KemiraGEOAudit/1.0 (independent portfolio audit of how AI assistants describe Kemira; "
    "+https://github.com/tsm765/kemira-geo-audit)"
)
REQUEST_DELAY_SECONDS = 5
TIMEOUT_SECONDS = 30

# Where each local PDF was downloaded from. Recorded in meta.json so the
# committed text points back at Kemira's public copy, not ours.
PDF_SOURCE_URLS = {
    "S17": "https://www.kemira.com/app/uploads/2026/02/kemira-full-annual-report-2025.pdf",
}

# Below this many characters of main-content text, a page is flagged as thin.
THIN_TEXT_CHARS = 800

BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre",
              "tr", "dt", "dd", "figcaption", "summary"}
STRIP_EVERYWHERE = ["script", "style", "noscript", "template", "svg", "iframe", "form"]
STRIP_LAYOUT = ["nav", "footer", "aside"]
CHROME_PATTERN = re.compile(r"cookie|consent|breadcrumb|skip-link|screen-reader", re.I)
FAQ_TEXT = re.compile(r"\bFAQs?\b|frequently asked", re.I)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


def _sha256(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


# ---- robots.txt ----------------------------------------------------------

class Robots:
    """robots.txt per host, fetched once each."""

    def __init__(self, session):
        self.session = session
        self.hosts = {}  # netloc -> (parser or None, crawl_delay, note)

    def _for(self, url):
        parts = urlparse(url)
        if parts.netloc not in self.hosts:
            self.hosts[parts.netloc] = _load_robots(self.session, f"{parts.scheme}://{parts.netloc}")
            print(f"{parts.netloc}: {self.hosts[parts.netloc][2]}")
        return self.hosts[parts.netloc]

    def can_fetch(self, url):
        parser, _, _ = self._for(url)
        return parser is not None and parser.can_fetch(USER_AGENT, url)

    def delay(self, url):
        _, crawl_delay, _ = self._for(url)
        return max(REQUEST_DELAY_SECONDS, crawl_delay or 0)


def _load_robots(session, origin):
    """Returns (parser, crawl_delay, note). Parser is None if fetching must stop."""
    robots_url = f"{origin}/robots.txt"
    parser = RobotFileParser(robots_url)
    try:
        resp = session.get(robots_url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        return None, None, f"robots.txt unreachable ({exc}); not fetching"
    if resp.status_code >= 500:
        return None, None, f"robots.txt returned {resp.status_code}; not fetching"
    if resp.status_code >= 400:
        parser.parse([])  # no robots.txt means no restrictions
        return parser, None, f"robots.txt returned {resp.status_code}; treated as allow-all"
    parser.parse(resp.text.splitlines())
    return parser, parser.crawl_delay(USER_AGENT), f"robots.txt {resp.status_code}"


# ---- HTML analysis -------------------------------------------------------

def _schema_types(soup):
    json_ld, microdata, rdfa, errors = set(), set(), set(), []

    def collect(node):
        if isinstance(node, dict):
            t = node.get("@type")
            for item in (t if isinstance(t, list) else [t]):
                if isinstance(item, str):
                    json_ld.add(item.rsplit("/", 1)[-1])
            for v in node.values():
                collect(v)
        elif isinstance(node, list):
            for v in node:
                collect(v)

    for i, script in enumerate(soup.find_all("script", type=re.compile(r"application/ld\+json", re.I))):
        try:
            collect(json.loads(script.string or script.get_text() or "", strict=False))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON-LD block {i + 1}: {exc}")

    for el in soup.find_all(attrs={"itemtype": True}):
        for t in el["itemtype"].split():
            microdata.add(t.rstrip("/").rsplit("/", 1)[-1])
    for el in soup.find_all(attrs={"typeof": True}):
        for t in el["typeof"].split():
            rdfa.add(t.rsplit(":", 1)[-1].rsplit("/", 1)[-1])

    detail = {"json_ld": sorted(json_ld), "microdata": sorted(microdata), "rdfa": sorted(rdfa)}
    if errors:
        detail["parse_errors"] = errors
    return sorted(json_ld | microdata | rdfa), detail


def _clean(soup):
    for tag in soup.find_all(STRIP_EVERYWHERE):
        tag.decompose()
    for tag in soup.find_all(STRIP_LAYOUT):
        tag.decompose()
    for tag in soup.find_all(attrs={"role": re.compile(r"navigation|contentinfo", re.I)}):
        tag.decompose()
    for tag in soup.find_all(True):
        if tag.attrs is None or tag.name in ("html", "body", "main"):
            continue
        ident = " ".join([tag.get("id") or ""] + (tag.get("class") or []))
        if ident and CHROME_PATTERN.search(ident):
            tag.decompose()
    return soup


def _main_root(soup):
    """Pick the main-content element. Returns (element, how it was found)."""
    for selector, label in [("main", "<main>"), ("[role=main]", "role=main"),
                            ("article", "<article>"), ("#content", "#content"),
                            (".entry-content", ".entry-content")]:
        el = soup.select_one(selector)
        if el and _norm(el.get_text(" ")):
            return el, label
    body = soup.body or soup
    for tag in body.find_all("header"):
        tag.decompose()
    return body, "<body> minus <header>"


def _has_direct_text(el):
    return any(isinstance(c, NavigableString) and c.strip() for c in el.children)


def _blocks(root):
    """Ordered (tag, text) content blocks, without nesting duplicates."""
    out = []

    def walk(el):
        for child in el.children:
            if not isinstance(child, Tag):
                continue
            if child.name in BLOCK_TAGS or (child.name == "div" and _has_direct_text(child)):
                text = _norm(child.get_text(" "))
                if text:
                    out.append((child.name, text))
            else:
                walk(child)

    walk(root)
    return out


def _to_markdown(blocks):
    lines = []
    for tag, text in blocks:
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lines.append("#" * int(tag[1]) + " " + text)
        elif tag == "li":
            lines.append("- " + text)
        elif tag == "blockquote":
            lines.append("> " + text)
        elif tag == "tr":
            lines.append("| " + text + " |")
        else:
            lines.append(text)
    return "\n\n".join(lines) + "\n"


def _faq(cleaned, schema_types):
    detected = []
    if "FAQPage" in schema_types:
        detected.append("schema: FAQPage")
    for h in cleaned.find_all(["h1", "h2", "h3", "h4"]):
        text = _norm(h.get_text(" "))
        if FAQ_TEXT.search(text):
            detected.append(f"heading: {text}")
    for el in cleaned.find_all(True):
        if el.name in ("html", "body"):
            continue
        ident = " ".join([el.get("id") or ""] + (el.get("class") or []))
        if re.search(r"faq", ident, re.I):
            detected.append(f"markup: <{el.name}> id/class '{_norm(ident)}'")
            break
    details = cleaned.find_all("details")
    if len(details) >= 2:
        detected.append(f"markup: {len(details)} <details>/<summary> items")
    accordions = cleaned.find_all(class_=re.compile(r"accordion", re.I))
    signals = [f"{len(accordions)} accordion elements (not counted as FAQ on their own)"] if accordions else []
    return {"present": bool(detected), "detected_by": detected, "other_signals": signals}


def _js_signals(soup, text_chars):
    flags = []
    body = soup.body
    if body is not None:
        for app_id in ("root", "app", "__next", "__nuxt"):
            el = body.find(id=app_id)
            if el is not None and not _norm(el.get_text(" ")):
                flags.append(f"empty #{app_id} container (possible client-side rendering)")
        for ns in soup.find_all("noscript"):
            if re.search(r"enable javascript", ns.get_text(" "), re.I):
                flags.append("noscript asks to enable JavaScript")
                break
    if text_chars < THIN_TEXT_CHARS:
        flags.append(f"thin: {text_chars} characters of main-content text")
    return flags


def analyse_html(html):
    raw = BeautifulSoup(html, "html.parser")
    schema_types, schema_detail = _schema_types(raw)
    js_flags_soup = BeautifulSoup(html, "html.parser")

    cleaned = _clean(BeautifulSoup(html, "html.parser"))
    headings = [{"level": int(h.name[1]), "text": _norm(h.get_text(" "))}
                for h in cleaned.find_all(["h1", "h2", "h3"]) if _norm(h.get_text(" "))]
    faq = _faq(cleaned, schema_types)

    root, root_how = _main_root(cleaned)
    blocks = _blocks(root)
    markdown = _to_markdown(blocks)
    text_chars = sum(len(t) for _, t in blocks)

    first_blocks = [{"tag": tag, "text": text} for tag, text in blocks if tag != "h1"][:3]

    return markdown, {
        "main_content_from": root_how,
        "text_chars": text_chars,
        "flags": _js_signals(js_flags_soup, text_chars),
        "direct_answer": {
            "first_blocks": first_blocks,
            "judgment": None,
            "note": "First three content blocks after the h1, verbatim. Judgment left to a human.",
        },
        "faq_block": faq,
        "schema_types": schema_types,
        "schema_detail": schema_detail,
        "headings": headings,
    }


# ---- PDF ------------------------------------------------------------------

def _is_pdf_url(url):
    return urlparse(url).path.lower().endswith(".pdf")


def extract_pdf(source_id, pdf_path, out_path, source_url=None):
    reader = PdfReader(str(pdf_path))
    labels = list(reader.page_labels) if reader.page_labels else []
    lines = [
        f"# {source_id} — extracted PDF text",
        "",
        f"Source: {source_url or 'unrecorded'}",
        f"Pages: {len(reader.pages)}. Each page starts with a marker giving the PDF page "
        "number and, where the PDF defines one, the printed page label. Cite as "
        f"`{source_id} p.<PDF page>`.",
        "",
    ]
    empty_pages = []
    for i, page in enumerate(reader.pages, start=1):
        label = labels[i - 1] if i - 1 < len(labels) else str(i)
        text = (page.extract_text() or "").strip()
        if not text:
            empty_pages.append(i)
        lines.append(f"<!-- page {i} | printed {label} -->")
        lines.append(f"## Page {i} (printed: {label})")
        lines.append("")
        lines.append(text or "_[no extractable text on this page]_")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "file": pdf_path.name,
        "source_url": source_url,
        "sha256": _sha256(pdf_path.read_bytes()),
        "pages": len(reader.pages),
        "pages_without_text": empty_pages,
        "extracted_at": _now(),
        "text_file": out_path.name,
    }


# ---- Fetch ----------------------------------------------------------------

def _fetch(session, url):
    resp = session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True)
    return resp, {
        "http_status": resp.status_code,
        "final_url": resp.url,
        "redirects": [{"status": r.status_code, "url": r.url} for r in resp.history],
        "content_type": resp.headers.get("Content-Type"),
        "bytes": len(resp.content),
        "content_hash": _sha256(resp.content),
    }


def capture_source(session, robots, source, interim_date):
    sid, url = source["id"], source["url"]
    out_dir = GROUND_TRUTH_DIR / sid
    out_dir.mkdir(parents=True, exist_ok=True)
    local_pdfs = sorted(GROUND_TRUTH_DIR.glob(f"{sid}_*.pdf"))

    captured_at = _now()
    meta = {
        "id": sid,
        "url": url,
        "captured_at": captured_at,
        "captured_relative_to_interim_report": (
            "before" if datetime.fromisoformat(captured_at).date() < interim_date else "on_or_after"
        ),
        "error": None,
    }
    if source.get("canonical_host"):
        meta["canonical_host"] = source["canonical_host"]

    fetched = False
    pdf_url = url if _is_pdf_url(url) else PDF_SOURCE_URLS.get(sid)
    if _is_pdf_url(url) and local_pdfs:
        meta["fetch"] = "skipped: url is a PDF and a local copy exists; local copy extracted"
    elif not robots.can_fetch(url):
        meta["robots_allowed"] = False
        meta["error"] = "disallowed by robots.txt; not fetched"
    else:
        meta["robots_allowed"] = True
        try:
            resp, fetch_meta = _fetch(session, url)
            fetched = True
            meta.update(fetch_meta)
            (out_dir / "raw.html").write_bytes(resp.content)
            if resp.status_code != 200:
                meta["error"] = f"HTTP {resp.status_code}"
            elif "html" not in (resp.headers.get("Content-Type") or "").lower():
                meta["error"] = f"not HTML ({resp.headers.get('Content-Type')}); no text extracted"
            else:
                markdown, analysis = analyse_html(resp.content)
                text_name = "page.md" if local_pdfs else "text.md"
                (out_dir / text_name).write_text(markdown, encoding="utf-8")
                meta["page_text_file"] = text_name
                meta.update(analysis)
        except requests.RequestException as exc:
            meta["error"] = f"{type(exc).__name__}: {exc}"

    if local_pdfs:
        meta["pdf"] = extract_pdf(sid, local_pdfs[0], out_dir / "text.md", pdf_url)

    write_meta(out_dir, meta)
    return meta, fetched


# ---- meta.json / meta.local.json --------------------------------------------
# meta.json is published and must carry no text from Kemira's pages.
# Page text (first content blocks, heading text, FAQ match text) goes to
# meta.local.json, which stays out of git.

LOCAL_KEYS = ("direct_answer", "headings")


def _faq_method(detail):
    if detail.startswith("schema:"):
        return detail  # e.g. "schema: FAQPage"
    if detail.startswith("heading:"):
        return "heading"
    if "<details>" in detail:
        return "markup: details/summary"
    return "markup: faq id/class"


def split_meta(meta):
    """Split a full meta dict into (public, local)."""
    public = {k: v for k, v in meta.items() if k not in LOCAL_KEYS and k != "faq_block"}
    local = {"id": meta["id"]}

    headings = meta.get("headings")
    if headings is not None:
        by_level = {f"h{n}": sum(1 for h in headings if h["level"] == n) for n in (1, 2, 3)}
        public["headings"] = {
            "count": len(headings),
            "by_level": by_level,
            "max_depth": max((h["level"] for h in headings), default=0),
        }
        local["headings"] = headings
    if "direct_answer" in meta:
        local["direct_answer"] = meta["direct_answer"]

    faq = meta.get("faq_block")
    if faq is not None:
        public["faq_block"] = {
            "present": faq["present"],
            "detected_by": sorted({_faq_method(d) for d in faq["detected_by"]}),
        }
        local["faq_block"] = faq
    return public, local


def write_meta(out_dir, meta):
    public, local = split_meta(meta)
    (out_dir / "meta.json").write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "meta.local.json").write_text(json.dumps(local, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_meta(out_dir):
    """Full meta for one source: public fields, with local page-text fields merged over them."""
    meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    local_path = out_dir / "meta.local.json"
    if local_path.exists():
        meta.update(json.loads(local_path.read_text(encoding="utf-8")))
    return meta


def _set_captured_at(run_date):
    text = config.SOURCES_FILE.read_text(encoding="utf-8")
    new, n = re.subn(r"(?m)^captured_at:[^\n#]*?(\s*#.*)?$",
                     lambda m: f"captured_at: {run_date.isoformat()}{m.group(1) or ''}", text, count=1)
    if n != 1:
        raise RuntimeError("could not find captured_at line in sources.yaml")
    config.SOURCES_FILE.write_text(new, encoding="utf-8")


def main(argv):
    cfg = config.load()
    sources = cfg.sources["sources"]
    if argv:
        unknown = set(argv) - {s["id"] for s in sources}
        if unknown:
            print(f"Unknown source id(s): {', '.join(sorted(unknown))}")
            return 1
        sources = [s for s in sources if s["id"] in argv]
    interim = cfg.sources.get("interim_report_published")
    interim_date = interim if isinstance(interim, date) else date.fromisoformat(str(interim))

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    robots = Robots(session)

    results = []
    for i, source in enumerate(sources):
        meta, fetched = capture_source(session, robots, source, interim_date)
        delay = robots.delay(source["url"]) if fetched else 0
        results.append(meta)
        status = meta.get("http_status", "-")
        flags = "; ".join(meta.get("flags", []))
        print(f"{meta['id']:4} {status!s:4} {meta.get('text_chars', 0):6} chars  "
              f"{'ERROR ' + meta['error'] if meta['error'] else ''}{flags}")
        if fetched and i < len(sources) - 1:
            time.sleep(delay)

    failures = [m for m in results if m["error"]]
    print(f"\n{len(results)} sources, {len(failures)} with errors.")
    if not argv:
        _set_captured_at(datetime.now(timezone.utc).date())
        print("captured_at set in sources.yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
