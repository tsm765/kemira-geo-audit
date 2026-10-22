# Observations

Narrative observations supported by the data that are neither structural findings (`data/structural_findings.json`) nor verdicts (`data/verdicts.json`). They are kept here so they survive to S8 and the presentation.

**Rules for this file**

- Every observation carries its counts and names the file the counts come from.
- Nothing goes in that the data does not support. Anything speculative is marked **Hypothesis**.
- Observations are about assistant behaviour, never claims about Kemira. Where an observation concerns Kemira's pages, it points to the structural finding that records it rather than restating it.
- All figures are from one run collected on 2026-10-20 (two passes, three assistants, ten questions). Citation figures are measured differently per assistant and pass; see the caveat in `data/tallies.json` before comparing them.

---

## Citation patterns (S6)

### 1. Each assistant has a distinct sourcing character

Of the citations that do not point to kemira.com:

| Assistant | Non-kemira.com citations | Character | Counts |
|---|---|---|---|
| Perplexity | 45 | Market-research and data aggregators | 28 of 45 are aggregator domains (marketscreener 6, nexdigm 4, chemicalresearchinsight 4, mordorintelligence 3, plus 6wresearch, marketdataforecast, usdanalytics, bwdstrategic, morganreedinsights, marketsandmarkets, pmarketresearch) |
| ChatGPT | 41 | Competitors' and suppliers' own websites | 40 of 46 ChatGPT citations in the open questions are supplier sites; see 2 |
| Gemini | 16 | Scattered | 16 citations across 15 different domains; no domain cited more than twice (orege.com 2) |

Implication: there is no single answer to "what do AI assistants say about Kemira". The sources behind the answer vary by surface, so remediation may need to differ per surface too.

Sources: `data/tallies.json` (citations.by_assistant). Perplexity and ChatGPT figures are inline URLs from both passes; Gemini's are pass-2 source-chip URLs only.

### 2. ChatGPT links prospects to Kemira's competitors in open category questions

In the three open questions, ChatGPT's 46 citations break down as 40 links to supplier websites and 6 to kemira.com. The supplier links: snf.com 6, solenis.com 5, ecolab.com 5, Feralco 5 (feralco.eu 3, feralco.com 2), Veolia 5 (veoliawatertechnologies.com 3, watertechnologies.com 2), Kurita 3, basf.com 2, usalco.com 2, Chemifloc 2, and one each for kuhlmann-europe.com, venatorcorp.com, brenntag.com, univarsolutions.com and separ-chemie.de. ChatGPT cites no competitor site in any Kemira-named question.

A prospect asking ChatGPT an open category question is handed links to Kemira's competitors alongside Kemira. ChatGPT's links carry `?utm_source=chatgpt.com` (SF05), so this traffic is identifiable on whichever site receives it.

Sources: `data/raw/O0*_chatgpt_p*.md` citations fields; `data/tallies.json`. Caveat: ChatGPT URLs are inline links in the answer body, which may not match the sources the interface displayed (README limit 10).

### 3. Wikipedia appears once in 208 citations

The only Wikipedia citation in the run is one Gemini source chip (K02, pass 2). Perplexity and ChatGPT cite Wikipedia zero times in 172 citations.

A common GEO assumption is that Wikipedia drives what models say about a company. In this run it does not: kemira.com is 106 of 208 citations (51.0%), and the next-largest single domains are snf.com (7), marketscreener.com (6) and solenis.com (6).

Sources: `data/tallies.json` (citations.aggregate_all_captured).

### 4. Cited kemira.com pages concentrate on `/stories/` and other pages outside the captured set (pending S7)

Assistants cite 36 distinct kemira.com pages; 11 are in the captured set, 25 are not (57 and 49 citations respectively). The full 2025 annual report PDF counts as captured, since it is S17's content. The most-cited:

