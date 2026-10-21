// Render reports/geo_snapshot.md to reports/geo_snapshot.docx (A4, one page).
//
//   NODE_PATH=scratch/node/node_modules node src/render_snapshot_docx.js
//
// Generated from the Markdown that src/snapshot.py writes, so the Word file is
// output, not a hand-edited copy. Layout mirrors src/render_snapshot.py (PDF):
// A4, 10 mm top/bottom and 15 mm side margins, 10 pt Segoe UI body.

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, LevelFormat, BorderStyle, AlignmentType,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const MD = path.join(ROOT, "reports", "geo_snapshot.md");
const OUT = path.join(ROOT, "reports", "geo_snapshot.docx");

const mm = (v) => Math.round((v * 1440) / 25.4);      // millimetres to twips (DXA)
const FONT = "Segoe UI";
const BODY = 20;                                        // half-points: 10 pt
const SMALL = 17;                                       // 8.5 pt footer
const LINE = Math.round(240 * 1.32);                    // 1.32 line spacing
const HEADING_COLOUR = "0B3D5C";

// **bold**, *italic*, `code` -> TextRuns
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|(?<![\w*])\*(?!\s)[^*]+?(?<!\s)\*(?![\w*]))/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(new TextRun({ text: tok.slice(2, -2), ...base, bold: true }));
    else if (tok.startsWith("`")) out.push(new TextRun({ text: tok.slice(1, -1), ...base, font: "Consolas", size: (base.size || BODY) - 2 }));
    else out.push(new TextRun({ text: tok.slice(1, -1), ...base, italics: true }));
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

function build(md) {
  const children = [];
  let afterRule = false;
  for (const line of md.split(/\r?\n/)) {
    if (!line.trim()) continue;
    if (line.startsWith("# ")) {
      children.push(new Paragraph({ spacing: { after: mm(0.5) }, children: [new TextRun({ text: line.slice(2), bold: true, size: 32 })] }));
    } else if (line.startsWith("## ")) {
      children.push(new Paragraph({
        spacing: { before: mm(2), after: mm(0.5) },
        children: [new TextRun({ text: line.slice(3), bold: true, size: 22, color: HEADING_COLOUR })],
      }));
    } else if (line.startsWith("- ")) {
      children.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: mm(0.5), line: LINE }, children: runs(line.slice(2)) }));
    } else if (line.trim() === "---") {
      children.push(new Paragraph({ spacing: { before: mm(1.8), after: mm(1) },
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "999999", space: 1 } }, children: [] }));
      afterRule = true;
    } else if (afterRule) {
      const text = line.replace(/^\*(.*)\*$/, "$1");
      children.push(new Paragraph({ spacing: { after: 0, line: Math.round(240 * 1.25) },
        children: runs(text, { italics: true, size: SMALL, color: "444444" }) }));
    } else if (/^\*[^*].*\*$/.test(line)) {
      children.push(new Paragraph({ spacing: { after: mm(1.3), line: LINE },
        children: runs(line.slice(1, -1), { italics: true, color: "444444" }) }));
    } else {
      children.push(new Paragraph({ spacing: { after: mm(1.3), line: LINE }, children: runs(line) }));
    }
  }
  return children;
}

const doc = new Document({
  title: "What AI assistants say about Kemira",
  styles: { default: { document: { run: { font: FONT, size: BODY, color: "1A1A1A" } } } },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: mm(5), hanging: mm(3.5) } } } }],
    }],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: mm(10), bottom: mm(10), left: mm(15), right: mm(15) } } },
    children: build(fs.readFileSync(MD, "utf8")),
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log(`Wrote ${path.relative(ROOT, OUT)} (${buf.length} bytes)`);
});
