"""Render reports/geo_snapshot.md to a one-page A4 PDF.

    python -m src.render_snapshot

Converts the snapshot's limited Markdown (headings, paragraphs, bullets, bold,
italic, code, rules) to print-styled HTML and prints it with headless Microsoft
Edge. Reports the page count so a run that overflows one A4 page is visible.

Note: in some sandboxed shells headless Edge exits without writing the PDF. The
HTML is still written; print it from PowerShell instead:

    & "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --headless=new --no-pdf-header-footer `
      --print-to-pdf="$PWD\\reports\\geo_snapshot.pdf" "file:///$PWD/reports/geo_snapshot.html"
"""

import html
import re
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

from src import config

MD = config.ROOT / "reports" / "geo_snapshot.md"
HTML = config.ROOT / "reports" / "geo_snapshot.html"
PDF = config.ROOT / "reports" / "geo_snapshot.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

CSS = """
@page { size: A4; margin: 10mm 15mm; }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10pt; line-height: 1.32; color: #1a1a1a; margin: 0; }
h1 { font-size: 16pt; margin: 0 0 0.5mm; }
h2 { font-size: 11pt; margin: 2mm 0 0.5mm; color: #0b3d5c; }
p { margin: 0 0 1.3mm; }
ul { margin: 1mm 0 1.6mm; padding-left: 5mm; }
li { margin: 0 0 0.5mm; }
em { color: #444; }
hr { border: 0; border-top: 0.4pt solid #999; margin: 1.8mm 0 1mm; }
p.small { font-size: 8.5pt; line-height: 1.25; }
code { font-family: Consolas, monospace; font-size: 9pt; }
"""


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    return text


def to_html(md):
    out, in_list, after_rule = [], False, False
    for line in md.splitlines():
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if not line.strip():
            continue
        if line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.strip() == "---":
            out.append("<hr>")
            after_rule = True
        else:
            cls = ' class="small"' if after_rule else ""
            out.append(f"<p{cls}>{inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>What AI assistants say about Kemira</title>"
            f"<style>{CSS}</style></head><body>{''.join(out)}</body></html>")


def main():
    HTML.write_text(to_html(MD.read_text(encoding="utf-8")), encoding="utf-8")
    if not EDGE.exists():
        print(f"Edge not found at {EDGE}; wrote {HTML.relative_to(config.ROOT)} only.")
        return 1
    profile = config.ROOT / "scratch" / "edge-profile"  # separate profile, so a running Edge doesn't block headless mode
    if PDF.exists():
        PDF.unlink()
    # Edge re-splits arguments at spaces ("Kemira Project"), so run from reports/ with relative names.
    profile.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--user-data-dir=../scratch/edge-profile", f"--print-to-pdf={PDF.name}", HTML.name],
                   cwd=PDF.parent, capture_output=True, timeout=120)
    if not PDF.exists():
        print("Edge did not produce a PDF.")
        return 1
    pages = len(PdfReader(str(PDF)).pages)
    print(f"Wrote {PDF.relative_to(config.ROOT)}: {pages} page(s) of A4 at 10 pt body text.")
    return 0 if pages == 1 else 2


if __name__ == "__main__":
    sys.exit(main())