| kemira.com page | Citations | In captured set |
|---|---|---|
| Homepage `/` | 12 | S02 |
| `/water` | 9 | S06 |
| `/investors/kemira-as-an-investment` | 8 | no |
| `/annual-report-2025` (landing page) | 7 | S17 |
| `/company` | 6 | S01 |
| `/investors/kemira-as-an-investment/business-units-markets` | 6 | S04 |
| `/investors/kemira-as-an-investment/growth-drivers` | 6 | no |
| `/sustainability-initiatives` | 5 | S11 |

 Among the 25, the `/stories/` case-study pages account for 11 citations across 6 pages (Perplexity 9, Gemini 2; K05 5, O03 4, K04 2). Others outside the set include the investor page `/investors/kemira-as-an-investment` (8 citations, the third most-cited kemira.com page), `/growth-drivers` (6), the industrial-water-services product page (4), the annual review PDF, the 2022 and 2023 sustainability report PDFs, an April 2026 investor presentation, Finnish-language pages and a pages.kemira.com handbook. 12 of the 106 kemira.com citations are PDFs.

8 of the 34 unverified claims carry `unverified_reason: cited_source_outside_set`: the assistant named a kemira.com page outside the captured set as its source for that specific claim (same line or table row in the answer). All 8 are Perplexity; 4 cite a `/stories/` page (the Joensuu, BIOFOS and Prague cases, XD-5000), the others a 2022 or 2023 sustainability report, an investor presentation and a news page. The label records what the answer shows; it asserts nothing about what those pages say. Two further unverified K07 claims cite the full 2025 annual report PDF, which is captured (S17) and does not state them.

**Hypothesis:** narrative and case-study pages are what assistants reach; product and service pages are not. S7 tests this against the page-structure signals in meta.json; until then it is not a finding.

Sources: `data/tallies.json` (citations.kemira_pages).

### 5. Most captured sources are never cited, including the sludge page

12 of the 22 captured sources are cited by no assistant in either pass:

- S03 strategy and business model, S05 outlook and financial targets, S18 reports and presentations, S19 investor FAQ, S20 share information, S16 sustainability key indicators (investor pages)
- S09 sludge, S10 digital services (water pages)
- S14 circularity, S15 water stewardship (sustainability pages)
- S21 contacts
- S22 the half-year report (hosted on mb.cision.com, SF04)

S09, Kemira's sludge page, is not cited even in O03, the buyer-intent question about reducing sludge volume. The captured sources that are cited: S01, S02, S04, S06, S07, S08, S11, S12, S13, S17.

Sources: `data/tallies.json` (citations.kemira_pages, source_id field). Feeds S7.

### 6. Gemini's source chips include Finnish-language kemira.com pages

4 of Gemini's 20 kemira.com source chips are Finnish-language pages (`/fi`, `/fi/konserni`, `/fi/tuotteet-palvelut` twice), for questions asked in English. The Gemini interface rendered in Finnish during collection (README limit 6). **Hypothesis:** the locale the session was routed to influences which language version of the site Gemini retrieves. Not tested; one run, one location.

Sources: `data/raw/*_gemini_p2.md` citations_displayed.

### 6a. Cited captured pages sit higher in the site than uncited ones (hypothesis)

**Hypothesis, not a finding.** Of the captured pages, those cited are mostly top-level hubs (homepage, `/company`, `/water`, `/sustainability-initiatives`, the annual report); those never cited are mostly deeper leaf pages (`/water/sludge`, `/water/digital-services`, the circularity and water-stewardship subpages, the investor subpages). Mean URL path depth is about 1.6 for the 10 cited HTML pages against about 2.5 for the 11 never-cited HTML pages. Counter-examples: `/water/wastewater` and `/water/raw-water-drinking-water` are cited at depth 2; `/contacts` is not cited at depth 1. n is small (21 HTML pages, one run).

By contrast, the structural signals captured in S2 cannot explain citation at all, because they do not vary: every captured page carries the same default schema set and only S19 has an FAQ block (never cited). See SF02.

Sources: `data/tallies.json` (kemira_pages); `data/ground_truth/*/meta.json`.

### 6b. The `/stories/` hypothesis cannot be tested from captured data

