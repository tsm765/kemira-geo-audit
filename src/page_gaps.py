"""S7: page gaps.

    python -m src.page_gaps check    validate data/page_gaps_input.yaml
    python -m src.page_gaps review   write scratch/page_gaps_review.md (direct-answer judgements, passage first)
    python -m src.page_gaps build    write data/page_gaps.json

Two outputs, by design (CLAUDE.md): a site-wide structural diagnosis stated once,
and a per-page content-gap list ranked by claim instances fixed (distinct claims
as tiebreak). Unassigned claims are reported separately, outside the ranking.
"""

import json
import sys
from collections import Counter

import yaml

from src import config
from src.ground_truth import GROUND_TRUTH_DIR, load_meta

INPUT = config.ROOT / "data" / "page_gaps_input.yaml"
OUTPUT = config.ROOT / "data" / "page_gaps.json"
REVIEW = config.ROOT / "scratch" / "page_gaps_review.md"
JUDGEMENTS = {"answers", "partial", "no"}
OPENS = {"answer", "framing", "date", "promo", "heading"}
STATUSES = {"proposed", "confirmed", "revised"}


def _load():
    data = yaml.safe_load(INPUT.read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in yaml.safe_load((config.ROOT / "sources.yaml").read_text(encoding="utf-8"))["sources"]}
    claims = {c["claim_key"]: c for c in json.loads((config.ROOT / "data" / "claims.json").read_text(encoding="utf-8"))["claims"]}
    verdicts = {v["claim_key"]: v for v in json.loads((config.ROOT / "data" / "verdicts.json").read_text(encoding="utf-8"))["verdicts"]}
    return data, sources, claims, verdicts


def check():
    data, sources, claims, verdicts = _load()
    errors = []
    html_pages = [sid for sid in sources if (GROUND_TRUTH_DIR / sid / "meta.json").exists()
                  and load_meta(GROUND_TRUTH_DIR / sid).get("direct_answer")]
    for sid in html_pages:
        j = data["direct_answer"].get(sid)
        if not j:
            errors.append(f"direct_answer: {sid} has no judgement")
            continue
        if j.get("judgement") not in JUDGEMENTS:
            errors.append(f"direct_answer {sid}: judgement must be one of {sorted(JUDGEMENTS)}")
        if j.get("opens_with") not in OPENS:
            errors.append(f"direct_answer {sid}: opens_with must be one of {sorted(OPENS)}")
        if j.get("status") not in STATUSES:
            errors.append(f"direct_answer {sid}: bad status")
    problem = {k for k, v in verdicts.items() if v["verdict"] != "supported"}
    mapped = set(data["claim_map"])
    for k in sorted(problem - mapped):
        errors.append(f"claim_map: {k} ({verdicts[k]['verdict']}) is not mapped")
    for k in sorted(mapped - problem):
        errors.append(f"claim_map: {k} is mapped but its verdict is supported (or unknown)")
    for k, m in data["claim_map"].items():
        if m["page"] != "unassigned" and m["page"] not in sources:
            errors.append(f"claim_map {k}: page {m['page']} not in sources.yaml")
        for s in m.get("also_involved", []):
            if s not in sources:
                errors.append(f"claim_map {k}: also_involved {s} not in sources.yaml")
        if not m.get("reason"):
            errors.append(f"claim_map {k}: reason is empty")
    for e in errors:
        print(f"ERROR   {e}")
    st = Counter(j.get("status") for j in data["direct_answer"].values())
    print(f"{len(data['direct_answer'])} direct-answer judgements {dict(st)}; {len(mapped)} claims mapped "
          f"({sum(1 for m in data['claim_map'].values() if m['page'] == 'unassigned')} unassigned); {len(errors)} error(s).")
    return 1 if errors else 0


