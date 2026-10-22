# Kemira GEO Audit

**What do AI assistants say about Kemira, how much of it is right, and which web pages should change?**

This tool runs a fixed battery of questions about Kemira through three consumer AI assistants, extracts the factual claims from their answers, checks each claim against Kemira's own published material, and records which sources the assistants cite. It runs the same battery against peer companies to measure share of voice. Every wrong or missing claim is traced back to the kemira.com page that should have answered it, producing a ranked list of pages to fix.

Kemira is a Nasdaq Helsinki-listed company in sustainable chemistry for water-intensive industries. This is an independent audit, not affiliated with or endorsed by Kemira.

**Results:** [Dashboard](https://tsm765.github.io/kemira-geo-audit/dashboard/) · [One-page snapshot](reports/geo_snapshot.md) · [What I would do (signed opinion)](reports/recommendations.md)

---

## Why generative engine optimization

Search used to send people to a page. Increasingly, an assistant answers the question itself and the page is never visited — or is visited, summarised, and attributed to someone else. For a company, that shifts the question from *where do we rank* to *what do models say about us, and whose page did they read to say it*.

That makes three things measurable: **accuracy** (is what the model says true), **citation** (does it point at your material or someone else's), and **share of voice** (when a buyer asks an open question in your category, are you named at all).

This tool measures those three.

---

## Method

### Collection

Answers are collected **by hand from consumer interfaces**, not from model APIs. The API response and the chat response differ, sometimes substantially, and the chat response is what a customer, investor or journalist actually sees. Measuring the API would be easier and would answer a different question.

All sessions were run **logged out, in a private browsing window**, to remove personalisation from account history.

> **This is not the same as neutrality.** Logged-out sessions are still shaped by geographic routing (these were run from Finland, so likely EU-specific behaviour), by whichever default model version is served to anonymous users, and by any A/B bucketing invisible from outside. The claim here is narrow: *no personalisation from a signed-in history*.

Each question was asked **twice, in separate sessions**. A single pass cannot distinguish a stable model belief from one answer's variance. Claims that appeared in only one of the two passes are flagged as unstable rather than reported as findings.

**Citation capture.** For each answer, `citations` holds the URLs present in the copied answer text, extracted automatically. In pass 2, `citations_displayed` also records, by hand, the URLs behind the interface's source chips, or `not_captured` where the chips were not checked. On a small number of ChatGPT and Perplexity cells, chip sources were checked against the inline URLs the extractor captured and matched exactly; this was not verified systematically.

### Models and run date

| Assistant | Model / surface | Browsing | Date collected |
|---|---|---|---|
| Perplexity | unknown (not displayed to logged-out users) | on | 20 October 2026 |
| ChatGPT | unknown (not displayed to logged-out users) | on | 20 October 2026 |
| Gemini | 3.5 Flash-Lite (as selected in the model picker; other models required sign-in) | on | 20 October 2026 |

Model versions served to anonymous users are not always disclosed; where the surface did not state one, this is recorded as unknown rather than inferred. Both sessions ran on the same day, several hours apart.

The ten second-session Gemini files in `data/raw/` record `browsing: off`. That is a recording error: Gemini returned web sources on every answer in both sessions. The raw files are frozen and were not edited; this note is the correction.

**Findings are a snapshot of a specific date.** These systems change without notice. An answer collected in October 2026 is not evidence about January 2027.

### Ground truth

Claims are checked against Kemira's own published material — pages on kemira.com and the 2025 annual report — scraped into `data/ground_truth/` **before any assistant answers were collected**, so the reference set could not be shaped to fit what the models happened to say. Sources are listed in `sources.yaml`.

### Adjudication

Each extracted claim is marked:

| Verdict | Meaning |
|---|---|
| `supported` | Matches Kemira's published material |
| `contradicted` | Conflicts with Kemira's published material |
| `unverified` | Neither confirmed nor contradicted by available ground truth |
| `source_conflict` | The claim matches part of Kemira’s published material and conflicts with another part of it. The ground truth cannot settle it because the sources disagree with each other. |

`source_conflict` is the only verdict that cites two passages. The disagreement between them is the evidence, so both are quoted in full.

**No model grades another model.** Verdicts are made against the ground truth store, and every verdict carries the evidence snippet it rests on, so a reader who doesn't trust this code can check the judgment directly.

Contradictions carry a second field distinguishing **`assistant_wrong`** (the published material is clear and the assistant departed from it) from **`source_unclear`** (the published material is ambiguous, stale, or silent). These lead to different fixes, and the second is usually the more actionable one.

### The unverified bucket

34 of 123 claims (28%) resolved to `unverified`.

`unverified` means the claim was not settled by the 22 captured sources. It is not a finding that the claim is wrong, and it is not a statement about anything Kemira publishes elsewhere. Three sub-reasons qualify it further where they can be told:

| Sub-reason | Meaning | Claims |
|---|---|---|
| `cited_source_outside_set` | the assistant named a kemira.com page outside the captured set as its source for that claim; nothing is asserted about what that page says | 8 |
| `outside_ground_truth` | related material exists elsewhere on kemira.com but is not in the captured set, a limit of this audit | 2 |
| `not_addressed` | Kemira's published material does not cover it, a content gap | 0 |
| unset | cannot be told without looking beyond the captured set | 24 |

No claim is marked `not_addressed`, because establishing that Kemira publishes nothing on a point would require looking beyond the captured set. This audit therefore reports no count of content gaps in Kemira's material, only claims its captured material does not settle.

This bucket is reported rather than minimised. The ground truth set is fixed rather than extended when a claim does not resolve, for two reasons: a fixed set is what makes the unverified count meaningful, and a fact that lives only outside the captured set is itself a GEO-relevant observation about discoverability.

---

## Peer selection and share of voice

Kemira competes against different sets in different segments:

| Kemira area | Main peers |
|---|---|
| Water Solutions – polymers | SNF, Solvay, Ecolab, Solenis |
| Water Solutions – coagulants | Feralco, USALCO, Chemtrade |
| Packaging & Hygiene Solutions | Solenis, SNF, Ecolab, Buckman |
| Fiber Essentials | Nouryon, Solvay, ERCO, Chemtrade |

Running all four would be four separate experiments with four different baselines. This audit covers **Water Solutions**, Kemira's core segment, with **Solenis, SNF and Ecolab** as comparators.

Share of voice is measured on open questions that name no company at all — e.g. asking who supplies water treatment chemicals in Europe — and counting who comes back. Peers were selected from Kemira's own segment reporting rather than by asking an assistant, which would have made the baseline circular.

---

## Findings

The [one-page snapshot](reports/geo_snapshot.md) states the findings; the [dashboard](https://tsm765.github.io/kemira-geo-audit/dashboard/) shows them with the full claim table and share-of-voice counts. The ranked page list is in `data/page_gaps.json`. In short: of 123 distinct claims, 78 checked out and 3 conflicted with Kemira's material; 34 were not settled by the captured material and 8 matched one Kemira source while conflicting with another. None of the 30 claims made by all three assistants in both sessions conflicted with Kemira's material.

**All findings in this repository are findings about assistant behaviour.** They take the form *"assistant X stated Y on date Z; Kemira's published material states W"*. Nothing here is a claim about Kemira's disclosures, and no finding should be read as one.

---

## Scope

**In scope:** measuring how assistants describe Kemira (accuracy, citations, share of voice vs peers); a prototype monitoring dashboard showing one run; diagnosis of which kemira.com pages would fix the most claims and what each lacks.

**Deliberately out of scope:**

- Writing or restructuring kemira.com content, or generating schema markup for Kemira. This audit diagnoses; it does not author material for a company it has no mandate from.
- Time-series monitoring. One run, two passes. No trending, no scheduled re-runs.
- Segments other than Water Solutions.
- Languages other than English. Finnish and Dutch GEO is a real question and a larger one.
- Model APIs (see Collection).

These are stated because a reader should know what the numbers do and don't cover.

---

## Limits

1. **One run, one date.** A snapshot, not a trend.
2. **Three assistants.** Not a census of how AI systems describe Kemira.
3. **Logged-out is not neutral.** See Collection.
4. **Ground truth is only as complete as the sources scraped.** The `unverified` bucket is partly a measure of this tool's reach, not only of Kemira's content gaps.
5. **Claim extraction involves judgment.** Where an answer is vague, deciding what counts as one discrete factual claim is a call, and a different reasonable person would split some of them differently.
6. **English only, Finland-routed.** During collection the Gemini interface rendered in Finnish, confirming that these sessions were routed to a Finland locale. This is an observation about these sessions, not a claim about how routing works generally.
7. **Manual collection means a small sample.** Breadth was traded for fidelity to the actual consumer experience.
8. **Model identity is not exposed to anonymous users.** None of the three surfaces shows logged-out users which model produced an answer, so the models table records what each interface displayed rather than an inferred version. This is itself a constraint on GEO reproducibility: an auditor cannot pin which system produced a given answer.
9. **No citation data could be captured for Gemini in the first session.** During that session, Gemini displayed retrieval indicators on every answer, but the interface's copy function did not carry resolvable source URLs into the copied text. This describes what the copy function returned in these sessions, not how Gemini handles citations generally. In the second session, Gemini's sources were recorded by hand from the interface's source chips (36 links), so Gemini's citation figures cover the second session only and are not comparable with its first.
10. **ChatGPT citations are inline links.** ChatGPT’s citation markers did not resolve to URLs in the copied text; the URLs captured for ChatGPT are inline links within the answer body, which may not match the sources the interface displayed.

---

## Repository layout

```
questions.yaml            question battery (Kemira + open category questions)
peers.yaml                comparator set and selection reasoning
sources.yaml              ground truth URLs and documents

data/raw/                 verbatim answers, immutable after commit
data/ground_truth/        scraped Kemira material
data/claims.json          extracted claims, each linked to its raw file
data/verdicts.json        adjudication with evidence snippets
data/tallies.json         cited domains, share-of-voice counts
data/page_gaps.json       ranked page list

reports/geo_snapshot.md   one-page summary, generated from the JSON by src/snapshot.py;
                          renders to PDF (src/render_snapshot.py) and Word
                          (src/render_snapshot_docx.js); neither rendered file is committed
reports/recommendations.md
                          signed opinion, generated by src/recommendations.py

dashboard/                static site (GitHub Pages, served from the repo root)
dashboard/data.json       every figure the dashboard shows, generated by
                          src/dashboard_data.py from data/ with assertions
dashboard/index.html      page structure; app.js renders it from data.json and
dashboard/app.js          reads the recommendations tab from reports/recommendations.md
dashboard/style.css
```

Every stage writes a committed file and can be rebuilt from the stage before it. The raw logs are never edited after commit — if the logs are sound, every downstream step is checkable independently of this code.

---

## Running it

Python 3 with the packages in `requirements.txt`:

```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      (Windows; .venv/bin/pip elsewhere)
```

Each stage is a module run from the repository root, for example `python -m src.tallies`, `python -m src.snapshot`, `python -m src.recommendations`. Each rebuilds its output from the committed files of the stage before and fails rather than writing a figure its assertions do not confirm. The captured ground-truth text and source PDFs are not in the repository (only each source's `meta.json` is committed, and short quoted passages appear in `verdicts.json`), so stages that quote them need a fresh capture to rerun from scratch.

The dashboard reads from committed JSON. It makes no live calls to any assistant and will render identically whenever it is opened.

To rebuild its data after any change upstream, then preview it locally (it fetches its data, so it needs a server rather than opening the file directly):

```
python -m src.dashboard_data
python -m http.server 8765
```

and open `http://localhost:8765/dashboard/`.

---

## Author

Built by Talha Malik ([github.com/tsm765](https://github.com/tsm765)) as a portfolio project, October 2026.

Independent work. Not affiliated with, commissioned by, or endorsed by Kemira Oyj.
