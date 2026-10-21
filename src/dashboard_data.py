"""S9c: build dashboard/data.json from the committed data.

    python -m src.dashboard_data

The dashboard reads only this file (plus reports/recommendations.md at runtime),
so it makes no live calls and renders identically whenever it is opened. Every
figure is computed here from data/*.json and the frozen raw answers, with
assertions like the snapshot's; nothing on the page is typed by hand.

Plain English only in anything the page displays: no internal labels, source
ids or claim ids (the K07 rule and the S8 framing rules in CLAUDE.md apply).
"""

import json
import re
import sys
from collections import Counter
from urllib.parse import urlparse

import yaml

from src import collection, config
from src.tallies import domain, normalise_url

ROOT = config.ROOT
OUT = ROOT / "dashboard" / "data.json"

OUTCOME = {
    "supported": "Checked out",
    "unverified": "Not addressed in the Kemira material checked",
    "source_conflict": "Kemira's own pages and reports give different figures",
    "contradicted": "Conflicted with Kemira's material",
}
TIER = {
    "1_all_three_both_passes": "Said by all three assistants, in both sessions",
    "2_two_or_three_assistants": "Said by two assistants",
    "3_one_assistant_repeated": "Said by one assistant, more than once",
    "4_singleton": "Said once",
}
ASSISTANT = {"perplexity": "Perplexity", "chatgpt": "ChatGPT", "gemini": "Gemini"}
PAGE_NAMES = {
    "S01": "Company", "S02": "Homepage", "S03": "Strategy and business model", "S04": "Business units and markets",
    "S05": "Outlook and financial targets", "S06": "Water", "S07": "Wastewater", "S08": "Raw and drinking water",
    "S09": "Sludge", "S10": "Digital services", "S11": "Sustainability", "S12": "Sustainability approach",
    "S13": "Climate and energy", "S14": "Circularity", "S15": "Water stewardship", "S16": "Sustainability key indicators",
    "S17": "Annual report 2025", "S18": "Reports and presentations", "S19": "Investor FAQ", "S20": "Share information",
    "S21": "Contacts", "S22": "Half-year report (hosted on a press-release service)",
}
# Destination groups for the "where the links go" chart. Every non-Kemira domain
# must be classed explicitly; an unclassed domain stops the build.
SUPPLIERS = {
    "snf.com", "solenis.com", "ecolab.com", "feralco.eu", "feralco.com", "veoliawatertechnologies.com", "watertechnologies.com",
    "kurita.eu", "kurita-water.com", "basf.com", "usalco.com", "kuhlmann-europe.com", "venatorcorp.com", "brenntag.com",
    "univarsolutions.com", "univarsolutions.fi", "chemifloc.ie", "chemifloc.com", "separ-chemie.de", "hawkinsinc.com",
    "arieschem.com", "envirochemie.com", "orege.com", "derypol.com", "nijhuissaurindustries.com", "acat.com", "enva.com",
}
RESEARCH = {
    "marketscreener.com", "nexdigm.com", "chemicalresearchinsight.com", "mordorintelligence.com", "6wresearch.com",
    "marketdataforecast.com", "usdanalytics.com", "morganreedinsights.com", "marketsandmarkets.com", "pmarketresearch.com",
    "bwdstrategic.com", "bccresearch.com",
}
OTHER = {
    "wikipedia.org", "forbes.com", "cision.com", "impaktly.com", "foundrymax.com", "vuosikertomukset.net", "un.org",
    "ethifinance.com", "bloomberglaw.com", "epa.gov",
}
# K07 rule: reputational and regulatory allegations appear only as one aggregate row.
K07_AGGREGATE = {
    "riverkeeper_lawsuit_2021", "mobile_alabama_petition_2019", "epa_settlement_2013", "epa_cafo_2026",
    "greenwashing_accusations", "ethifinance_intensity_rise", "spills_2019", "spills_2021_2022", "ehs_fines_2023",
}


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _page_label(url, source_id):
    if source_id:
        return PAGE_NAMES[source_id]
    path = urlparse(url).path.rstrip("/")
    last = path.split("/")[-1] or "home"
    last = re.sub(r"\.pdf$", " (PDF)", last)
    words = re.sub(r"[-_]+", " ", last).strip()
    prefix = "Story: " if "/stories/" in path else ("Finnish page: " if path.startswith("/fi") else "")
    if urlparse(url).netloc.startswith("pages."):
        prefix = "Marketing page: "
    return prefix + words[:1].upper() + words[1:]


