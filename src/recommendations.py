"""S9b: the recommendations, generated like the snapshot so the numbers cannot drift.

    python -m src.recommendations

Writes reports/recommendations.md. The text is the author's signed opinion,
kept verbatim; every number in it is asserted against the committed data before
the file is written, and the build fails rather than publish a stale figure.

The dashboard reads RECOMMENDATIONS from this module (or parses the Markdown,
which has one '## N' section per recommendation: statement paragraph in bold,
then the expansion paragraph).
"""

import json
import sys

import yaml

from src import collection, config

ROOT = config.ROOT
OUT = ROOT / "reports" / "recommendations.md"

TITLE = "What I would do: five changes to kemira.com"
HEADER = ("*Signed opinion by Talha Malik, not audit output. Everything else in this repository describes what was found; "
          "this file says what I would do.*")

RECOMMENDATIONS = [
    {
        "number": 1,
        "statement": ("Kemira’s own pages and reports give different numbers for the same climate target, so assistants repeat "
                      "whichever one they happened to read. Every page and report needs to state one figure and one date."),
        "expansion": ("The climate page says 52%. Both financial reports say 51.23%. The sustainability page says both 50% and 52%. "
                      "The second climate target splits the same way, 33% or 32.5%, and two target dates moved between the annual "
                      "and the half-year report. Eight of the claims assistants made, repeated 27 times across the answers, trace "
                      "back to this. It is a handful of edits on two web pages."),
    },
    {
        "number": 2,
        "statement": ("The sustainability figures load from an outside service and the half-year report sits on another company’s "
                      "site, so an assistant reading kemira.com finds neither. Both need to be text on Kemira’s own pages."),
        "expansion": ("The sustainability key indicators page contains 38 characters of readable text, because the figures arrive "
                      "from a third-party service after the page loads. The January to June 2026 half-year report is published on "
                      "a press-release service rather than kemira.com, and the reports index links no interim report at all. An "
                      "assistant restricted to Kemira’s own domain reaches none of it. Hosting the reports on kemira.com and "
                      "linking them from the reports index would put them where assistants already search."),
    },
    {
        "number": 3,
        "statement": ("No Kemira page carries the hidden label that tells software “this page belongs to Kemira”, and 19 of 21 "
                      "have no main title in their code. One change to the page template adds both everywhere."),
        "expansion": ("All 21 pages carry the same default set of tags, and none of them identifies an organisation. Nineteen have "
                      "no main heading; the homepage’s are carousel slides. One page on the site has a question and answer "
                      "section, it carries no markup saying so, and no assistant cited it. Adding both is standard practice and "
                      "roughly a day’s work for a developer. This audit cannot show it would change what assistants cite, because "
                      "every page lacked the same things and there was nothing to compare against."),
    },
    {
        "number": 4,
        "statement": ("Most pages open with a date or a tagline rather than the answer, and the opening is what an assistant reads "
                      "first. Each page should lead with the answer."),
        "expansion": ("Two of 21 pages open with an answer to the question the page exists for. Nine partly do. Ten do not. Seven "
                      "open with a date, and those seven are the entire investor section, which is where analysts and journalists "
                      "look. There is no proof this costs citations: one page that opens with a date was cited six times. But the "
                      "opening is what both a reader and an assistant take first, and it is a one-line change per page."),
    },
    {
        "number": 5,
        "statement": ("Asked how to reduce sludge, the assistants never linked to Kemira’s sludge page, even though it exists. The "
                      "page needs the case results and product names so that it is cited."),
        "expansion": ("None of the links the assistants gave across the 60 answers pointed to the sludge page, including the 28 "
                      "links in the six answers about reducing sludge volume at a municipal plant. Case-study pages elsewhere on "
                      "kemira.com were cited 11 times in the same run. Five claims the captured material could not settle trace "
                      "back to this page, second only to the sustainability page. Why assistants do not reach it is not "
                      "established here. The pages they do reach carry named cases, results and products; this one does not."),
    },
]


