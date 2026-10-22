// Renders the dashboard from data.json (built by src/dashboard_data.py) and the
// recommendations from reports/recommendations.md. No other data source.

const $ = (id) => document.getElementById(id);
const el = (tag, props = {}, ...kids) => {
  const n = document.createElement(tag);
  Object.assign(n, props);
  for (const k of kids) if (k !== null && k !== undefined && k !== "") n.append(k);
  return n;
};
const pct = (n, of) => `${Math.round((100 * n) / of)}%`;

// One stacked bar. Each segment carries its count (shown when there is room)
// and a hover title; the text line under the bar names every part, so the
// bar never relies on colour alone.
function stackedBar(parts, total, label, thin = false) {
  const bar = el("div", { className: thin ? "bar thin" : "bar", role: "img" });
  bar.setAttribute("aria-label", label);
  for (const p of parts) {
    if (!p.n) continue;
    const s = el("span", { className: `seg-${p.key}`, title: `${p.label}: ${p.n} of ${total}` }, p.n / total > 0.06 ? `${p.n}` : "");
    s.style.flex = `${p.n} 0 0`;
    bar.append(s);
  }
  return bar;
}
const barLabels = (parts) =>
  el("div", { className: "barlabels" }, ...parts.flatMap((p, i) => [i ? " · " : "", el("b", {}, `${p.n}`), ` ${p.label}`]));
const legend = (target, parts) => {
  for (const p of parts) $(target).append(el("li", {}, el("span", { className: `swatch seg-${p.key}` }), p.label));
};

function tabs() {
  const list = [...document.querySelectorAll('[role="tab"]')];
  const select = (t, push = true) => {
    for (const o of list) {
      const on = o === t;
      o.setAttribute("aria-selected", on);
      o.tabIndex = on ? 0 : -1;
      $(o.getAttribute("aria-controls")).hidden = !on;
    }
    if (push) history.replaceState(null, "", `#${t.id.slice(4)}`);
  };
  list.forEach((t, i) => {
    t.addEventListener("click", () => select(t));
    t.addEventListener("keydown", (e) => {
      const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (d) { const n = list[(i + d + list.length) % list.length]; n.focus(); select(n); }
    });
  });
  const start = list.find((t) => t.id === `tab-${location.hash.slice(1)}`);
  if (start) select(start, false);
}

function header(d) {
  document.title = d.title;
  $("title").textContent = d.title;
  $("independence").textContent = d.independence;
  $("method").textContent = d.method;
  for (const h of d.headline) {
    const [, num, unit] = h.figure.match(/^(\d+) ([a-z]+)$/) || [, h.figure, ""];
    $("headline").append(el("li", {}, el("span", { className: "figure" }, num, unit ? el("span", { className: "unit" }, ` ${unit}`) : null),
      el("span", { className: "line" }, h.line)));
  }
}

function questions(Q) {
  $("questions-label").textContent = Q.label;
  $("questions-hint").textContent = Q.hint;
  for (const g of Q.groups)
    $("questions-body").append(el("h3", {}, g.heading), el("ol", {}, ...g.questions.map((q) => el("li", {}, q))));
  $("questions-body").append(el("p", { className: "why" }, Q.why));
}

