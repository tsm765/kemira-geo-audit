"""S4: build data/claims.json from the hand-made extraction in data/claims_input.yaml.

    python -m src.claims

Precondition: both collection passes complete and frozen (src.collection check
--require-complete). Every quote in the input must appear verbatim in its raw
answer file; the build fails otherwise. Frequency, stability, instability_cause
and kemira_presence are computed here, never typed by hand.

Input format (data/claims_input.yaml):

    claims:
      <key>:
        statement: canonical statement of the claim
        topic: identity | financials | ...
        value: {...}                  # optional, structured figure
        self_contradictory: <reason>  # optional: incoherent as stated, whatever ground truth says
    files:
      <file stem, e.g. K03_chatgpt_p1>:
        presence: {named: true, position: 1, of: 7}   # open questions only
        instances:
          - {c: <claim key>, q: ["verbatim quote", ...], n: "note on a borderline call"}
"""

import json
import re
import sys
from pathlib import Path

import yaml

from src import collection, config

INPUT_FILE = config.ROOT / "data" / "claims_input.yaml"
OUTPUT_FILE = config.ROOT / "data" / "claims.json"
ASSISTANTS = ("perplexity", "chatgpt", "gemini")
PASSES = (1, 2)


def _norm(text):
    """Whitespace-insensitive form for verbatim quote matching."""
    return re.sub(r"\s+", " ", text).strip()


def _quote_pieces(quote):
    """A quote may join non-adjacent spans of the same answer with ' … '."""
    return [p for p in (s.strip() for s in quote.split(" … ")) if p]