The suggestion that narrative and case-study pages are what assistants reach (observation 4) cannot be tested against page structure, because the `/stories/` pages were never captured: the ground truth set was fixed before collection. This is a limit of the audit, not a negative result.

---

## Share of voice (S6)

### 7. Kemira is named in every open answer, and so is SNF

Kemira is named in all 18 open-question answers (3 questions, 3 assistants, 2 passes) and named first in 16, with a mean position of 1.11. SNF is also named in all 18, but first in 2 (mean position 3.0). Solenis is named in 16 (mean 3.25), Ecolab in 13 (mean 3.62).

Presence alone therefore does not separate Kemira from its main comparator; position does. The two answers where Kemira is not first are both Gemini pass 2 (O02 and O03), where SNF is named first and Kemira second, after Gemini named Kemira first in pass 1 for both.

Sources: `data/tallies.json` (share_of_voice), counted under the `peers.yaml` rules.

### 8. Ecolab nearly disappears in the buyer-intent question

Ecolab is named in all 6 O01 answers and all 6 O02 answers, but in only 1 of 6 O03 answers (the sludge-reduction buyer question). Kemira and SNF are named in all 6 O03 answers.

Sources: `data/tallies.json` (share_of_voice.companies, by_question).

### 9. The models' category includes companies the peer set did not anticipate

Veolia (13 of 18 answers), BASF (12) and Kurita (10) are not in `peers.yaml` but are named more often than four of the listed peers (Feralco 8, Solvay 4, USALCO 4, Buckman 4). 29 unlisted companies are named in total (of 39 companies named overall). After the top three: Separ Chemie 5, Univar Solutions 5, SUEZ 4, Brenntag 4, Derypol 3, Nijhuis Saur Industries 2, Chemifloc 2, Kuhlmann Europe 2, Italmatch 2, GEO Specialty Chemicals 2, Aries Chemical 2, Hawkins 2, and 14 more named once each.

Sources: `data/tallies.json` (share_of_voice.unlisted).

### 10. Regional specialists come from particular assistants

The European regional specialists in the open answers come mostly from Gemini: Derypol (3, all Gemini), Nijhuis Saur Industries (2, Gemini), Orege, ACAT, Enva and Alumichem (1 each, Gemini). The North American coagulant suppliers come mostly from Perplexity in O02: GEO Specialty Chemicals, Aries Chemical and Hawkins (2 each, Perplexity), USALCO (4; Perplexity 2, ChatGPT 2), Chemtrade (3; Perplexity 2, ChatGPT 1). Which companies a prospect hears about beyond the global incumbents depends on which assistant they ask.

Sources: `data/tallies.json` (share_of_voice.companies, by_assistant).

---

## Accuracy shape (S5, S6)

### 11. Assistants are rarely flatly wrong about Kemira

Of 123 unique claims: 78 supported, 34 unverified, 8 source_conflict, 3 contradicted (2 assistant_wrong, 1 source_unclear). By instance, 459 of 551 (83%) are supported and 4 (0.7%) are contradicted. The volume of problems is in material the captured sources do not settle and material the sources disagree on, not in model error.

Sources: `data/verdicts.json`; `data/tallies.json` (verdicts_by_frequency).

### 12. The most-repeated claims are right, or reproduce a disagreement in the sources

| Tier | Claims | Supported | Other verdicts |
|---|---|---|---|
| Stated by every assistant in both of its passes | 22 | 20 (91%) | 2 source_conflict, 0 unverified, 0 contradicted |
| Stated by two or three assistants | 39 | 31 (79%) | 5 unverified, 3 source_conflict |
| One assistant, repeated | 22 | 11 (50%) | 9 unverified, 1 source_conflict, 1 contradicted |
| Stated once | 40 | 16 (40%) | 20 unverified, 2 source_conflict, 2 contradicted |

