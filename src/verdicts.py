"""S5: check, review and build verdicts.

    python -m src.verdicts check     validate data/verdicts_input.yaml against claims.json and the ground truth
    python -m src.verdicts review    write scratch/verdicts_review.md: passage, then verdict, then claim
    python -m src.verdicts build     write data/verdicts.json from confirmed/revised verdicts only

Every evidence quote must appear verbatim (whitespace-insensitive) in the cited
ground truth file, and on the cited page for PDF sources.
"""

import json
import re
import sys

import yaml

from src import config
from src.gt_search import GT, PAGE_MARK

INPUT_FILE = config.ROOT / "data" / "verdicts_input.yaml"
CLAIMS_FILE = config.ROOT / "data" / "claims.json"
OUTPUT_FILE = config.ROOT / "data" / "verdicts.json"
REVIEW_FILE = config.ROOT / "scratch" / "verdicts_review.md"

# source_conflict: the claim matches some of Kemira's published material and
# conflicts with other parts of it, so the ground truth cannot settle it. It cites
# two passages: `evidence` (the one the claim matches) and `conflicting_evidence`.
VERDICTS = {"supported", "contradicted", "unverified", "source_conflict", "not_adjudicated"}
CONTRADICTION_TYPES = {"assistant_wrong", "source_unclear"}
# Why an unverified claim is unverified. Left unset where it cannot be told
# without looking outside sources.yaml (which adjudication never does).
#   outside_ground_truth: related material exists elsewhere on kemira.com but is
#                         not in the captured set (a limit of this audit)
#   not_addressed:        Kemira's published material does not cover it (a content gap)
#   cited_source_outside_set: the assistant named a kemira.com page outside the
#                         captured set as its source for this claim (read from the
#                         frozen raw answer; asserts nothing about what that page says)
UNVERIFIED_REASONS = {"outside_ground_truth", "not_addressed", "cited_source_outside_set"}
STATUSES = {"proposed", "confirmed", "revised"}


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


def _page_texts(text):
    """{pdf_page: text} for a PDF text file."""
    marks = list(PAGE_MARK.finditer(text))
    return {int(m.group(1)): text[m.end():(marks[i + 1].start() if i + 1 < len(marks) else len(text))]
            for i, m in enumerate(marks)}


def load():
    data = yaml.safe_load(INPUT_FILE.read_text(encoding="utf-8")) or {}
    claims = {c["claim_key"]: c for c in json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))["claims"]}
    return data.get("verdicts") or {}, claims


def check():
    verdicts, claims = load()
    errors = []
    for key, v in verdicts.items():
        def err(msg):
            errors.append(f"{key}: {msg}")
        if key not in claims:
            err("not a claim key in claims.json")
        if v.get("verdict") not in VERDICTS:
            err(f"verdict {v.get('verdict')!r} not one of {sorted(VERDICTS)}")
        if v.get("status") not in STATUSES:
            err(f"status {v.get('status')!r} not one of {sorted(STATUSES)}")
        if v.get("verdict") == "contradicted" and v.get("contradiction_type") not in CONTRADICTION_TYPES:
            err("contradicted needs contradiction_type: assistant_wrong or source_unclear")
        if v.get("verdict") != "contradicted" and v.get("contradiction_type"):
            err("contradiction_type is only for contradicted verdicts")
        if not v.get("reason"):
            err("reason is empty")
        if v.get("unverified_reason") is not None:
            if v.get("verdict") != "unverified":
                err("unverified_reason is only for unverified verdicts")
            elif v["unverified_reason"] not in UNVERIFIED_REASONS:
                err(f"unverified_reason {v['unverified_reason']!r} not one of {sorted(UNVERIFIED_REASONS)}")
        if "evaluative" in v and not isinstance(v["evaluative"], bool):
            err("evaluative must be true or false")
        ev = v.get("evidence")
        if v.get("verdict") in ("supported", "contradicted", "source_conflict") and not ev:
            err("supported/contradicted/source_conflict verdicts need an evidence passage")
        if v.get("verdict") == "source_conflict" and not v.get("conflicting_evidence"):
            err("source_conflict needs conflicting_evidence: the passage the claim conflicts with")
        if v.get("verdict") != "source_conflict" and v.get("conflicting_evidence"):
            err("conflicting_evidence is only for source_conflict verdicts")
        for ev in [e for e in (ev, v.get("conflicting_evidence")) if e]:
            path = GT / ev["source"] / ev.get("file", "text.md")
            if not path.exists():
                err(f"evidence file {path.relative_to(config.ROOT)} not found")
                continue
            text = path.read_text(encoding="utf-8")
            if ev.get("page") is not None:
                text = _page_texts(text).get(int(ev["page"]), "")
                if not text:
                    err(f"page {ev['page']} not found in {ev['source']}")
            if _norm(ev["quote"]) not in _norm(text):
                where = f"{ev['source']}" + (f" p.{ev['page']}" if ev.get("page") else "")
                err(f"evidence quote not found verbatim in {where}: {ev['quote'][:80]!r}")
            sentences = len(re.findall(r"[.!?](\s|$)", _norm(ev["quote"]) + " "))
            if sentences > 3:
                err(f"evidence passage has {sentences} sentences; the rule is one to three")
    for e in errors:
        print(f"ERROR   {e}")
    pending = sorted(set(claims) - set(verdicts))
    by_status = {s: sum(1 for v in verdicts.values() if v.get("status") == s) for s in STATUSES}
    print(f"{len(verdicts)} verdicts ({by_status}); {len(pending)} claims without a verdict; {len(errors)} error(s).")
    return 1 if errors else 0