def _load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def verify():
    """Assert every number the text states against the committed data."""
    claims = {c["claim_key"]: c for c in _load("claims.json")["claims"]}
    verdicts = {v["claim_key"]: v for v in _load("verdicts.json")["verdicts"]}
    tallies = _load("tallies.json")
    gaps = _load("page_gaps.json")
    sfs = {f["id"]: f for f in _load("structural_findings.json")["findings"]}
    sources = yaml.safe_load((ROOT / "sources.yaml").read_text(encoding="utf-8"))["sources"]

    # 1. Climate figures and the eight conflicting claims.
    assert "-52%" in verdicts["target_scope12_2030"]["evidence"]["quote"]               # climate page 52%
    assert verdicts["target_scope12_2030"]["evidence"]["source"] == "S13"
    assert "51.23%" in verdicts["target_scope12_2030"]["conflicting_evidence"]["quote"]  # annual report
    assert "51.23%" in sfs["SF06"]["summary"] and "half-year" in sfs["SF06"]["summary"]  # both financial reports
    assert "by 50%" in sfs["SF06"]["summary"] and "-52%" in sfs["SF06"]["summary"]       # sustainability page both
    assert "33%" in verdicts["target_scope3_2033"]["evidence"]["quote"]
    assert "32.5%" in verdicts["target_scope3_2033"]["conflicting_evidence"]["quote"]
    assert verdicts["target_trif_2026"]["verdict"] == verdicts["target_dei_2026"]["verdict"] == "source_conflict"
    conflict = [k for k, v in verdicts.items() if v["verdict"] == "source_conflict"]
    assert len(conflict) == 8, len(conflict)
    assert sum(claims[k]["frequency"]["instances"] for k in conflict) == 27

    # 2. Indicators embed, half-year report hosting, reports index.
    assert _json(ROOT / "data" / "ground_truth" / "S16" / "meta.json")["text_chars"] == 38
    assert "eurolandir" in json.dumps(sfs["SF01"])
    assert "mb.cision.com" in sfs["SF04"]["summary"]
    assert "links no interim or half-year report" in sfs["SF03"]["summary"]

    # 3. No organisation tag, no main heading, one FAQ page uncited and unmarked.
    html_ids = [s["id"] for s in sources if (ROOT / "data" / "ground_truth" / s["id"] / "meta.json").exists()
                and _json(ROOT / "data" / "ground_truth" / s["id"] / "meta.json").get("schema_types") is not None]
    assert len(html_ids) == 21, len(html_ids)
    metas = {sid: _json(ROOT / "data" / "ground_truth" / sid / "meta.json") for sid in html_ids}
    assert not any(t in m["schema_types"] for m in metas.values() for t in ("Organization", "Corporation"))
    h1 = next(s for s in gaps["site_wide"] if s["id"] == "h1")["statement"]
    assert h1.startswith("19 of 21") and "carousel" in h1
    faq_pages = [sid for sid, m in metas.items() if m["faq_block"]["present"]]
    assert faq_pages == ["S19"] and "FAQPage" not in metas["S19"]["schema_types"]
    cited = {p["source_id"] for p in tallies["citations"]["kemira_pages"] if p["source_id"]}
    assert "S19" not in cited

    # 4. Direct-answer openings.
    da = gaps["direct_answer_summary"]
    assert da["pages"] == 21 and da["judgement"] == {"answers": 2, "partial": 9, "no": 10}
    investor = sorted(s["id"] for s in sources if "/investors/" in s["url"])
    assert sorted(da["opens_with_date"]) == investor and len(investor) == 7
    date_cites = {sid: sum(p["count"] for p in tallies["citations"]["kemira_pages"] if p["source_id"] == sid)
                  for sid in da["opens_with_date"]}
    assert sorted(n for n in date_cites.values() if n) == [6], date_cites

    # 5. The sludge page.
    assert "S09" not in cited
    raw = sorted(collection.RAW_DIR.glob("*_p[12].md"))
    assert len(raw) == 60
    o03_links = 0
    for p in raw:
        front, body = collection.parse(p)
        shown = front.get("citations_displayed")
        urls = front["citations"] + (shown if isinstance(shown, list) else [])
        assert not any("kemira.com/water/sludge" in u for u in urls) and "kemira.com/water/sludge" not in body
        if p.name.startswith("O03_"):
            o03_links += len(urls)
    assert len(list(collection.RAW_DIR.glob("O03_*_p[12].md"))) == 6 and o03_links == 28, o03_links
    stories = sum(p["count"] for p in tallies["citations"]["kemira_pages"] if "/stories/" in p["url"])
    assert stories == 11, stories
    ranked = gaps["pages"]
    assert ranked[0]["source_id"] == "S11" and ranked[1]["source_id"] == "S09" and ranked[1]["claims_settled"] == 5

    # Register: no em dashes, no audit-voice recommendation.
    text = " ".join([TITLE, HEADER] + [r["statement"] + r["expansion"] for r in RECOMMENDATIONS])
    assert "—" not in text and "the audit recommends" not in text.lower()


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build():
    verify()
    lines = [f"# {TITLE}", "", HEADER, ""]
    for r in RECOMMENDATIONS:
        lines += [f"## {r['number']}", "", f"**{r['statement']}**", "", r["expansion"], ""]
    lines += ["---", "",
              "*Every figure above is checked against this repository's data by `src/recommendations.py` before the file is "
              "written. The findings themselves are in `reports/geo_snapshot.md`.*", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(RECOMMENDATIONS)} recommendations, all figures verified.")
    return 0


if __name__ == "__main__":
    sys.exit(build())