def build():
    cfg = config.load()
    assistants = collection.load_assistants()
    for pass_no in PASSES:
        if collection.check(cfg, assistants, pass_no, require_complete=True) != 0:
            print(f"Collection pass {pass_no} is not complete and frozen; not building claims.")
            return 1

    data = yaml.safe_load(INPUT_FILE.read_text(encoding="utf-8"))
    claim_defs, files = data["claims"], data["files"]
    questions = {q["id"]: q for q in cfg.questions["questions"]}
    errors = []

    expected = {f"{q}_{a}_p{p}" for q in questions for a in ASSISTANTS for p in PASSES}
    for missing in sorted(expected - set(files)):
        errors.append(f"{missing}: no extraction entry (use 'instances: []' if the answer makes no claims)")
    for extra in sorted(set(files) - expected):
        errors.append(f"{extra}: not a collected answer file")

    bodies = {}
    for stem in sorted(set(files) & expected):
        _, body = collection.parse(collection.RAW_DIR / f"{stem}.md")
        bodies[stem] = _norm(body)

    instances = []
    for stem in sorted(set(files) & expected, key=lambda s: (s.split("_")[0], ASSISTANTS.index(s.split("_")[1]), s[-1])):
        qid, assistant, p = stem.split("_")
        entry = files[stem] or {}
        if qid.startswith("O") and "presence" not in entry:
            errors.append(f"{stem}: open question needs a presence entry")
        if not qid.startswith("O") and "presence" in entry:
            errors.append(f"{stem}: presence is recorded for open questions only")
        seen = set()
        for i, inst in enumerate(entry.get("instances") or [], start=1):
            key = inst["c"]
            if key not in claim_defs:
                errors.append(f"{stem}#{i}: unknown claim key '{key}'")
            if key in seen:
                errors.append(f"{stem}#{i}: claim '{key}' appears twice in one answer; merge the quotes")
            seen.add(key)
            for quote in inst["q"]:
                for piece in _quote_pieces(quote):
                    if _norm(piece) not in bodies[stem]:
                        errors.append(f"{stem}#{i} ({key}): quote not found verbatim: {piece[:90]!r}")
            instances.append({
                "instance_id": f"{stem}#{i:02d}",
                "file": f"{stem}.md",
                "question_id": qid,
                "assistant": assistant,
                "pass": int(p[1]),
                "quote": inst["q"],
                "claim_key": key,
                **({"note": inst["n"]} if inst.get("n") else {}),
            })

    unused = sorted(set(claim_defs) - {i["claim_key"] for i in instances})
    for key in unused:
        errors.append(f"claim '{key}' is defined but has no instances")

    if errors:
        for e in errors:
            print(f"ERROR   {e}")
        print(f"\n{len(errors)} error(s); claims.json not written.")
        return 1

    # Presence of Kemira in open questions, per question x assistant.
    presence_rows = []
    for qid in sorted(q for q in questions if q.startswith("O")):
        for a in ASSISTANTS:
            row = {"question_id": qid, "assistant": a}
            named = []
            for p in PASSES:
                pr = files[f"{qid}_{a}_p{p}"]["presence"]
                row[f"pass_{p}"] = pr
                named.append(bool(pr["named"]))
            row["presence_stability"] = {
                (True, True): "stable_present", (False, False): "stable_absent",
                (True, False): "pass1_only", (False, True): "pass2_only",
            }[tuple(named)]
            # Named in both passes but at a different position is a result in its own right.
            if all(named):
                p1, p2 = row["pass_1"]["position"], row["pass_2"]["position"]
                row["position_stability"] = "same" if p1 == p2 else f"changed {p1}->{p2}"
            presence_rows.append(row)
    named_in = {(r["question_id"], r["assistant"], p): r[f"pass_{p}"]["named"] for r in presence_rows for p in PASSES}

    # Order claims by first appearance, then number them.
    order = []
    for inst in instances:
        if inst["claim_key"] not in order:
            order.append(inst["claim_key"])
    ids = {key: f"C{n:03d}" for n, key in enumerate(order, start=1)}

    claims = []
    for key in order:
        mine = [i for i in instances if i["claim_key"] == key]
        definition = claim_defs[key]
        stability, cause = {}, {}
        for a in ASSISTANTS:
            in_pass = {p: any(i["assistant"] == a and i["pass"] == p for i in mine) for p in PASSES}
            state = {(True, True): "both_passes", (True, False): "pass1_only",
                     (False, True): "pass2_only", (False, False): "absent"}[(in_pass[1], in_pass[2])]
            stability[a] = state
            if state in ("pass1_only", "pass2_only"):
                missing_pass = 2 if state == "pass1_only" else 1
                qids = {i["question_id"] for i in mine if i["assistant"] == a}
                # Unstable because Kemira was not named at all in the other pass?
                presence_gap = all(q.startswith("O") and not named_in[(q, a, missing_pass)] for q in qids)
                cause[a] = "kemira_presence" if presence_gap else "claim"
        claims.append({
            "claim_id": ids[key],
            "claim_key": key,
            "statement": definition["statement"],
            "topic": definition["topic"],
            **({"value": definition["value"]} if definition.get("value") else {}),
            "self_contradictory": definition.get("self_contradictory"),
            "instance_ids": [i["instance_id"] for i in mine],
            "frequency": {
                "instances": len(mine),
                "assistants": [a for a in ASSISTANTS if any(i["assistant"] == a for i in mine)],
                "passes": [p for p in PASSES if any(i["pass"] == p for i in mine)],
                "questions": sorted({i["question_id"] for i in mine}),
            },
            "stability": stability,
            "instability_cause": cause,
        })
    for inst in instances:
        inst["claim_id"] = ids[inst["claim_key"]]

    out = {
        "schema_version": 1,
        "description": (
            "Claims extracted from the 60 frozen answer files (data/raw/). Each instance quotes the answer "
            "verbatim; unique claims collapse instances that a reader would check as one unit. Frequency, "
            "stability and instability_cause are computed from the instances. kemira_presence records whether "
            "Kemira was named in each open-question answer, separately from claims. Extraction involves "
            "judgment (README limit 5); borderline calls are noted on the instance."
        ),
        "source": "data/claims_input.yaml",
        "counts": {"instances": len(instances), "claims": len(claims)},
        "instances": instances,
        "claims": claims,
        "kemira_presence": presence_rows,
    }
    OUTPUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE.relative_to(config.ROOT)}: {len(instances)} instances, {len(claims)} unique claims.")
    return 0


def check_partial():
    """Verify quotes and keys for whatever files are in the input so far (used while extracting)."""
    data = yaml.safe_load(INPUT_FILE.read_text(encoding="utf-8"))
    claim_defs, files = data.get("claims") or {}, data.get("files") or {}
    bad, n = 0, 0
    for stem, entry in files.items():
        _, body = collection.parse(collection.RAW_DIR / f"{stem}.md")
        body = _norm(body)
        for i, inst in enumerate((entry or {}).get("instances") or [], start=1):
            n += 1
            if inst["c"] not in claim_defs:
                print(f"{stem}#{i}: unknown claim key {inst['c']}"); bad += 1
            for quote in inst["q"]:
                for piece in _quote_pieces(quote):
                    if _norm(piece) not in body:
                        print(f"{stem}#{i} ({inst['c']}): not found: {piece[:100]!r}"); bad += 1
    print(f"{len(files)} files, {n} instances, {len(claim_defs)} claim keys, {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(check_partial() if sys.argv[1:] == ["--partial"] else build())
