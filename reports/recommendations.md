# What I would do: five changes to kemira.com

*Signed opinion by Talha Malik, not audit output. Everything else in this repository describes what was found; this file says what I would do.*

## 1

**Kemira’s own pages and reports give different numbers for the same climate target, so assistants repeat whichever one they happened to read. Every page and report needs to state one figure and one date.**

The climate page says 52%. Both financial reports say 51.23%. The sustainability page says both 50% and 52%. The second climate target splits the same way, 33% or 32.5%, and two target dates moved between the annual and the half-year report. Eight of the claims assistants made, repeated 27 times across the answers, trace back to this. It is a handful of edits on two web pages.

## 2

**The sustainability figures load from an outside service and the half-year report sits on another company’s site, so an assistant reading kemira.com finds neither. Both need to be text on Kemira’s own pages.**

The sustainability key indicators page contains 38 characters of readable text, because the figures arrive from a third-party service after the page loads. The January to June 2026 half-year report is published on a press-release service rather than kemira.com, and the reports index links no interim report at all. An assistant restricted to Kemira’s own domain reaches none of it. Hosting the reports on kemira.com and linking them from the reports index would put them where assistants already search.

## 3

**No Kemira page carries the hidden label that tells software “this page belongs to Kemira”, and 19 of 21 have no main title in their code. One change to the page template adds both everywhere.**

All 21 pages carry the same default set of tags, and none of them identifies an organisation. Nineteen have no main heading; the homepage’s are carousel slides. One page on the site has a question and answer section, it carries no markup saying so, and no assistant cited it. Adding both is standard practice and roughly a day’s work for a developer. This audit cannot show it would change what assistants cite, because every page lacked the same things and there was nothing to compare against.

## 4

**Most pages open with a date or a tagline rather than the answer, and the opening is what an assistant reads first. Each page should lead with the answer.**

Two of 21 pages open with an answer to the question the page exists for. Nine partly do. Ten do not. Seven open with a date, and those seven are the entire investor section, which is where analysts and journalists look. There is no proof this costs citations: one page that opens with a date was cited six times. But the opening is what both a reader and an assistant take first, and it is a one-line change per page.

## 5

**Asked how to reduce sludge, the assistants never linked to Kemira’s sludge page, even though it exists. The page needs the case results and product names so that it is cited.**

None of the links the assistants gave across the 60 answers pointed to the sludge page, including the 28 links in the six answers about reducing sludge volume at a municipal plant. Case-study pages elsewhere on kemira.com were cited 11 times in the same run. Five claims the captured material could not settle trace back to this page, second only to the sustainability page. Why assistants do not reach it is not established here. The pages they do reach carry named cases, results and products; this one does not.

---

*Every figure above is checked against this repository's data by `src/recommendations.py` before the file is written. The findings themselves are in `reports/geo_snapshot.md`.*