function links(L) {
  $("links-lede").append(el("strong", {}, `${L.kemira} of the ${L.total} links`),
    ` the assistants gave (${pct(L.kemira, L.total)}) went to kemira.com. Which share depends heavily on the assistant.`);
  const groups = [
    { key: "kemira", label: "kemira.com" }, { key: "suppliers", label: "other suppliers' sites" },
    { key: "research", label: "market-research sites" }, { key: "other", label: "other" },
  ];
  legend("links-legend", groups);
  for (const a of L.by_assistant) {
    const parts = groups.map((g) => ({ ...g, n: a[g.key] }));
    $("links-chart").append(el("div", { className: "barrow" },
      el("div", { className: "barhead" },
        el("span", { className: "name" }, a.assistant, a.note ? el("small", {}, ` (${a.note})`) : null),
        el("span", { className: "total" }, `${a.total} links`)),
      stackedBar(parts, a.total, `${a.assistant}: ` + parts.map((p) => `${p.n} to ${p.label}`).join(", ")),
      barLabels(parts.filter((p) => p.n))));
  }
  $("links-wiki").textContent = `Wikipedia appears once in all ${L.total} links.`;
  for (const p of L.most_cited)
    $("links-most").append(el("li", {}, `${p.page} `, el("span", { className: "n" }, `${p.citations}`),
      p.checked ? null : el("span", { className: "outside" }, " · not among the pages checked")));
  $("links-outside").textContent =
    `${L.outside_checked_set} of the Kemira pages the assistants linked to were outside the ${L.checked_total} pages and reports this audit checked.`;
  for (const p of L.never_cited)
    $("links-never").append(el("li", { className: p.highlight ? "highlight" : "" }, p.page,
      p.highlight ? el("small", {}, "Never linked. Asked how to reduce sludge, the assistants did link Kemira sludge material: a "
        + "sludge-dewatering page in the digital services section and two case studies. The page built for the question was not among them.") : null));
  $("links-caveat").textContent = L.caveat;
}

function claims(C) {
  const keys = Object.keys(C.outcome_labels);
  const n = Object.fromEntries(keys.map((k, i) => [k, C.outcomes[i].count]));
  $("claims-lede").append(`Of ${C.total} claims about Kemira, `, el("strong", {}, `${n.supported} checked out and ${n.contradicted} conflicted`),
    ` with Kemira's material. The rest are things the Kemira material checked doesn't address (${n.unverified}) or where its own pages and reports disagree (${n.source_conflict}).`);
  const parts = keys.map((k) => ({ key: k, label: C.outcome_labels[k], n: n[k] }));
  legend("claims-legend", parts);
  $("claims-outcomes").append(stackedBar(parts, C.total, "All claims by outcome: " + parts.map((p) => `${p.n} ${p.label}`).join(", ")),
    el("div", { className: "outcomes" }, ...parts.map((p) =>
      el("div", { className: `b-${p.key}` }, el("span", { className: "num" }, `${p.n}`), el("span", { className: "lbl" }, p.label)))));
  for (const r of C.tiers) {
    const tp = keys.map((k) => ({ key: k, label: C.outcome_labels[k], n: r[k] }));
    const callout = r.contradicted === 0 ? el("div", { className: "callout" }, "None conflicted with Kemira's material.") : null;
    $("claims-tiers").append(el("div", { className: "barrow" },
      el("div", { className: "barhead" }, el("span", { className: "name" }, r.label), el("span", { className: "total" }, `${r.claims} claims`)),
      stackedBar(tp, r.claims, `${r.label}: ` + tp.map((p) => `${p.n} ${p.label}`).join(", "), true),
      barLabels(tp.filter((p) => p.n)), callout));
  }
  for (const e of C.errors) $("claims-errors").append(el("li", {}, el("strong", {}, `${e.assistant}. `), e.text));
  $("claims-errors").after(el("p", {}, C.sustainability_question));
  const tb = $("claims-table").tBodies[0];
  for (const r of C.table)
    tb.append(el("tr", {}, el("td", {}, r.claim), el("td", {}, r.outcome), el("td", { className: "num" }, `${r.times}`), el("td", {}, r.assistants.join(", "))));
  const a = C.aggregate_row;
  tb.append(el("tr", { className: "aggregate" }, el("td", {}, a.text), el("td", {}, C.outcome_labels.unverified),
    el("td", { className: "num" }, `${a.times}`), el("td", {}, "")));
}

