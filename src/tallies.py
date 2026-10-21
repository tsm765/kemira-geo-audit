"""S6: citation tally, share of voice and verdict-by-frequency cross-cut.

    python -m src.tallies

Preconditions: both collection passes complete and frozen; claims.json built;
every claim has a confirmed/revised verdict in verdicts.json.

Citation rules (CLAUDE.md): strip utm_* parameters and #fragments (including
#:~:text= anchors) before counting; never count `not_captured` as zero; Gemini
pass 1 is 'retrieval shown, sources not capturable', not zero. The unit is one
URL in one answer's citation list (lists are de-duplicated within an answer).
"""

import json
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import yaml

from src import collection, config

OUT = config.ROOT / "data" / "tallies.json"
SOV_INPUT = config.ROOT / "data" / "sov_input.yaml"
ASSISTANTS = ("perplexity", "chatgpt", "gemini")
KEMIRA_DOMAIN = "kemira.com"


# ---- URLs -----------------------------------------------------------------

def normalise_url(url):
    p = urlparse(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")])
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", query, ""))


def domain(url):
    host = urlparse(url).netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _counter_rows(counter, total):
    return [{"domain": d, "count": n, "share": round(n / total, 4) if total else None} for d, n in counter.most_common()]


# ---- citations ------------------------------------------------------------

def citation_tally(cfg):
    sources = {normalise_url(s["url"]): s["id"] for s in cfg.sources["sources"]}
    # A captured PDF is in the set under its own URL too (S17's landing page is in
    # sources.yaml; the PDF it links to is what was captured as its text).
    from src.ground_truth import PDF_SOURCE_URLS
    sources.update({normalise_url(u): sid for sid, u in PDF_SOURCE_URLS.items()})
    records = []  # (assistant, pass, measure, question, normalised url)
    not_captured = Counter()
    for path in sorted(collection.RAW_DIR.glob("*_p[12].md")):
        qid, a, ps = path.stem.split("_")
        p = int(ps[1])
        front, _ = collection.parse(path)
        for u in front["citations"]:
            records.append((a, p, "inline", qid, normalise_url(u)))
        shown = front.get("citations_displayed")
        if shown == collection.NOT_CAPTURED:
            not_captured[(a, p)] += 1
        elif isinstance(shown, list):
            for u in shown:
                records.append((a, p, "displayed", qid, normalise_url(u)))

    def summarise(rows):
        doms = Counter(domain(r[4]) for r in rows)
        total = len(rows)
        k = doms.get(KEMIRA_DOMAIN, 0)
        return {
            "citations": total,
            "kemira_com": k,
            "kemira_com_share": round(k / total, 4) if total else None,
            "distinct_domains": len(doms),
            "domains": _counter_rows(doms, total),
        }

    cells = {}
    for a in ASSISTANTS:
        for p in (1, 2):
            for m in ("inline", "displayed"):
                rows = [r for r in records if r[0] == a and r[1] == p and r[2] == m]
                key = f"{a}_p{p}_{m}"
                if rows:
                    cells[key] = summarise(rows)
                elif m == "displayed" and not_captured[(a, p)]:
                    cells[key] = {"status": "not_captured", "cells": not_captured[(a, p)]}
                elif a == "gemini" and p == 1:
                    cells[key] = {"status": "retrieval shown, sources not capturable (README limit 9)"}
    per_assistant = {a: summarise([r for r in records if r[0] == a]) for a in ASSISTANTS}

    kemira_pages = defaultdict(lambda: {"count": 0, "assistants": Counter(), "questions": set(), "measures": Counter()})
    for a, p, m, q, u in records:
        if domain(u) == KEMIRA_DOMAIN:
            e = kemira_pages[u]
            e["count"] += 1
            e["assistants"][a] += 1
            e["questions"].add(q)
            e["measures"][f"{m}_p{p}"] += 1
    pages = sorted(({
        "url": u, "count": e["count"], "assistants": dict(e["assistants"]),
        "questions": sorted(e["questions"]), "measures": dict(e["measures"]),
        "source_id": sources.get(u),
    } for u, e in kemira_pages.items()), key=lambda r: (-r["count"], r["url"]))

    return {
        "rules": "utm_* parameters and #fragments (incl. #:~:text=) stripped; domains reduced to the registrable domain (www./subdomains folded, e.g. pages.kemira.com -> kemira.com); unit = one URL in one answer's de-duplicated citation list.",
        "measurement_caveat": (
            "Not comparable across assistants or passes as if measured the same way. Perplexity and ChatGPT: inline URLs "
            "in the copied answer text, both passes (pass-2 source chips not captured). Gemini: pass 1 retrieval shown but "
            "sources not capturable; pass 2 source-chip URLs entered by hand. ChatGPT URLs are inline links within the answer "
            "body, which may not match the sources the interface displayed (README limit 10)."),
        "aggregate_all_captured": summarise(records),
        "by_assistant": per_assistant,
        "by_assistant_pass_measure": cells,
        "kemira_pages": pages,
        "kemira_pages_in_sources_yaml": sum(1 for r in pages if r["source_id"]),
        "kemira_pages_outside_sources_yaml": sum(1 for r in pages if not r["source_id"]),
    }


# ---- share of voice -------------------------------------------------------

def _listed(peers):
    names = {c["name"] for c in peers["comparators"]}
    for seg in peers["segments"].values():
        names.update(seg["peers"])
    return {c["name"] for c in peers["comparators"]}, names


def share_of_voice(cfg, warnings):
    data = yaml.safe_load(SOV_INPUT.read_text(encoding="utf-8"))
    aliases, answers = data["aliases"], data["answers"]
    comparators, listed = _listed(cfg.peers)
    expected = {f"{q}_{a}_p{p}" for q in ("O01", "O02", "O03") for a in ASSISTANTS for p in (1, 2)}
    if set(answers) != expected:
        raise SystemExit(f"sov_input.yaml must cover exactly the 18 open answers; missing {sorted(expected - set(answers))}")

    def found(name, text):
        return any(re.search(rf"\b{re.escape(al)}\b", text, re.I) for al in aliases[name])

    rows = []
    for stem in sorted(answers, key=lambda s: (s[:3], ASSISTANTS.index(s.split('_')[1]), s[-1])):
        entry = answers[stem]
        _, body = collection.parse(collection.RAW_DIR / f"{stem}.md")
        sup = entry["suppliers"]
        if len(set(sup)) != len(sup):
            warnings.append(f"{stem}: duplicate supplier in list")
        for name in sup:
            if name not in aliases:
                warnings.append(f"{stem}: '{name}' has no alias entry")
            elif not found(name, body):
                warnings.append(f"{stem}: '{name}' not found in the answer text")
        for name in aliases:
            if name not in sup and name not in (entry.get("excluded") or {}) and found(name, body):
                warnings.append(f"{stem}: '{name}' appears in the answer but is neither counted nor excluded")
        q, a, ps = stem.split("_")
        rows.append({"answer": stem, "question_id": q, "assistant": a, "pass": int(ps[1]),
                     "suppliers": sup, "of": len(sup),
                     "kemira": {"named": "Kemira" in sup, "position": sup.index("Kemira") + 1 if "Kemira" in sup else None},
                     "first_named": sup[0] if sup else None,
                     "excluded": entry.get("excluded") or {}, "notes": entry.get("notes")})

    by_company = defaultdict(lambda: {"answers": 0, "positions": [], "by_assistant": Counter(), "by_question": Counter(), "first": 0})
    for r in rows:
        for i, name in enumerate(r["suppliers"], start=1):
            e = by_company[name]
            e["answers"] += 1
            e["positions"].append(i)
            e["by_assistant"][r["assistant"]] += 1
            e["by_question"][r["question_id"]] += 1
            e["first"] += i == 1
    companies = sorted(({
        "company": n, "answers_named": e["answers"], "of_answers": len(rows),
        "named_first": e["first"], "mean_position": round(sum(e["positions"]) / len(e["positions"]), 2),
        "by_assistant": dict(e["by_assistant"]), "by_question": dict(e["by_question"]),
        "status": "kemira" if n == "Kemira" else ("comparator" if n in comparators else ("listed" if n in listed else "unlisted")),
    } for n, e in by_company.items()), key=lambda c: (-c["answers_named"], c["mean_position"]))

    kemira_rows = [r for r in rows if r["kemira"]["named"]]
    presence = []
    for q in ("O01", "O02", "O03"):
        for a in ASSISTANTS:
            p1 = next(r for r in rows if r["question_id"] == q and r["assistant"] == a and r["pass"] == 1)
            p2 = next(r for r in rows if r["question_id"] == q and r["assistant"] == a and r["pass"] == 2)
            presence.append({"question_id": q, "assistant": a,
                             "pass_1": {**p1["kemira"], "of": p1["of"], "first_named": p1["first_named"]},
                             "pass_2": {**p2["kemira"], "of": p2["of"], "first_named": p2["first_named"]},
                             "position_stability": "same" if p1["kemira"]["position"] == p2["kemira"]["position"]
                             else f"changed {p1['kemira']['position']}->{p2['kemira']['position']}"})
    return {
        "rules": "peers.yaml counting rules plus the conventions in data/sov_input.yaml; position is order of first mention in the answer body.",
        "kemira_summary": {
            "named_in": len(kemira_rows), "of_answers": len(rows),
            "named_first": sum(1 for r in kemira_rows if r["kemira"]["position"] == 1),
            "not_first": [{"answer": r["answer"], "position": r["kemira"]["position"], "first_named": r["first_named"]}
                          for r in kemira_rows if r["kemira"]["position"] != 1],
        },
        "kemira_presence": presence,
        "comparators": [c for c in companies if c["status"] in ("kemira", "comparator")],
        "companies": companies,
        "unlisted": [c for c in companies if c["status"] == "unlisted"],
        "answers": rows,
    }


# ---- verdicts by frequency --------------------------------------------------

def verdicts_by_frequency():
    claims = {c["claim_key"]: c for c in json.loads((config.ROOT / "data" / "claims.json").read_text(encoding="utf-8"))["claims"]}
    verdicts = {v["claim_key"]: v for v in json.loads((config.ROOT / "data" / "verdicts.json").read_text(encoding="utf-8"))["verdicts"]}
    missing = sorted(set(claims) - set(verdicts))
    if missing:
        raise SystemExit(f"{len(missing)} claims have no confirmed verdict; finish S5 first")

    def label(v):
        return v["verdict"] + (f"/{v['contradiction_type']}" if v.get("contradiction_type") else "")

    def tier(c):
        f = c["frequency"]
        if len(f["assistants"]) == 3 and f["passes"] == [1, 2]:
            return "1_all_three_both_passes"
        if len(f["assistants"]) >= 2:
            return "2_two_or_three_assistants"
        if f["instances"] > 1:
            return "3_one_assistant_repeated"
        return "4_singleton"

    tiers = defaultdict(lambda: {"claims": 0, "instances": 0, "verdicts": Counter(), "verdicts_by_instance": Counter()})
    for k, c in claims.items():
        t = tiers[tier(c)]
        t["claims"] += 1
        t["instances"] += c["frequency"]["instances"]
        t["verdicts"][label(verdicts[k])] += 1
        t["verdicts_by_instance"][label(verdicts[k])] += c["frequency"]["instances"]
    out = {}
    for name in sorted(tiers):
        t = tiers[name]
        out[name] = {"claims": t["claims"], "instances": t["instances"],
                     "verdicts": dict(t["verdicts"].most_common()),
                     "supported_share": round(t["verdicts"].get("supported", 0) / t["claims"], 3),
                     "verdicts_by_instance": dict(t["verdicts_by_instance"].most_common())}
    all_v = Counter(label(v) for v in verdicts.values())
    all_i = Counter()
    for k, c in claims.items():
        all_i[label(verdicts[k])] += c["frequency"]["instances"]
    return {"tiers": out, "all_claims": dict(all_v.most_common()), "all_instances": dict(all_i.most_common())}


def main():
    cfg = config.load()
    assistants = collection.load_assistants()
    for p in (1, 2):
        if collection.check(cfg, assistants, p, require_complete=True) != 0:
            print(f"Collection pass {p} is not complete and frozen.")
            return 1
    warnings = []
    out = {
        "schema_version": 1,
        "citations": citation_tally(cfg),
        "share_of_voice": share_of_voice(cfg, warnings),
        "verdicts_by_frequency": verdicts_by_frequency(),
    }
    for w in warnings:
        print(f"WARNING {w}")
    if warnings:
        print(f"{len(warnings)} warning(s); tallies.json not written.")
        return 1
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(config.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
