# Kemira GEO Audit

**What do AI assistants say about Kemira, how much of it is right, and which web pages should change?**

This tool runs a fixed battery of questions about Kemira through three consumer AI assistants, extracts the factual claims from their answers, checks each claim against Kemira's own published material, and records which sources the assistants cite. It runs the same battery against peer companies to measure share of voice. Every wrong or missing claim is traced back to the kemira.com page that should have answered it, producing a ranked list of pages to fix.

Kemira is a Nasdaq Helsinki-listed company in sustainable chemistry for water-intensive industries. This is an independent audit, not affiliated with or endorsed by Kemira.

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

### Models and run date

| Assistant | Model / surface | Browsing | Date collected |
|---|---|---|---|
| _[assistant 1]_ | _[model version as reported by the surface]_ | _[on / off]_ | _[date]_ |
| _[assistant 2]_ | _[model version]_ | _[on / off]_ | _[date]_ |
| _[assistant 3]_ | _[model version]_ | _[on / off]_ | _[date]_ |

Model versions served to anonymous users are not always disclosed; where the surface did not state one, this is recorded as unknown rather than inferred.

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

**No model grades another model.** Verdicts are made against the ground truth store, and every verdict carries the evidence snippet it rests on, so a reader who doesn't trust this code can check the judgment directly.

Contradictions carry a second field distinguishing **`assistant_wrong`** (the published material is clear and the assistant departed from it) from **`source_unclear`** (the published material is ambiguous, stale, or silent). These lead to different fixes, and the second is usually the more actionable one.

### The unverified bucket

_[N]_ of _[N]_ claims (_[N]%_) resolved to `unverified`.

This bucket is reported rather than minimised. A large unverified share is itself informative: it means assistants are asserting things about Kemira that Kemira's own published material does not address, which is a content gap before it is an accuracy problem.

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

_[Generated from the run. See `reports/geo_snapshot.md` for the one-page version and the dashboard for the full claim table, share-of-voice counts and ranked page list.]_

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
6. **English only, Finland-routed.**
7. **Manual collection means a small sample.** Breadth was traded for fidelity to the actual consumer experience.

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

reports/geo_snapshot.md   one-page summary
```

Every stage writes a committed file and can be rebuilt from the stage before it. The raw logs are never edited after commit — if the logs are sound, every downstream step is checkable independently of this code.

---

## Running it

_[Install and run instructions.]_

The dashboard reads from committed JSON. It makes no live calls to any assistant and will render identically whenever it is opened.

---

## Author

Built by Talha Malik ([github.com/tsm765](https://github.com/tsm765)) as a portfolio project, October 2026.

Independent work. Not affiliated with, commissioned by, or endorsed by Kemira Oyj.
