// Renders the dashboard from data.json (built by src/dashboard_data.py) and the
// recommendations from reports/recommendations.md. No other data source.

const $ = (id) => document.getElementById(id);
const el = (tag, props = {}, ...kids) => {
  const n = document.createElement(tag);
  Object.assign(n, props);
  for (const k of kids) n.append(k);
  return n;
};
const pct = (n, of) => `${Math.round((100 * n) / of)}%`;

function stackedBar(parts, total, label) {
  const bar = el("div", { className: "bar", role: "img" });
  bar.setAttribute("aria-label", label);
  for (const p of parts) {
    if (!p.n) continue;
    const s = el("span", { className: `seg-${p.key}`, title: `${p.label}: ${p.n}` }, `${p.n}`);
    s.style.width = pct(p.n, total);
    bar.append(s);
  }
  return bar;
}

function tabs() {
  const list = [...document.querySelectorAll('[role="tab"]')];
  const select = (t) => {
    for (const o of list) {
      const on = o === t;
      o.setAttribute("aria-selected", on);
      o.tabIndex = on ? 0 : -1;
      $(o.getAttribute("aria-controls")).hidden = !on;
    }
    history.replaceState(null, "", `#${t.id.slice(4)}`);
  };
  list.forEach((t, i) => {
    t.addEventListener("click", () => select(t));
    t.addEventListener("keydown", (e) => {
      const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (d) { const n = list[(i + d + list.length) % list.length]; n.focus(); select(n); }
    });
  });
  const start = list.find((t) => t.id === `tab-${location.hash.slice(1)}`);
  if (start) select(start);
}

function header(d) {
  document.title = d.title;
  $("title").textContent = d.title;
  $("independence").textContent = d.independence;
  $("method").textContent = d.method;
  for (const h of d.headline) $("headline").append(el("li", {}, el("strong", {}, h.figure), " ", h.line));
}

function links(L) {
  $("links-lede").textContent =
    `${L.kemira} of the ${L.total} links the assistants gave (${pct(L.kemira, L.total)}) went to kemira.com.`;
  const groups = [
    ["kemira", "kemira.com"], ["suppliers", "other suppliers' sites"],
    ["research", "market-research sites"], ["other", "other"],
  ];
  const t = el("table");
  t.append(el("thead", {}, el("tr", {}, el("th", {}, "Assistant"), ...groups.map(([, l]) => el("th", {}, l)), el("th", {}, "Links"))));
  const body = el("tbody");
  const charts = el("div");
  for (const a of L.by_assistant) {
    const name = a.note ? `${a.assistant} (${a.note})` : a.assistant;
    body.append(el("tr", {}, el("td", {}, name), ...groups.map(([k]) => el("td", {}, `${a[k]}`)), el("td", {}, `${a.total}`)));
    charts.append(el("p", {}, name), stackedBar(groups.map(([k, l]) => ({ key: k, label: l, n: a[k] })), a.total,
      `${name}: ` + groups.map(([k, l]) => `${a[k]} to ${l}`).join(", ")));
  }
  t.append(body);
  $("links-chart").append(charts, el("div", { className: "table-wrap" }, t));
  $("links-wiki").textContent = `Wikipedia: ${L.wikipedia} link of ${L.total}.`;
  for (const p of L.most_cited)
    $("links-most").append(el("li", {}, `${p.page}: ${p.citations}`, p.checked ? "" : " (not among the pages checked)"));
  $("links-outside").textContent =
    `${L.outside_checked_set} of the Kemira pages linked to were outside the ${L.checked_total} pages and reports this audit checked.`;
  for (const p of L.never_cited)
    $("links-never").append(el("li", { className: p.highlight ? "highlight" : "" }, p.page,
      p.highlight ? " (the page that answers the question about reducing sludge, which no assistant linked to when asked it)" : ""));
  $("links-caveat").firstChild.textContent = L.caveat;
}