// The source map: Kemira's sources across the top, what the assistants said
// down the side, and in each cell whether that answer matches or conflicts
// with that source. The diagonal is the finding: each figure matches one
// Kemira source and conflicts with the other.
function figures(F) {
  $("figures-lede").textContent = F.lede;
  const src = Object.fromEntries(F.sources.map((s) => [s.key, s]));
  const cols = ["climate", "reports"];
  const m = $("figures-map");
  m.append(el("div", { className: "corner" }, "Assistants said ↓  ·  Kemira says →"));
  for (const c of cols)
    m.append(el("div", { className: "src" }, el("span", { className: "who" }, src[c].source), el("span", { className: "val" }, src[c].states)));
  for (const a of F.answers) {
    m.append(el("div", { className: "ans" }, el("span", { className: "val" }, a.figure), el("span", { className: "who" }, a.assistants.join(", "))));
    for (const c of cols) {
      const match = a.matches === c;
      m.append(el("div", { className: `cell ${match ? "match" : "conflict"}` },
        el("span", { className: "mark", ariaHidden: "true" }, match ? "✓" : "✕"), match ? "Matches" : "Conflicts"));
    }
  }
  const third = src.sustainability;
  m.append(el("div", { className: "third" }, `The ${third.source.toLowerCase()} states `, el("strong", {}, third.states), ", on the same page."));
  m.append(el("div", { className: "conclusion" }, F.conclusion));
  $("figures-hedge").textContent = `${F.hedge.assistant} once gave "${F.hedge.figure}", a range spanning both of Kemira's figures.`;
  $("figures-also").textContent = F.also;
}

function names(N) {
  $("names-lede").append(`Asked three questions that name no company, the assistants named `,
    el("strong", {}, `Kemira in all ${N.kemira.named_in} answers, first in ${N.kemira.first}`),
    `. SNF was also named in all ${N.snf.named_in}, and first in ${N.snf.first}.`);
  const cols = [];
  for (const a of ["Perplexity", "ChatGPT", "Gemini"]) for (const s of [1, 2]) cols.push([a, s]);
  const g = $("names-grid");
  g.append(el("p", { className: "gridkey" },
    "Each assistant was asked twice, in a 1st and a 2nd session. Large number: Kemira's place. Below it: SNF's place. Dashed: SNF named first."));
  for (const q of [...new Set(N.strip.map((r) => r.question))]) {
    const grid = el("div", { className: "grid6" });
    for (const a of ["Perplexity", "ChatGPT", "Gemini"]) grid.append(el("div", { className: "colhead assistant" }, a));
    for (const [, s] of cols) grid.append(el("div", { className: "colhead" }, s === 1 ? "1st" : "2nd"));
    for (const [a, s] of cols) {
      const r = N.strip.find((x) => x.question === q && x.assistant === a && x.session === s);
      const shift = r.kemira !== 1;
      const cell = el("div", { className: shift ? "pos shift" : "pos",
        title: `${a}, session ${s}: Kemira ${r.kemira} of ${r.named}; SNF ${r.snf ?? "not named"}` },
        el("span", { className: "k" }, `${r.kemira}`), el("span", { className: "s" }, r.snf ? (shift && r.snf === 1 ? "SNF 1st" : `SNF ${r.snf}`) : "no SNF"));
      grid.append(cell);
    }
    g.append(el("div", { className: "qblock" }, el("p", { className: "qtext" }, q), grid));
  }
  $("names-shift").textContent = N.shift_note;
  const pb = $("names-peers").tBodies[0];
  for (const p of N.peers)
    pb.append(el("tr", {}, el("td", {}, p.company), el("td", { className: "num" }, `${p.named_in} of ${N.answers}`), el("td", { className: "num" }, `${p.first}`)));
}

// Parses the generated recommendations file: '# title', italic header line,
// then '## N' sections of a bold statement and an expansion paragraph.
function opinion(md) {
  const inline = (s) => s.replace(/^\*+|\*+$/g, "");
  const lines = md.split(/\r?\n/);
  $("opinion-title").textContent = lines.find((l) => l.startsWith("# ")).slice(2);
  $("opinion-header").textContent = inline(lines.find((l) => /^\*[^*]/.test(l)))
    .replace("Everything else in this repository", "Everything else on this page").replace("this file says", "this section says");
  for (const s of md.split(/^## /m).slice(1)) {
    const paras = s.split(/\n\s*\n/).map((p) => p.trim()).filter((p) => p && p !== "---" && !p.startsWith("*Every"));
    const [num, statement, ...rest] = paras;
    $("opinion-list").append(el("details", {},
      el("summary", {}, el("span", { className: "n" }, num), el("span", {}, inline(statement), el("span", { className: "more" }, "Why, and what it involves"))),
      ...rest.map((p) => el("p", {}, p))));
  }
}

async function main() {
  tabs();
  const d = await (await fetch("data.json")).json();
  header(d);
  questions(d.questions);
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