def review():
    data, sources, _, _ = _load()
    lines = ["# S7 direct-answer review", "",
             "Read the page's opening first and decide whether it answers the question; the proposal is a prompt.", ""]
    for n, (sid, j) in enumerate(data["direct_answer"].items(), start=1):
        meta = load_meta(GROUND_TRUTH_DIR / sid)
        blocks = meta["direct_answer"]["first_blocks"]
        lines += [f"## {n}. {sid} · {sources[sid]['url']} · {j['status']}", "", "**1. First content blocks (verbatim)**", ""]
        lines += [f"> [{b['tag']}] {b['text']}" for b in blocks] + [""]
        lines += [f"**2. Proposed judgement:** {j['judgement']} (opens with {j['opens_with']}). {j['reason']}", "",
                  f"**3. Implied question:** {j['question']}", ""]
    REVIEW.parent.mkdir(exist_ok=True)
    REVIEW.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REVIEW.relative_to(config.ROOT)} ({len(data['direct_answer'])} pages).")
    return 0


def build():
    if check() != 0:
        return 1
    data, sources, claims, verdicts = _load()
    if any(j["status"] == "proposed" for j in data["direct_answer"].values()):
        print("Direct-answer judgements are still proposed; confirm them before building.")
        return 1
    tallies = json.loads((config.ROOT / "data" / "tallies.json").read_text(encoding="utf-8"))
    cites = Counter()
    for p in tallies["citations"]["kemira_pages"]:
        if p["source_id"]:
            cites[p["source_id"]] += p["count"]
    sf = {f["id"]: f for f in json.loads((config.ROOT / "data" / "structural_findings.json").read_text(encoding="utf-8"))["findings"]}

    pages = {}
    unassigned = []
    for k, m in data["claim_map"].items():
        c, v = claims[k], verdicts[k]
        item = {"claim_id": c["claim_id"], "claim_key": k, "verdict": v["verdict"],
                "unverified_reason": v.get("unverified_reason"), "instances": c["frequency"]["instances"],
                "reason": m["reason"], "also_involved": m.get("also_involved", [])}
        if m["page"] == "unassigned":
            unassigned.append(item)
        else:
            pages.setdefault(m["page"], []).append(item)

    # Findings stated in the site-wide diagnosis apply to every page equally and are
    # never attached to page entries (they would imply variation that does not exist).
    site_wide_sf = {s["structural_finding"] for s in data["site_wide"] if s.get("structural_finding")}
    entries = []
    for sid, items in pages.items():
        j = data["direct_answer"].get(sid)
        linked = sorted(f for f, x in sf.items() if sid in x.get("affects_sources", []) and f not in site_wide_sf)
        entries.append({
            "source_id": sid, "url": sources[sid]["url"],
            "claims_settled": len(items), "instances_settled": sum(i["instances"] for i in items),
            "verdict_mix": dict(Counter(i["verdict"] for i in items)),
            "direct_answer": ({"question": j["question"], "judgement": j["judgement"], "opens_with": j["opens_with"],
                               "reason": j["reason"]} if j else None),
            "cited": {"citations": cites.get(sid, 0), "never_cited": cites.get(sid, 0) == 0},
            "structural_findings": linked,
            "claims": sorted(items, key=lambda i: -i["instances"]),
        })
    entries.sort(key=lambda e: (-e["instances_settled"], -e["claims_settled"], e["source_id"]))
    for n, e in enumerate(entries, start=1):
        e["rank"] = n

    da = data["direct_answer"]
    out = {
        "schema_version": 1,
        "description": ("S7 page gaps. Diagnosis only: which captured kemira.com pages would settle which unresolved "
                        "claims, and what each page's opening does. The site-wide structural diagnosis applies equally to "
                        "every captured page and is stated once; it does not differentiate pages."),
        "site_wide": [{k: v for k, v in s.items() if k != "status"} for s in data["site_wide"]],
        "direct_answer_summary": {
            "pages": len(da),
            "judgement": dict(Counter(j["judgement"] for j in da.values())),
            "opens_with": dict(Counter(j["opens_with"] for j in da.values())),
            "opens_with_date": sorted(s for s, j in da.items() if j["opens_with"] == "date"),
        },
        "direct_answer_all_pages": {s: {k: v for k, v in j.items() if k != "status"} for s, j in da.items()},
        "pages": entries,
        "unassigned": {"description": "Claims no captured page is expected to settle; outside the ranking.",
                       "claims": len(unassigned), "instances": sum(i["instances"] for i in unassigned),
                       "items": sorted(unassigned, key=lambda i: -i["instances"])},
    }
    OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(config.ROOT)}: {len(entries)} pages ranked, {len(unassigned)} claims unassigned.")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit({"check": check, "review": review, "build": build}[cmd]())
