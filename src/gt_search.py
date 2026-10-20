"""Search the ground truth store for S5 adjudication.

    python -m src.gt_search "regex" [more regexes...] [--sources S17,S22] [--context 300]

Searches the extracted text of every source in data/ground_truth/ (text.md, and
page.md for S17) for each pattern, case-insensitive. Prints source id, file,
PDF page (for PDF sources, from the page markers) and the surrounding text, so a
passage can be cited as "S17 p.12". Read-only; never fetches anything.
"""

import argparse
import re
import sys

from src import config

GT = config.ROOT / "data" / "ground_truth"
PAGE_MARK = re.compile(r"<!-- page (\d+) \| printed ([^ ]+) -->")


def _pages(text):
    """[(offset, pdf_page, printed_label)] for a PDF text file; empty for web pages."""
    return [(m.start(), int(m.group(1)), m.group(2)) for m in PAGE_MARK.finditer(text)]


def _page_at(pages, offset):
    current = None
    for start, page, label in pages:
        if start > offset:
            break
        current = (page, label)
    return current


def search(patterns, sources=None, context=300, limit=12):
    hits = []
    for d in sorted(p for p in GT.iterdir() if p.is_dir()):
        if sources and d.name not in sources:
            continue
        for name in ("text.md", "page.md"):
            f = d / name
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8")
            pages = _pages(text)
            for pat in patterns:
                for m in re.finditer(pat, text, re.I):
                    a, b = max(0, m.start() - context), min(len(text), m.end() + context)
                    snippet = re.sub(r"\s+", " ", text[a:b]).strip()
                    page = _page_at(pages, m.start()) if pages else None
                    hits.append((d.name, name, page, pat, snippet))
    return hits


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("patterns", nargs="+")
    ap.add_argument("--sources", help="comma-separated source ids, e.g. S17,S22")
    ap.add_argument("--context", type=int, default=300)
    ap.add_argument("--limit", type=int, default=8, help="max hits per source file")
    args = ap.parse_args(argv)
    sources = set(args.sources.split(",")) if args.sources else None
    hits = search(args.patterns, sources, args.context)
    per_file = {}
    for sid, name, page, pat, snippet in hits:
        key = (sid, name)
        per_file[key] = per_file.get(key, 0) + 1
        if per_file[key] > args.limit:
            continue
        where = f"{sid}/{name}" + (f" p.{page[0]} (printed {page[1]})" if page else "")
        print(f"--- {where}  [{pat}]\n{snippet}\n")
    print(f"{len(hits)} hit(s) in {len(per_file)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
