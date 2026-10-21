"""S8: the one-page GEO snapshot, generated from the committed JSON.

    python -m src.snapshot

Writes reports/geo_snapshot.md. Every number is computed from data/*.json; the
few figures quoted in words are asserted against the stored evidence, so the
build fails rather than publish a stale sentence. Plain English for a reader who
has never seen the repo: no internal labels, page ids or claim ids.
"""

import json
import sys
from collections import Counter
from datetime import date

import yaml

from src import collection, config

ROOT = config.ROOT
OUT = ROOT / "reports" / "geo_snapshot.md"

PAGE_NAMES = {
    "S01": "the company page", "S02": "the homepage", "S04": "the business units page",
    "S06": "the water page", "S07": "the wastewater page", "S08": "the drinking water page",
    "S09": "the sludge page", "S10": "the digital services page", "S11": "the sustainability page",
    "S12": "the sustainability approach page", "S13": "the climate page", "S14": "the circularity page",
    "S16": "the sustainability indicators page", "S18": "the reports page", "S21": "the contacts page",
}
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def _load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def w(n):
    return WORDS.get(n, str(n))


def build():
    claims = {c["claim_key"]: c for c in _load("claims.json")["claims"]}
    verdicts = {v["claim_key"]: v for v in _load("verdicts.json")["verdicts"]}
    tallies = _load("tallies.json")
    gaps = _load("page_gaps.json")
    sfs = {f["id"]: f for f in _load("structural_findings.json")["findings"]}
    cfg = config.load()
    if set(claims) != set(verdicts):
        raise SystemExit("Every claim needs a confirmed verdict before the snapshot is built.")

    n_questions = len(cfg.questions["questions"])
    n_open = sum(1 for q in cfg.questions["questions"] if q["type"] == "open")
    assistants = [a["name"] for a in collection.load_assistants()]
    dates = set()
    for p in collection.RAW_DIR.glob("*_p[12].md"):
        f, _ = collection.parse(p)
        dates.add(f["collected_at"].date() if hasattr(f["collected_at"], "date") else date.fromisoformat(str(f["collected_at"])[:10]))
    run_date = min(dates)
    if dates != {run_date}:
        raise SystemExit(f"Answers span several dates {sorted(dates)}; update the method line.")

    v = Counter(x["verdict"] for x in verdicts.values())
    total = len(verdicts)
    contradicted = [k for k, x in verdicts.items() if x["verdict"] == "contradicted"]
    tiers = tallies["verdicts_by_frequency"]["tiers"]
    top = tiers["1_all_three_both_passes"]
    low_contra = sum(t["verdicts"].get(k, 0) for name, t in tiers.items() if not name.startswith("1")
                     for k in t["verdicts"] if k.startswith("contradicted"))
    assert top["verdicts"].get("supported", 0) + top["verdicts"].get("source_conflict", 0) + top["verdicts"].get("unverified", 0) == top["claims"]
    assert not any(k.startswith("contradicted") for k in top["verdicts"]), "top tier now has a contradiction; rewrite the headline"
    assert low_contra == len(contradicted)

    # Facts that all three assistants stated in both passes and that checked out.
    def ok(key):
        c, x = claims[key], verdicts[key]
        return x["verdict"] == "supported" and len(c["frequency"]["assistants"]) == 3 and c["frequency"]["passes"] == [1, 2]
    for key in ("hq_helsinki", "listing_nasdaq_helsinki", "revenue_2025", "employees_4900", "segments_three"):
        assert ok(key), key

    # Climate-target symmetry: all four versions are source conflicts, quoted figures checked.
    sym = ["target_scope12_2030", "target_scope3_2033", "target_scope12_51_2", "target_scope3_32_5"]
    assert all(verdicts[k]["verdict"] == "source_conflict" for k in sym)
    assert "-52%" in verdicts["target_scope12_2030"]["evidence"]["quote"]
    assert "51.23%" in verdicts["target_scope12_2030"]["conflicting_evidence"]["quote"]
    assert "33%" in verdicts["target_scope3_2033"]["evidence"]["quote"]
    assert "32.5%" in verdicts["target_scope3_2033"]["conflicting_evidence"]["quote"]
    assert "50%" in sfs["SF06"]["summary"] and "-52%" in sfs["SF06"]["summary"]
    hedge = claims["target_scope12_range_51_52"]
    assert verdicts["target_scope12_range_51_52"]["verdict"] == "supported" and hedge["frequency"]["assistants"] == ["chatgpt"]
    assert all(verdicts[k]["verdict"] == "source_conflict" for k in ("target_trif_2026", "target_trif_2025", "target_dei_2026"))
    plat = claims["ecovadis_platinum"]
    assert verdicts["ecovadis_platinum"]["verdict"] == "contradicted" and plat["frequency"]["assistants"] == ["gemini"] and plat["frequency"]["passes"] == [1, 2]

    # Share of voice.
    sov = tallies["share_of_voice"]
    ks = sov["kemira_summary"]
    comp = {c["company"]: c for c in sov["companies"]}
    snf = comp["SNF"]
    shifts = [x for x in sov["kemira_presence"] if x["position_stability"] != "same"]
    assert all(x["assistant"] == "gemini" and x["pass_2"]["first_named"] == "SNF" for x in shifts)

    # Citations.
    cit = tallies["citations"]
    agg = cit["aggregate_all_captured"]
    outside_pages = cit["kemira_pages_outside_sources_yaml"]
    captured = cfg.sources["sources"]
    cited_ids = {p["source_id"] for p in cit["kemira_pages"] if p["source_id"]}
    never = [s["id"] for s in captured if s["id"] not in cited_ids]
    assert "S09" in never
    o03_sludge_cites = [p for p in cit["kemira_pages"] if p["source_id"] == "S09"]
    assert not o03_sludge_cites
    chatgpt_open = [r for r in tallies["share_of_voice"]["answers"] if r["assistant"] == "chatgpt"]  # noqa: F841 (presence only)

    # Pages.
    da = gaps["direct_answer_summary"]
    investor_ids = [s["id"] for s in captured if "/investors/" in s["url"]]
    assert sorted(da["opens_with_date"]) == sorted(investor_ids), "date-first pages are no longer exactly the investor section"
    n_html = da["pages"]
    h1 = next(s for s in gaps["site_wide"] if s["id"] == "h1")
    no_h1 = int(h1["statement"].split(" of ")[0])
    ranked = gaps["pages"]
    first, second = ranked[0], ranked[1]
    assert first["source_id"] == "S11" and second["source_id"] == "S09"

    # Unresolved material and the criticisms question.
    unver = [k for k, x in verdicts.items() if x["verdict"] == "unverified"]
    k07 = [k for k in unver if "K07" in claims[k]["frequency"]["questions"]]
    cited_outside = [k for k in unver if verdicts[k].get("unverified_reason") == "cited_source_outside_set"]

    # Opening numbers.
    from src.tallies import domain, normalise_url
    s16 = json.loads((ROOT / "data" / "ground_truth" / "S16" / "meta.json").read_text(encoding="utf-8"))["text_chars"]
    assert "eurolandir" in json.dumps(sfs["SF01"]), "SF01 no longer records the third-party embed"
    cg_links = []
    for p in sorted(collection.RAW_DIR.glob("O0*_chatgpt_p*.md")):
        f, _ = collection.parse(p)
        cg_links += [normalise_url(u) for u in f["citations"]]
    cg_kemira = sum(1 for u in cg_links if domain(u) == "kemira.com")
    cg_other = [domain(u) for u in cg_links if domain(u) != "kemira.com"]
    supplier_domains = {"snf.com", "solenis.com", "ecolab.com", "feralco.eu", "feralco.com", "veoliawatertechnologies.com",
                        "watertechnologies.com", "kurita.eu", "kurita-water.com", "basf.com", "usalco.com",
                        "kuhlmann-europe.com", "venatorcorp.com", "brenntag.com", "univarsolutions.com",
                        "chemifloc.ie", "chemifloc.com", "separ-chemie.de"}
    assert set(cg_other) <= supplier_domains, f"non-supplier domains in ChatGPT open-question links: {set(cg_other) - supplier_domains}"
    # The 'carbon neutrality overall' sentence relies on a separate supply-chain (Scope 3) target in the captured set.
    assert verdicts["target_scope3_2033"]["evidence"]["source"] in {s["id"] for s in cfg.sources["sources"]}
    # 'None of the errors appeared in a claim more than one assistant made.'
    assert all(len(claims[k]["frequency"]["assistants"]) == 1 for k in contradicted)

    names = ", ".join(assistants[:-1]) + " and " + assistants[-1]
    answers_n = da["judgement"]["answers"]
    date_n = len(da["opens_with_date"])
    wrong_by = {a for k in contradicted for a in claims[k]["frequency"]["assistants"]}
    assert wrong_by == {"gemini"}, "contradictions no longer all from Gemini; rewrite that sentence"
    unclear = [k for k in contradicted if verdicts[k]["contradiction_type"] == "source_unclear"]
    assert unclear == ["carbon_neutrality_overall"]
    lines = [
        "# What AI assistants say about Kemira",
        "",
        f"*GEO snapshot · answers collected {run_date.day} {run_date.strftime('%B %Y')} · independent audit, not affiliated with Kemira*",
        "",
        f"- **{s16} characters.** That is all the readable text on Kemira's sustainability key indicators page. The figures load from a third-party service, so an assistant reading the page sees almost nothing.",
        f"- **{len(cg_other)} of {len(cg_links)}.** ChatGPT's links on the {w(n_open)} questions that name no company: {len(cg_other)} go to other chemical suppliers' websites, {w(cg_kemira)} to kemira.com.",
        f"- **{w(answers_n).capitalize()} of {n_html}.** Kemira pages that open with an answer to the question they exist for.",
        "",
        f"**How this was done.** We asked {names} the same {w(n_questions)} questions, each twice in separate sessions, logged out, "
        f"and checked every claim they made about Kemira against {len(captured)} Kemira pages and reports captured beforehand. The README has the full method.",
        "",
        "## The short answer",
        "",
        f"The assistants made **{total} distinct claims** about Kemira. **{v['supported']} checked out and {w(len(contradicted))} conflicted with Kemira's material.** "
        f"The rest fall into two groups: {v['unverified']} that the Kemira material we checked doesn't address, and {w(v['source_conflict'])} where "
        "Kemira's own pages and reports give different figures. The assistants are rarely wrong about Kemira. The gaps are in what the pages "
        "don't cover and in figures the pages disagree on.",
        "",
        f"The more often a claim was repeated, the safer it was. Of the {top['claims']} claims all three assistants made in both sessions, **none was wrong**: "
        f"{top['verdicts']['supported']} checked out, {w(top['verdicts']['source_conflict'])} were figures Kemira itself states differently in different places, "
        f"and {w(top['verdicts']['unverified'])} wasn't addressed. None of the errors appeared in a claim more than one assistant made.",
        "",
        "## What they get right",
        "",
        "All three, in both sessions, get the basic facts right: headquarters, listing, 2025 revenue (about €2.8 billion), "
        "headcount (about 4,900) and business units.",
        "",
        f"Asked {w(n_open)} questions about water treatment suppliers that name no company, **every assistant named Kemira in every answer, "
        f"{ks['named_in']} of {ks['of_answers']}, and first in {ks['named_first']}.** Its main rival, SNF, was also named in all {snf['answers_named']}, "
        f"but first in only {w(snf['named_first'])}, so what sets Kemira apart is being named first. Gemini named SNF first in {w(len(shifts))} "
        f"of the {w(n_open)} questions in its second session, after putting Kemira first in its first.",
        "",
        "## What they get wrong",
        "",
        f"All {w(len(contradicted))} errors came from Gemini. It said, in both sessions, that Kemira holds an EcoVadis Platinum sustainability rating; "
        "Kemira reports Gold. It garbled Kemira's list of sustainability priorities. And it said Kemira aims for carbon neutrality \"overall\". "
        "Kemira's 2045 target covers its own operations and the energy it buys; emissions from its supply chain sit under a separate reduction target.",
        "",
        "## Where the assistants disagree, and why",
        "",
        "Assistants gave Kemira's main climate target as either a 52% emissions cut by 2030 or 51.23%. Both are Kemira's figures: "
        "its climate page says 52%, its financial reports say 51.23%. **Whichever figure an assistant gave, it matched one Kemira source "
        "and contradicted another**, so the divergence starts in Kemira's own material. A second climate target and two target dates split "
        "the same way. One ChatGPT answer said \"approximately 51–52%\", spanning both.",
        "",
        "## What is missing",
        "",
        f"For {v['unverified']} claims, the Kemira material we checked has nothing to confirm or contradict them. "
        f"{len(k07)} of the {v['unverified']} came from one question, \"Is Kemira a sustainable company? What are the criticisms?\", "
        "where assistants raised reputational and regulatory material that Kemira's pages don't discuss.",
        "",
        "## Where the assistants look, and what they find",
        "",
        f"**{agg['kemira_com']} of the {agg['citations']} links the assistants gave point to kemira.com**, so Kemira's own site is their main source. "
        f"But they reach different pages from the ones built to answer the question: they cited {outside_pages} Kemira pages outside our set, "
        f"while {len(never)} of the {len(captured)} we checked were never cited. **The sludge page was never cited, even in answers about reducing sludge.**",
        "",
        f"**{w(date_n).capitalize()} of {n_html} pages open with a date rather than an answer, and those {w(date_n)} are the whole investor section.** No page carries the hidden label that tells software it describes a company, "
        f"and {no_h1} of {n_html} have no title heading in their code. Every page lacks the same things. "
        f"Of the unresolved claims we could trace to a page, most belong to two: {PAGE_NAMES[first['source_id']]} ({first['claims_settled']} claims, "
        f"made {first['instances_settled']} times across the answers) and {PAGE_NAMES[second['source_id']]} "
        f"({second['claims_settled']} claims, made {second['instances_settled']} times).",
        "",
        "---",
        "",
        f"*One run, one day, from Finland. Assistants change without notice; these findings describe what they said on "
        f"{run_date.day} {run_date.strftime('%B %Y')}, not facts about Kemira. Generated from this repository's data by `src/snapshot.py`. "
        "ChatGPT's links are those inside its answer text, which may differ from the sources its interface showed.*",
        "",
    ]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    words = sum(len(l.split()) for l in lines)
    print(f"Wrote {OUT.relative_to(ROOT)} ({words} words).")
    return 0


if __name__ == "__main__":
    sys.exit(build())