def build():
    claims = {c["claim_key"]: c for c in _json(ROOT / "data" / "claims.json")["claims"]}
    verdicts = {v["claim_key"]: v for v in _json(ROOT / "data" / "verdicts.json")["verdicts"]}
    tallies = _json(ROOT / "data" / "tallies.json")
    gaps = _json(ROOT / "data" / "page_gaps.json")
    sfs = {f["id"]: f for f in _json(ROOT / "data" / "structural_findings.json")["findings"]}
    cfg = config.load()
    sources = cfg.sources["sources"]
    if set(claims) != set(verdicts):
        raise SystemExit("Every claim needs a confirmed verdict first.")

    # ---- run facts ---------------------------------------------------------
    raw = sorted(collection.RAW_DIR.glob("*_p[12].md"))
    assert len(raw) == 60
    dates = {str(collection.parse(p)[0]["collected_at"])[:10] for p in raw}
    assert len(dates) == 1
    run_date = dates.pop()

    # ---- headline numbers --------------------------------------------------
    cg = []
    for p in sorted(collection.RAW_DIR.glob("O0*_chatgpt_p*.md")):
        cg += [normalise_url(u) for u in collection.parse(p)[0]["citations"]]
    cg_kemira = sum(domain(u) == "kemira.com" for u in cg)
    assert (len(cg), len(cg) - cg_kemira, cg_kemira) == (46, 40, 6)
    assert {domain(u) for u in cg if domain(u) != "kemira.com"} <= SUPPLIERS
    s16 = _json(ROOT / "data" / "ground_truth" / "S16" / "meta.json")["text_chars"]
    assert s16 == 38 and "eurolandir" in json.dumps(sfs["SF01"])
    da = gaps["direct_answer_summary"]
    investor = sorted(s["id"] for s in sources if "/investors/" in s["url"])
    assert sorted(da["opens_with_date"]) == investor
    headline = [
        {"figure": f"{len(cg) - cg_kemira} of {len(cg)}",
         "line": f"Ask ChatGPT who supplies water treatment chemicals and {len(cg) - cg_kemira} of the {len(cg)} links it offers "
                 f"go to other suppliers. {['None','One','Two','Three','Four','Five','Six','Seven'][cg_kemira]} go to Kemira."},
        {"figure": f"{s16} characters",
         "line": f"That is all the readable text on Kemira's sustainability figures page. The numbers come from an outside "
                 f"service, so an assistant reading the page finds almost nothing."},
        {"figure": f"{da['judgement']['answers']} of {da['pages']}",
         "line": f"Only {['no','one','two','three'][da['judgement']['answers']]} Kemira pages begin by answering the question "
                 f"the page exists for. {len(da['opens_with_date'])} begin with a date."},
    ]
    headline[2]["line"] = headline[2]["line"].replace(" 7 begin", " Seven begin")
    assert "Seven begin with a date" in headline[2]["line"]

    # ---- tab 1: where the links go -----------------------------------------
    cit = tallies["citations"]
    agg = cit["aggregate_all_captured"]
    assert (agg["kemira_com"], agg["citations"]) == (106, 208)
    groups = {}
    unclassed = set()
    for a, s in cit["by_assistant"].items():
        g = Counter()
        for row in s["domains"]:
            d = row["domain"]
            key = ("kemira" if d == "kemira.com" else "suppliers" if d in SUPPLIERS else "research" if d in RESEARCH
                   else "other" if d in OTHER else None)
            if key is None:
                unclassed.add(d)
            else:
                g[key] += row["count"]
        groups[a] = {"assistant": ASSISTANT[a], "total": s["citations"], **{k: g.get(k, 0) for k in ("kemira", "suppliers", "research", "other")},
                     "note": "second session only" if a == "gemini" else None}
    if unclassed:
        raise SystemExit(f"Unclassed citation domains: {sorted(unclassed)}")
    wiki = next((d["count"] for d in agg["domains"] if d["domain"] == "wikipedia.org"), 0)
    assert wiki == 1
    cited = [{"page": _page_label(p["url"], p["source_id"]), "citations": p["count"], "checked": bool(p["source_id"])}
             for p in cit["kemira_pages"]]
    cited_ids = {p["source_id"] for p in cit["kemira_pages"] if p["source_id"]}
    never = [{"page": PAGE_NAMES[s["id"]], "highlight": s["id"] == "S09"} for s in sources if s["id"] not in cited_ids]
    assert any(n["highlight"] for n in never)
    links = {
        "kemira": agg["kemira_com"], "total": agg["citations"], "wikipedia": wiki,
        "by_assistant": [groups[a] for a in ("perplexity", "chatgpt", "gemini")],
        "most_cited": cited[:8],
        "outside_checked_set": cit["kemira_pages_outside_sources_yaml"],
        "never_cited": never,
        "checked_total": len(sources),
        "caveat": ("Not every answer's sources were captured: none for Gemini's first session, and only the links inside "
                   "the answer text for ChatGPT and Perplexity in their second. ChatGPT's links are those inside its answer "
                   "text, which may differ from the sources its interface showed."),
    }

    # ---- tab 2: right and wrong --------------------------------------------
    counts = Counter(v["verdict"] for v in verdicts.values())
    assert dict(counts) == {"supported": 78, "unverified": 34, "source_conflict": 8, "contradicted": 3}
    tiers = []
    for key, t in tallies["verdicts_by_frequency"]["tiers"].items():
        v = Counter()
        for k, n in t["verdicts"].items():
            v[k.split("/")[0]] += n
        tiers.append({"label": TIER[key], "claims": t["claims"], **{o: v.get(o, 0) for o in OUTCOME}})
    assert tiers[0]["contradicted"] == 0
    errors = []
    error_text = {
        "ecovadis_platinum": "Said, in both sessions, that Kemira holds an EcoVadis Platinum sustainability rating. Kemira reports Gold.",
        "pillars_strategy_mix": "Gave a list of Kemira's sustainability priorities that mixes its strategy with its focus areas.",
        "carbon_neutrality_overall": ("Said Kemira aims for carbon neutrality \"overall\". Kemira's 2045 target covers its own "
                                      "operations and the energy it buys; its supply chain sits under a separate target."),
    }
    for k, v in verdicts.items():
        if v["verdict"] == "contradicted":
            assert claims[k]["frequency"]["assistants"] == ["gemini"]
            errors.append({"assistant": "Gemini", "text": error_text[k]})
    assert len(errors) == 3
    table, aggregated = [], []
    for k, c in sorted(claims.items(), key=lambda kv: (-kv[1]["frequency"]["instances"], kv[1]["statement"])):
        if k in K07_AGGREGATE:
            aggregated.append(k)
            continue
        table.append({"claim": c["statement"], "outcome": OUTCOME[verdicts[k]["verdict"]],
                      "times": c["frequency"]["instances"],
                      "assistants": [ASSISTANT[a] for a in c["frequency"]["assistants"]]})
    assert all(verdicts[k]["verdict"] == "unverified" for k in aggregated)
    k07_unverified = sum(1 for k, v in verdicts.items() if v["verdict"] == "unverified" and "K07" in claims[k]["frequency"]["questions"])
    assert (k07_unverified, counts["unverified"]) == (16, 34)
    right_wrong = {
        "total": len(claims), "outcomes": [{"label": OUTCOME[o], "count": counts[o]} for o in OUTCOME],
        "tiers": tiers, "outcome_labels": OUTCOME, "errors": errors, "table": table,
        "sustainability_question": (f"About half of the claims Kemira's material doesn't address ({k07_unverified} of "
                                    f"{counts['unverified']}) came from one question: \"Is Kemira a sustainable company? What are "
                                    "the criticisms?\". Assistants raised reputational and regulatory material that Kemira's own "
                                    "pages don't cover."),
        "aggregate_row": {"claims": len(aggregated), "times": sum(claims[k]["frequency"]["instances"] for k in aggregated),
                          "text": (f"{len(aggregated)} claims about reputational and regulatory matters, raised in answers to "
                                   "\"Is Kemira a sustainable company? What are the criticisms?\". Kemira's own pages don't "
                                   "address them. The full records are in the repository.")},
    }

    # ---- tab 3: why assistants give different figures ----------------------
    for k in ("target_scope12_2030", "target_scope12_51_2", "target_scope3_2033", "target_scope3_32_5"):
        assert verdicts[k]["verdict"] == "source_conflict"
    assert "-52%" in verdicts["target_scope12_2030"]["evidence"]["quote"]
    assert "51.23%" in verdicts["target_scope12_2030"]["conflicting_evidence"]["quote"]
    assert "by 50%" in sfs["SF06"]["summary"]
    said = lambda k: [ASSISTANT[a] for a in claims[k]["frequency"]["assistants"]]
    figures = {
        "lede": ("The assistants gave two different figures for the same climate target. Both come from Kemira: "
                 "its climate page states one, its financial reports the other."),
        "sources": [
            {"key": "climate", "source": "Climate page", "states": "52%"},
            {"key": "reports", "source": "Annual report and half-year report", "states": "51.23%"},
            {"key": "sustainability", "source": "Sustainability page", "states": "50% and 52%"},
        ],
        "answers": [
            {"figure": "52%", "assistants": said("target_scope12_2030"), "matches": "climate", "conflicts": "reports"},
            {"figure": "51.23%", "assistants": said("target_scope12_51_2"), "matches": "reports", "conflicts": "climate"},
        ],
        "hedge": {"assistant": said("target_scope12_range_51_52")[0], "figure": "approximately 51–52%"},
        "also": "A second climate target (33% or 32.5%) and two target dates (end of 2025 or 2026) split the same way.",
        "conclusion": "Whichever figure an assistant gave, it matched one Kemira source and contradicted another.",
    }
    assert figures["hedge"]["assistant"] == "ChatGPT"

    # ---- tab 4: who the assistants name ------------------------------------
    sov = tallies["share_of_voice"]
    ks = sov["kemira_summary"]
    comp = {c["company"]: c for c in sov["companies"]}
    assert (ks["named_in"], ks["named_first"], comp["SNF"]["answers_named"], comp["SNF"]["named_first"]) == (18, 16, 18, 2)
    qtext = {q["id"]: q["text"] for q in cfg.questions["questions"]}
    strip = []
    for r in sov["answers"]:
        strip.append({"question": qtext[r["question_id"]], "assistant": ASSISTANT[r["assistant"]], "session": r["pass"],
                      "named": r["of"], "kemira": r["kemira"]["position"],
                      "snf": r["suppliers"].index("SNF") + 1 if "SNF" in r["suppliers"] else None,
                      "first": r["first_named"]})
    shifts = [s for s in strip if s["kemira"] != 1]
    assert len(shifts) == 2 and all(s["assistant"] == "Gemini" and s["session"] == 2 and s["first"] == "SNF" for s in shifts)
    peers = [{"company": c["company"], "named_in": c["answers_named"], "first": c["named_first"]}
             for c in sov["companies"] if c["answers_named"] >= 4]
    names = {"answers": len(strip), "kemira": {"named_in": ks["named_in"], "first": ks["named_first"]},
             "snf": {"named_in": comp["SNF"]["answers_named"], "first": comp["SNF"]["named_first"]},
             "strip": strip, "peers": peers,
             "shift_note": ("In its second session, Gemini named SNF first and Kemira second in two of the three questions, "
                            "having named Kemira first in its first session.")}

    out = {
        "generated_from": "data/*.json and data/raw/ by src/dashboard_data.py",
        "title": "What AI assistants say about Kemira",
        "independence": "Independent audit, not affiliated with Kemira",
        "method": (f"Three assistants ({', '.join(ASSISTANT.values())}) answered {len(cfg.questions['questions'])} questions, "
                   f"each asked twice on {int(run_date[8:])} October {run_date[:4]}, and every claim was checked against "
                   f"{len(sources)} Kemira pages and reports."),
        "run_date": run_date,
        "headline": headline,
        "links": links,
        "right_wrong": right_wrong,
        "figures": figures,
        "names": names,
        "recommendations_source": "../reports/recommendations.md",
    }
    # Displayed text is every string value; dict keys are data, not shown.
    def strings(x):
        if isinstance(x, dict):
            for v in x.values():
                yield from strings(v)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v)
        elif isinstance(x, str):
            yield x
    leaked = [s for s in strings(out) if re.search(r"\bS\d{2}\b|\bC\d{3}\b|source_conflict|unverified|_", s)
              and not s.startswith(("data/", "../"))]
    assert not leaked, f"internal vocabulary in displayed text: {leaked[:5]}"
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(table)} claim rows + 1 aggregate row of {len(aggregated)}).")
    return 0


if __name__ == "__main__":
    sys.exit(build())