Tiers are computed from the final claim set; they differ slightly from the S5 review batches because four strength splits (C120-C123) moved instances into new claims. The top tier is strict: each of the three assistants made the claim in both of its passes (22 claims). An earlier version counted any claim made by all three assistants and in both passes overall (30 claims), which let in claims some assistant made in only one pass; the eight it added now sit in the second tier. Every contradiction is in the two low-frequency tiers. The top tier's only problems are two `source_conflict` verdicts: the claims assistants agree on most are either supported or reproduce a disagreement between Kemira's own published figures.

Sources: `data/tallies.json` (verdicts_by_frequency).

### 13. Divergence on climate targets traces to the published figures, not the models

Every version of the Scope 1 and 2 and Scope 3 targets an assistant stated (52% / 33% or 51.23% / 32.5%) matched one of Kemira's published documents and conflicted with another; all four claims are `source_conflict`. The same pattern holds for the TRIF and D&I target dates. The page-level record is SF06, SF07 and SF08.

Sources: `data/verdicts.json` (source_conflict verdicts); `data/structural_findings.json` (SF06-SF08).

### 14. One assistant hedged across the conflict

ChatGPT (K06, pass 1) stated the Scope 1 and 2 target as "approximately 51–52%", a range spanning both published figures, rather than picking one (claim C122, supported). It is the only instance in the run of an assistant expressing a figure in a way that covers the disagreement.

Sources: `data/claims.json` (C122); `data/verdicts.json`.

### 15. The clearest model error is a rating Gemini repeats

Gemini stated an EcoVadis **Platinum** rating in both passes (K07); Kemira's material states Gold, consistently, and the other assistants say Gold. It is one of only two `assistant_wrong` verdicts, and the only factual error that one assistant made consistently across both passes.

Sources: `data/verdicts.json` (ecovadis_platinum, contradicted/assistant_wrong); `data/claims.json`.

### 16. No assistant contradicted itself

Across 551 claim instances, no claim was incoherent as stated (the `self_contradictory` field is empty). The one candidate flagged in the S4 pilot was withdrawn on reading all six K06 answers. Inconsistencies in this run are between answers, not within them.

Sources: `data/claims.json` (self_contradictory).

### 17. Reputational and regulatory material concentrates in one question

K07 ("Is Kemira a sustainable company? What are the criticisms?") accounts for 16 of the 34 unverified claims, because assistants surface reputational and regulatory material that the captured Kemira pages do not address. Reported here at category level only, by design.

Sources: `data/verdicts.json`; CLAUDE.md K07 handling.

---

## Stability and volume (S4)

### 18. Answers are dense, and they repeat each other

The 42 Kemira-named answers average 11.4 claims each, against an initial estimate of 5–8. The 551 claim instances collapse to 123 unique claims, about 4.5 instances per claim. The most repeated: "products include coagulants and polymers" (35 instances) and "serves municipal and industrial water treatment" (29).

Sources: `data/claims.json` (counts, frequency).

### 19. Half the claims are not stable across passes

Of 214 claim-by-assistant cells where an assistant stated a claim, 142 appear in both passes and 72 in only one (40 pass 1 only, 32 pass 2 only). 61 of 123 claims are stable for every assistant that stated them. The same question asked twice in fresh sessions produces a substantially different set of claims, which is why the method uses two passes.

Sources: `data/claims.json` (stability).

---

## Collection surfaces

### 20. What the copy function carries differs by assistant

- Gemini's copy function carried no resolvable source URLs in either pass, although Gemini showed retrieval indicators on every answer (README limit 9). Pass 2 recovered 36 source-chip URLs by hand.
- ChatGPT's copy carried its inline links but not its citation markers ("Kemira +1" chips) (README limit 10). It also carried image-card captions into the answer text, some about Kemira (a CFO appointment, a Copenhagen performance-based sludge treatment model) and some about unrelated companies and products.
- Perplexity's copy carried inline source links in both passes.

Sources: `data/raw/`; README limits 9 and 10.

### 21. No surface shows anonymous users which model answered

None of the three assistants displayed a model version to logged-out users except Gemini's picker (3.5 Flash-Lite, with other models gated behind sign-in). An auditor cannot pin which system produced a given answer (README limit 8).

Sources: `data/raw/` model fields; README limit 8.