function claims(C) {
  const keys = Object.keys(C.outcome_labels);
  $("claims-lede").textContent = `The assistants made ${C.total} distinct claims about Kemira. Each was checked against Kemira's own material.`;
  const o = el("ul");
  C.outcomes.forEach((x, i) => o.append(el("li", {}, el("strong", {}, `${x.count}`), ` ${x.label}`)));
  $("claims-outcomes").append(
    stackedBar(C.outcomes.map((x, i) => ({ key: keys[i], label: x.label, n: x.count })), C.total, "All claims by outcome"), o);
  const t = el("table");
  t.append(el("thead", {}, el("tr", {}, el("th", {}, "How often"), el("th", {}, "Claims"), ...keys.map((k) => el("th", {}, C.outcome_labels[k])))));
  const body = el("tbody");
  for (const r of C.tiers) {
    body.append(el("tr", {}, el("td", {}, r.label, el("br"), stackedBar(keys.map((k) => ({ key: k, label: C.outcome_labels[k], n: r[k] })), r.claims, r.label)),
      el("td", {}, `${r.claims}`), ...keys.map((k) => el("td", {}, `${r[k]}`))));
  }
  t.append(body);
  $("claims-tiers").append(el("div", { className: "table-wrap" }, t));
  for (const e of C.errors) $("claims-errors").append(el("li", {}, `${e.assistant}: ${e.text}`));
  const tb = $("claims-table").tBodies[0];
  for (const r of C.table)
    tb.append(el("tr", {}, el("td", {}, r.claim), el("td", {}, r.outcome), el("td", {}, `${r.times}`), el("td", {}, r.assistants.join(", "))));
  const a = C.aggregate_row;
  tb.append(el("tr", {}, el("td", {}, a.text), el("td", {}, C.outcome_labels.unverified), el("td", {}, `${a.times}`), el("td", {}, "")));
}

function figures(F) {
  for (const s of F.sources) $("figures-sources").append(el("li", {}, `${s.source}: `, el("strong", {}, s.states)));
  const tb = $("figures-answers").tBodies[0];
  for (const a of F.answers)
    tb.append(el("tr", {}, el("td", {}, a.figure), el("td", {}, a.assistants.join(", ")), el("td", {}, a.matches), el("td", {}, a.conflicts)));
  $("figures-hedge").textContent = `${F.hedge.assistant} once gave "${F.hedge.figure}", a range spanning both of Kemira's figures.`;
  $("figures-also").textContent = F.also;
  $("figures-conclusion").textContent = F.conclusion;
}

function names(N) {
  $("names-lede").textContent =
    `Asked three open questions that name no company, the assistants named Kemira in all ${N.kemira.named_in} answers and first in ${N.kemira.first}. ` +
    `SNF was also named in all ${N.snf.named_in}, and first in ${N.snf.first}.`;
  const cols = [];
  for (const a of ["Perplexity", "ChatGPT", "Gemini"]) for (const s of [1, 2]) cols.push([a, s]);
  const qs = [...new Set(N.strip.map((r) => r.question))];
  const t = $("names-strip");
  t.append(el("thead", {}, el("tr", {}, el("th", {}, "Question"), ...cols.map(([a, s]) => el("th", {}, `${a}, session ${s}`)))));
  const body = el("tbody");
  for (const q of qs) {
    const tr = el("tr", {}, el("td", {}, q));
    for (const [a, s] of cols) {
      const r = N.strip.find((x) => x.question === q && x.assistant === a && x.session === s);
      tr.append(el("td", { className: r.kemira !== 1 ? "marked" : "" },
        `Kemira ${r.kemira}`, el("br"), r.snf ? `SNF ${r.snf}` : "SNF not named", el("br"), el("small", {}, `of ${r.named}`)));
    }
    body.append(tr);
  }
  t.append(body);
  $("names-shift").textContent = N.shift_note;
  const pb = $("names-peers").tBodies[0];
  for (const p of N.peers) pb.append(el("tr", {}, el("td", {}, p.company), el("td", {}, `${p.named_in} of ${N.answers}`), el("td", {}, `${p.first}`)));
}

// Parses the generated recommendations file: '# title', italic header line,
// then '## N' sections of a bold statement and an expansion paragraph.
function opinion(md) {
  const inline = (s) => s.replace(/^\*+|\*+$/g, "");
  const lines = md.split(/\r?\n/);
  $("opinion-title").textContent = lines.find((l) => l.startsWith("# ")).slice(2);
  $("opinion-header").textContent = inline(lines.find((l) => /^\*[^*]/.test(l)))
    .replace("Everything else in this repository", "Everything else on this page").replace("this file says", "this section says");
  const sections = md.split(/^## /m).slice(1);
  for (const s of sections) {
    const paras = s.split(/\n\s*\n/).map((p) => p.trim()).filter((p) => p && p !== "---" && !p.startsWith("*Every"));
    const [num, statement, ...rest] = paras;
    $("opinion-list").append(el("details", {}, el("summary", {}, el("strong", {}, `${num}. `), inline(statement)),
      ...rest.map((p) => el("p", {}, p))));
  }
}

async function main() {
  tabs();
  const d = await (await fetch("data.json")).json();
  header(d);
  links(d.links);
  claims(d.right_wrong);
  figures(d.figures);
  names(d.names);
  try {
    opinion(await (await fetch(d.recommendations_source)).text());
  } catch {
    $("opinion-list").textContent = "The recommendations could not be loaded.";
  }
}
main();