def review():
    verdicts, claims = load()
    lines = ["# S5 verdict review", "",
             "Read Kemira's passage first and decide; the proposed verdict is a prompt, not a conclusion.", ""]
    for n, (key, v) in enumerate(verdicts.items(), start=1):
        c = claims[key]
        ev = v.get("evidence") or {}
        where = f"{ev.get('source', '-')}" + (f" p.{ev['page']}" if ev.get("page") else "")
        verdict = v["verdict"] + (f" ({v['contradiction_type']})" if v.get("contradiction_type") else "")
        if v["verdict"] == "unverified":
            verdict += f" ({v.get('unverified_reason') or 'reason unset'})"
        if v.get("evaluative"):
            verdict += " [evaluative]"
        lines += [
            f"## {n}. {c['claim_id']} · {v['status']}",
            "",
            f"**1. Ground truth ({where})**",
            "",
            f"> {ev.get('quote', '(no passage)')}",
            "",
        ]
        cev = v.get("conflicting_evidence")
        if cev:
            cwhere = cev["source"] + (f" p.{cev['page']}" if cev.get("page") else "")
            lines += [f"**1b. Conflicting ground truth ({cwhere})**", "", f"> {cev['quote']}", ""]
        for s in v.get("see_also") or []:
            lines.append(f"- see also: {s}")
        if v.get("see_also"):
            lines.append("")
        lines += [
            f"**2. Proposed verdict:** {verdict}. {v['reason']}",
            "",
            f"**3. Claim:** {c['statement']}  ",
            f"_{c['frequency']['instances']} instances; assistants: {', '.join(c['frequency']['assistants'])}; passes: {c['frequency']['passes']}_",
            "",
        ]
    REVIEW_FILE.parent.mkdir(exist_ok=True)
    REVIEW_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REVIEW_FILE.relative_to(config.ROOT)} ({len(verdicts)} verdicts).")
    return 0


def build():
    if check() != 0:
        print("Not building: fix the errors above.")
        return 1
    verdicts, claims = load()
    out = []
    for key, v in verdicts.items():
        if v["status"] not in ("confirmed", "revised"):
            continue
        c = claims[key]
        out.append({
            "claim_id": c["claim_id"], "claim_key": key, "statement": c["statement"],
            "verdict": v["verdict"], "contradiction_type": v.get("contradiction_type"),
            "unverified_reason": v.get("unverified_reason"), "evaluative": bool(v.get("evaluative")),
            "evidence": v.get("evidence"), "conflicting_evidence": v.get("conflicting_evidence"),
            "reason": v["reason"], "see_also": v.get("see_also", []),
            "status": v["status"], "instance_ids": c["instance_ids"],
        })
    OUTPUT_FILE.write_text(json.dumps({"schema_version": 1, "verdicts": out}, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE.relative_to(config.ROOT)}: {len(out)} confirmed verdicts.")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit({"check": check, "review": review, "build": build}[cmd]())
