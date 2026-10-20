"""S3: collection harness for the raw answer logs in data/raw/.

    python -m src.collection scaffold --pass 1   create empty answer files (never overwrites)
    python -m src.collection sheet --pass 1      write collection_sheet.md (gitignored)
    python -m src.collection check --pass 1      validate; uncollected files are reported, not errors
    python -m src.collection check --pass 1 --require-complete
                                                 also fail if any file is uncollected or unfrozen
    python -m src.collection freeze --pass 1     record hashes of collected files in the manifest
    python -m src.collection fill K01 chatgpt    after pasting: stamp collected_at, extract citations,
                                                 set browsing; prints everything it wrote
    python -m src.collection fill K01 chatgpt --citations-only
                                                 re-extract citations only; touches nothing else

fill never overwrites a value that is already set without saying so: a
citations list that differs from what it extracts is kept unless --force
is given, and collected_at and browsing are kept once set.

The manifest (data/raw/manifest.json) holds a hash for every collected file.
Once a file is in it, any later change is an error: the logs are immutable.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime

import yaml

from src import config

RAW_DIR = config.ROOT / "data" / "raw"
MANIFEST_FILE = RAW_DIR / "manifest.json"
COLLECTION_FILE = config.ROOT / "collection.yaml"
SHEET_FILE = config.ROOT / "collection_sheet.md"

BODY_MARKER = "<!-- ANSWER BELOW THIS LINE: paste verbatim from the copy button. Never edit after saving. -->"
FIELDS = ["question_id", "battery_version", "assistant", "pass", "incognito", "prompt_verbatim",
          "model", "model_raw", "model_source", "collected_at", "browsing", "citations", "notes"]
# Fields added from a given pass onward. Earlier passes are frozen without them.
FIELDS_FROM_PASS = {2: ["citations_displayed"]}
# citations_displayed value for a cell whose source chips were not checked.
# [] means the chips were checked and none were shown; this means nobody looked.
NOT_CAPTURED = "not_captured"
MODEL_SOURCES = {"typed", "default"}


def fields_for(pass_no):
    extra = [f for p, fs in FIELDS_FROM_PASS.items() if pass_no >= p for f in fs]
    return FIELDS + extra
BROWSING_VALUES = {"on", "off", "unknown"}
FILE_PATTERN = re.compile(r"^(?P<qid>[A-Z]\d{2})_(?P<assistant>[a-z]+)_p(?P<pass>\d)\.md$")

TEMPLATE = """---
# RAW ANSWER LOG. Verbatim and immutable after collection.
# Paste the answer below the marker line exactly as copied with the
# interface's copy button (markdown source, not rendered text).
# Never edit this file after saving it. If something looks wrong, add a
# note in a new pass or report it; do not fix it here.
#
# After pasting, run: python -m src.collection fill {qid} {assistant} --pass {pass_no}
# fill sets collected_at, citations and browsing, and records model: what
# you typed (kept in model_raw, normalised in model), or the assistant's
# default if model is empty (printed as DEFAULTED). notes optional.
question_id: {qid}
battery_version: {battery_version}
assistant: {assistant}
pass: {pass_no}
incognito: true
prompt_verbatim: {prompt}
model:          # type what the interface shows, or unknown. Never inferred.
model_raw:      # set by fill: exactly what you typed in model
model_source:   # set by fill: typed, or default if model was left empty
collected_at:   # local time with offset, e.g. 2026-10-21T14:05:00+03:00
browsing:       # on / off / unknown
citations:      # set by fill: URLs present in the copied answer text, or [] if none
{extra_fields}notes:          # anything odd about the session
---

{marker}
"""


# ---- config ---------------------------------------------------------------

def load_assistants():
    data = yaml.safe_load(COLLECTION_FILE.read_text(encoding="utf-8"))
    return data["assistants"]


def expected_files(cfg, assistants, pass_no):
    """Ordered (question, assistant, filename): by question, then assistant."""
    return [(q, a, f"{q['id']}_{a['id']}_p{pass_no}.md")
            for q in cfg.questions["questions"] for a in assistants]


def _yaml_string(text):
    return json.dumps(text, ensure_ascii=False)  # a JSON string is a valid double-quoted YAML scalar


# ---- scaffold & sheet -----------------------------------------------------

def scaffold(cfg, assistants, pass_no):
    created, skipped = [], []
    for q, a, name in expected_files(cfg, assistants, pass_no):
        path = RAW_DIR / name
        if path.exists():
            skipped.append(name)
            continue
        extra = ""
        if "citations_displayed" in fields_for(pass_no):
            extra = ("citations_displayed:  # by hand, as a list below this line: URLs from clicking the source chips; "
                     f"[] if none shown; {NOT_CAPTURED} if not checked. fill never touches this.\n")
        path.write_text(TEMPLATE.format(
            qid=q["id"], battery_version=cfg.questions["battery_version"], assistant=a["id"],
            pass_no=pass_no, prompt=_yaml_string(q["text"]), marker=BODY_MARKER, extra_fields=extra,
        ), encoding="utf-8", newline="\n")
        created.append(name)
    print(f"Created {len(created)} file(s); {len(skipped)} already existed and were left untouched.")


def _norm_space(text):
    return re.sub(r"\s+", " ", text).strip()


def _ticked():
    """File names already ticked in an existing sheet, so regenerating keeps progress."""
    if not SHEET_FILE.exists():
        return set()
    return set(re.findall(r"(?m)^- \[[xX]\] `([^`]+)`", SHEET_FILE.read_text(encoding="utf-8")))


def write_sheet(cfg, assistants, pass_no):
    ticked = _ticked()
    chips = "citations_displayed" in fields_for(pass_no)
    interim = cfg.sources["interim_report_published"]
    order = ", ".join(f"{i}. {a['name']}" for i, a in enumerate(assistants, start=1))
    lines = [
        f"# Collection sheet: pass {pass_no}",
        "",
        "Local working sheet. Not published.",
        "",
        f"> ## ⚠ Cutoff: finish every cell before {interim}",
        f"> Kemira's interim report publishes on {interim}. Ground truth was captured before it, so any cell "
        "collected on or after that date fails validation and cannot be compared.",
        "",
    ]
    if chips:
        lines += [
            "> **New in this pass: source chip capture.** Pass 1 recorded only the URLs inside the copied text. "
            "This pass also records the URLs behind the interface's source chips, in `citations_displayed`, by hand.",
            "",
        ]
    lines += [
        f"**Assistants, in order:** {order}",
        "",
        "**Every cell:**",
        "1. Open a **fresh private/incognito window**, logged out. One cell per session: close it before the next cell.",
        "2. Paste the prompt below **exactly**. No greeting, no edits.",
        "3. Copy the answer with the **interface's copy button** (markdown source), not by selecting text.",
        "4. **Paste answer:** open the file, paste below the marker line. Save.",
    ]
    n = 5
    if chips:
        lines.append(
            f"{n}. **Record source chips:** click through each source chip the interface shows and add its URL to "
            "`citations_displayed` as a list, one `  - \"url\"` line each **below** the field, in the order shown. "
            "Do not type URLs on the field's own line or after the `#`: YAML ignores everything after `#`. "
            f"If the interface showed no chips, write `citations_displayed: []`; if you did not check, write "
            f"`citations_displayed: {NOT_CAPTURED}`. Save. (fill never touches this field.)")
        n += 1
    lines += [
        f"{n}. **Run fill** (command in each cell). It stamps `collected_at`, extracts `citations` from the "
        "pasted text, sets `browsing`, records the model (defaulting it if empty, and saying DEFAULTED), and prints "
        "all of it. If the printed `citations` miss something in the text, correct them by hand; re-running fill "
        "will not overwrite your correction.",
        f"{n + 1}. **Check model:** if the interface showed a different model from the one fill recorded, type it "
        "in `model` and run fill again with `--force`. Add `notes` if anything was odd.",
        "",
        "Run commands from the project folder. Do not edit the answer body after saving.",
        "",
        "**Where the model version is shown:**",
        "",
    ]
    lines += [f"- **{a['name']}** ({a['url']}): {a['model_hint']}" for a in assistants]
    lines += [
        "",
        "`collected_at` example: `2026-10-21T14:05:00+03:00` (Finland is UTC+3 until 25 October).",
        "",
        "## Checklist",
        "",
    ]
    files = expected_files(cfg, assistants, pass_no)
    lines += [f"- [{'x' if name in ticked else ' '}] `{name}`" for _, _, name in files]
    lines += ["", "## Cells", ""]
    current = None
    for q, a, name in files:
        if q["id"] != current:
            current = q["id"]
            lines += [f"### {q['id']}", ""]
        lines += [
            f"**{a['name']}**: open `data/raw/{name}`",
            "",
            "Prompt:",
            "",
            "```text",
            q["text"],
            "```",
            "",
            ("Then: paste answer → record source chip URLs → run fill → check model" if chips
             else "Then: paste answer → run fill → check model"),
            "",
        ]
        if a.get("cell_reminder"):
            lines += [f"> **{a['name']} reminder:** {_norm_space(a['cell_reminder'])}", ""]
        lines += [
            "```powershell",
            f".venv\\Scripts\\python -m src.collection fill {q['id']} {a['id']}" + (f" --pass {pass_no}" if pass_no != 1 else ""),
            "```",
            "",
        ]
    SHEET_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {SHEET_FILE.name} ({len(files)} cells).")


# ---- parsing --------------------------------------------------------------

def _raw_scalar(front_text, key):
    """A frontmatter value exactly as typed: quotes honoured, trailing # comment dropped. None if empty."""
    m = re.search(rf"(?m)^{key}:[ \t]*(.*?)[ \t]*$", front_text)
    if not m:
        return None
    value = m.group(1)
    if value[:1] in ("'", '"'):
        quoted = re.match(r"""("(?:[^"\\]|\\.)*"|'(?:[^']|'')*')""", value)
        return yaml.safe_load(quoted.group(1)) if quoted else value
    value = re.split(r"[ \t]#", value, maxsplit=1)[0].strip()
    if value.startswith("#"):
        value = ""
    return value or None


def normalise_model(text):
    """Canonical model name: lowercase, spaces and hyphens removed. GPT 5.6 / gpt-5.6 / gpt5.6 -> gpt5.6."""
    return re.sub(r"[\s\-‐-―]+", "", text).lower()


def parse(path):
    """Returns (frontmatter dict, body text). Raises ValueError on malformed files."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("does not start with a frontmatter block")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("frontmatter block is not closed")
    front = yaml.safe_load(text[4:end]) or {}
    # YAML 1.1 reads bare on/off as booleans; the template asks for on/off.
    if front.get("browsing") is True:
        front["browsing"] = "on"
    elif front.get("browsing") is False:
        front["browsing"] = "off"
    # Model names are read as typed: YAML would turn 5.10 into the number 5.1.
    for key in ("model", "model_raw"):
        if key in front:
            front[key] = _raw_scalar(text[4:end], key)
    rest = text[end + 5:]
    if BODY_MARKER not in rest:
        raise ValueError("answer marker line is missing or was edited")
    body = rest.split(BODY_MARKER, 1)[1]
    return front, body.strip()


def content_hash(path):
    """sha256 of the file with line endings normalised, so git's CRLF handling can't change it."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {"files": {}}


# ---- check ----------------------------------------------------------------

def _parse_collected_at(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value)
    else:
        raise ValueError(f"not a timestamp: {value!r}")
    if dt.tzinfo is None:
        raise ValueError("has no UTC offset")
    return dt


def check(cfg, assistants, pass_no, require_complete):
    errors, uncollected, unfrozen, collected = [], [], [], []
    manifest = load_manifest()["files"]
    files = expected_files(cfg, assistants, pass_no)
    expected_names = {name for _, _, name in files}
    assistant_ids = {a["id"] for a in assistants}

    interim = cfg.sources["interim_report_published"]
    interim = interim if isinstance(interim, date) else date.fromisoformat(str(interim))
    gt_captured = cfg.sources.get("captured_at")
    gt_before_interim = gt_captured is not None and date.fromisoformat(str(gt_captured)) < interim

    for path in sorted(RAW_DIR.glob("*.md")):
        m = FILE_PATTERN.match(path.name)
        if not m or m["assistant"] not in assistant_ids:
            errors.append(f"{path.name}: unexpected file name")
        elif int(m["pass"]) == pass_no and path.name not in expected_names:
            errors.append(f"{path.name}: not an expected file for pass {pass_no}")

    for q, a, name in files:
        path = RAW_DIR / name
        if not path.exists():
            errors.append(f"{name}: missing")
            continue
        try:
            front, body = parse(path)
        except (ValueError, yaml.YAMLError) as exc:
            errors.append(f"{name}: {exc}")
            continue

        def err(msg):
            errors.append(f"{name}: {msg}")

        missing = [f for f in fields_for(pass_no) if f not in front]
        if missing:
            err(f"frontmatter fields missing: {', '.join(missing)}")
        if front.get("question_id") != q["id"]:
            err(f"question_id is {front.get('question_id')!r}, file name says {q['id']}")
        if front.get("assistant") != a["id"]:
            err(f"assistant is {front.get('assistant')!r}, file name says {a['id']}")
        if front.get("pass") != pass_no:
            err(f"pass is {front.get('pass')!r}, expected {pass_no}")
        if front.get("battery_version") != cfg.questions["battery_version"]:
            err(f"battery_version is {front.get('battery_version')!r}, config is {cfg.questions['battery_version']}")
        if front.get("incognito") is not True:
            err(f"incognito is {front.get('incognito')!r}, expected true")
        if front.get("prompt_verbatim") != q["text"]:
            err(f"prompt_verbatim drifted from questions.yaml: {front.get('prompt_verbatim')!r} != {q['text']!r}")

        if name in manifest and manifest[name]["hash"] != content_hash(path):
            err("EDITED AFTER COLLECTION: content no longer matches the manifest hash")

        if not body:
            uncollected.append(name)
            continue
        collected.append(name)

        if not front.get("model"):
            err("model is empty (write unknown if the interface does not show one, then run fill)")
        elif not front.get("model_raw"):
            err("model_raw is empty: run fill to record what you typed and normalise model")
        elif front["model"] != normalise_model(front["model_raw"]):
            err(f"model {front['model']!r} is not the normalised form of model_raw {front['model_raw']!r} "
                f"(expected {normalise_model(front['model_raw'])!r})")
        elif front.get("model_source") not in MODEL_SOURCES:
            err(f"model_source is {front.get('model_source')!r}, expected typed or default (run fill)")
        elif front["model_source"] == "default" and front["model_raw"] != a.get("default_model"):
            err(f"model_source is default but model_raw {front['model_raw']!r} is not "
                f"{a['name']}'s default_model {a.get('default_model')!r}")
        try:
            dt = _parse_collected_at(front.get("collected_at"))
            if gt_before_interim and dt.date() >= interim:
                err(f"collected {dt.isoformat()}, on or after the interim report ({interim}); "
                    f"ground truth was captured before it ({gt_captured})")
        except ValueError as exc:
            err(f"collected_at {exc}")
        if front.get("browsing") not in BROWSING_VALUES:
            err(f"browsing is {front.get('browsing')!r}, expected one of on/off/unknown")
        citations = front.get("citations")
        if not isinstance(citations, list) or not all(isinstance(c, str) and c.strip() for c in citations):
            err("citations must be a list of URLs, or [] if none")
        if "citations_displayed" in fields_for(pass_no):
            shown = front.get("citations_displayed")
            if shown == NOT_CAPTURED:
                pass  # chips were not checked for this cell; distinct from [] (checked, none shown)
            elif not isinstance(shown, list) or not all(isinstance(u, str) and u.strip() for u in shown):
                err(f"citations_displayed must be a list of the source chip URLs, [] if the interface showed none, "
                    f"or {NOT_CAPTURED} if the chips were not checked (entered by hand)")
        if name not in manifest:
            unfrozen.append(name)

    total = len(files)
    for e in errors:
        print(f"ERROR   {e}")
    print(f"\nPass {pass_no}: {len(collected)}/{total} collected, {len(uncollected)} not yet collected, "
          f"{len(unfrozen)} collected but not yet frozen in the manifest.")
    if uncollected:
        print("Not yet collected: " + ", ".join(uncollected))
    if unfrozen:
        print("Not yet frozen (run freeze): " + ", ".join(unfrozen))

    if errors:
        print(f"\nInvalid: {len(errors)} error(s).")
        return 1
    if require_complete and (uncollected or unfrozen):
        print("\nIncomplete: every file must be collected and frozen before later stages run.")
        return 1
    print("\nNo errors.")
    return 0


# ---- freeze ---------------------------------------------------------------

def freeze(cfg, assistants, pass_no):
    if check(cfg, assistants, pass_no, require_complete=False) != 0:
        print("Not freezing: fix the errors above first.")
        return 1
    manifest = load_manifest()
    added = []
    for _, _, name in expected_files(cfg, assistants, pass_no):
        path = RAW_DIR / name
        if name in manifest["files"]:
            continue
        front, body = parse(path)
        if not body:
            continue
        manifest["files"][name] = {"hash": content_hash(path), "frozen_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        added.append(name)
    manifest["files"] = dict(sorted(manifest["files"].items()))
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nFroze {len(added)} file(s) into {MANIFEST_FILE.name}.")
    return 0


# ---- fill -----------------------------------------------------------------

MD_LINK_URL = re.compile(r"\]\(\s*<?(https?://[^\s()>]+(?:\([^\s()]*\)[^\s()>]*)*)>?(?:\s+\"[^\"]*\")?\s*\)")
BARE_URL = re.compile(r"https?://[^\s<>\"'`\[\]]+")
TRAILING_PUNCT = ".,;:!?*_"


def _clean_bare(url):
    url = url.rstrip(TRAILING_PUNCT)
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1].rstrip(TRAILING_PUNCT)
    return url


def extract_urls(body):
    """URLs in the markdown body, deduplicated, in order of first appearance."""
    found = []  # (position, url)
    covered = []
    for m in MD_LINK_URL.finditer(body):
        found.append((m.start(1), m.group(1)))
        covered.append((m.start(1), m.end(1)))
    for m in BARE_URL.finditer(body):
        if any(s <= m.start() < e for s, e in covered):
            continue
        found.append((m.start(), _clean_bare(m.group(0))))
    seen, urls = set(), []
    for _, url in sorted(found):
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _split_raw(path):
    """(frontmatter text including both --- lines, rest of file) with line endings preserved."""
    with open(path, encoding="utf-8", newline="") as fh:
        text = fh.read()
    m = re.match(r"---\r?\n.*?\r?\n---\r?\n", text, re.S)
    if not m:
        raise ValueError("frontmatter block not found")
    return text[:m.end()], text[m.end():]


def _set_scalar(head, key, value):
    new, n = re.subn(rf"(?m)^{key}:[^\r\n]*", f"{key}: {value}", head, count=1)
    if n != 1:
        raise ValueError(f"field '{key}' not found in frontmatter")
    return new


def _set_citations(head, urls):
    nl = "\r\n" if "\r\n" in head else "\n"
    block = f"citations: []{nl}" if not urls else (
        f"citations:{nl}" + "".join(f"  - {json.dumps(u, ensure_ascii=False)}{nl}" for u in urls))
    new, n = re.subn(r"(?m)^citations:[^\r\n]*\r?\n(?:[ \t]+-[^\r\n]*\r?\n)*", lambda _: block, head, count=1)
    if n != 1:
        raise ValueError("field 'citations' not found in frontmatter")
    return new


def _fill_model(head, front, force, report, warnings, default_model=None):
    """Move what was typed in model to model_raw and write the normalised form to model.

    If model is empty and the assistant has a default_model, the default is
    used and model_source records "default" rather than "typed".
    """
    model, raw = front.get("model"), front.get("model_raw")
    for key, after in (("model_raw", "model"), ("model_source", "model_raw")):
        if not re.search(rf"(?m)^{key}:", head):
            head = re.sub(rf"(?m)^({after}:[^\r\n]*)(\r?\n)", rf"\1\2{key}:\2", head, count=1)

    def record(value, source):
        h = _set_scalar(head, "model_raw", json.dumps(value, ensure_ascii=False))
        h = _set_scalar(h, "model", json.dumps(normalise_model(value), ensure_ascii=False))
        return _set_scalar(h, "model_source", source)

    if not model:
        if default_model:
            report.append(f"  model_raw:    {default_model!r}  (DEFAULTED: not read from the file)")
            report.append(f"  model:        {normalise_model(default_model)!r}  (normalised)")
            report.append("  model_source: default")
            warnings.append(f"model was empty, so it DEFAULTED to {default_model!r}. If this cell showed a "
                            "different model, type it in model and run fill with --force.")
            return record(default_model, "default")
        report.append("  model:        EMPTY  (type what the interface shows, or unknown, then run fill again)")
        return head
    if not raw:
        report.append(f"  model_raw:    {model!r}  (as you typed it)")
        report.append(f"  model:        {normalise_model(model)!r}  (normalised)")
        report.append("  model_source: typed")
        return record(model, "typed")
    if model == normalise_model(raw):
        source = front.get("model_source") or "typed"
        report.append(f"  model_raw:    {raw!r}  (already set, kept)")
        report.append(f"  model:        {model!r}  (normalised, unchanged)")
        report.append(f"  model_source: {source}" + ("  (DEFAULTED earlier, not typed)" if source == "default" else ""))
        if not front.get("model_source"):
            head = _set_scalar(head, "model_source", "typed")
        return head
    if force:
        report.append(f"  model_raw:    {model!r}  (REPLACING {raw!r}, --force)")
        report.append(f"  model:        {normalise_model(model)!r}  (normalised)")
        report.append("  model_source: typed")
        return record(model, "typed")
    report.append(f"  model_raw:    {raw!r}  (kept)")
    report.append(f"  model:        {model!r}  (kept; does not match model_raw)")
    warnings.append(f"model {model!r} is not the normalised form of model_raw {raw!r}. "
                    f"If you retyped the model, run fill with --force to record {model!r} as typed.")
    return head


def fill(qid, assistant_id, pass_no, citations_only, force):
    name = f"{qid}_{assistant_id}_p{pass_no}.md"
    path = RAW_DIR / name
    if not path.exists():
        print(f"{name}: no such file in data/raw/.")
        return 1
    if name in load_manifest()["files"]:
        print(f"{name}: already frozen in the manifest. Refusing to change it.")
        return 1
    front, body = parse(path)
    if not body:
        print(f"{name}: answer body is empty. Paste the answer below the marker line and save first. Nothing written.")
        return 1

    head, rest = _split_raw(path)
    urls = extract_urls(body)
    current = front.get("citations")
    report, warnings = [], []

    if not citations_only:
        if front.get("collected_at"):
            kept = front["collected_at"]
            kept = kept.isoformat() if isinstance(kept, datetime) else kept
            report.append(f"  collected_at: {kept}  (already set, kept)")
        else:
            stamp = datetime.now().astimezone().isoformat(timespec="seconds")
            head = _set_scalar(head, "collected_at", stamp)
            report.append(f"  collected_at: {stamp}  (set now)")

    if current is None:
        head = _set_citations(head, urls)
        report.append(f"  citations:    {len(urls)} URL(s) written")
    elif current == urls:
        report.append(f"  citations:    {len(urls)} URL(s), unchanged")
    elif force:
        head = _set_citations(head, urls)
        report.append(f"  citations:    {len(urls)} URL(s) written, REPLACING your {len(current)}-item list (--force)")
    else:
        report.append(f"  citations:    KEPT your existing {len(current)}-item list; the body yields {len(urls)} URL(s)")
        warnings.append("citations differ from what the body yields. Kept yours. "
                        "Re-run with --force to replace them with the extracted list.")
        added = [u for u in urls if u not in current]
        removed = [u for u in current if u not in urls]
        if added:
            warnings.append("in the body but not in your list: " + ", ".join(added))
        if removed:
            warnings.append("in your list but not in the body: " + ", ".join(removed))

    if not citations_only:
        final = urls if (current is None or force) else current
        # citations_displayed is read here, never written: chips are evidence of retrieval too.
        displayed = front.get("citations_displayed") if isinstance(front.get("citations_displayed"), list) else []
        basis = f"{len(final)} citation(s)"
        if front.get("citations_displayed") == NOT_CAPTURED:
            basis += ", displayed not captured"
        elif "citations_displayed" in front:
            basis += f", {len(displayed)} displayed"
        if front.get("browsing"):
            report.append(f"  browsing:     {front['browsing']}  (already set, kept)")
            expected = "on" if (final or displayed) else "off"
            if front["browsing"] != expected and front["browsing"] != "unknown":
                warnings.append(f"browsing is '{front['browsing']}' but citations suggest '{expected}'. Kept yours.")
        else:
            value = "on" if (final or displayed) else "off"
            head = _set_scalar(head, "browsing", value)
            report.append(f"  browsing:     {value}  (set: {basis})")

    if not citations_only:
        default = next((a.get("default_model") for a in load_assistants() if a["id"] == assistant_id), None)
        head = _fill_model(head, front, force, report, warnings, default)

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(head + rest)
    parse(path)  # the edited file must still parse

    print(name)
    print("\n".join(report))
    shown = urls if (current is None or force or current == urls) else current
    if shown:
        print("\n  Citations now in the file, in order:")
        for i, u in enumerate(shown, start=1):
            print(f"    {i:2}. {u}")
    else:
        print("\n  No citations in the file.")
    for w in warnings:
        print(f"\n  WARNING: {w}")
    print("\n  Compare these with the sources the interface showed.")
    return 0


def main(argv):
    parser = argparse.ArgumentParser(prog="python -m src.collection")
    parser.add_argument("command", choices=["scaffold", "sheet", "check", "freeze", "fill"])
    parser.add_argument("question_id", nargs="?", help="fill only, e.g. K01")
    parser.add_argument("assistant", nargs="?", help="fill only, e.g. chatgpt")
    parser.add_argument("--pass", dest="pass_no", type=int, choices=[1, 2],
                        help="required except for fill, where it defaults to 1")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--citations-only", action="store_true", help="fill: only re-extract citations")
    parser.add_argument("--force", action="store_true",
                        help="fill: replace a citations list that differs, and re-record a retyped model")
    args = parser.parse_args(argv)

    if args.command == "fill":
        if not (args.question_id and args.assistant):
            parser.error("fill needs <question_id> <assistant>, e.g. fill K01 chatgpt")
        if args.assistant not in {a["id"] for a in load_assistants()}:
            parser.error(f"unknown assistant '{args.assistant}'")
        return fill(args.question_id, args.assistant, args.pass_no or 1, args.citations_only, args.force)
    if args.pass_no is None:
        parser.error("--pass is required")

    cfg = config.load()
    assistants = load_assistants()
    if args.command == "scaffold":
        scaffold(cfg, assistants, args.pass_no)
        return 0
    if args.command == "sheet":
        write_sheet(cfg, assistants, args.pass_no)
        return 0
    if args.command == "freeze":
        return freeze(cfg, assistants, args.pass_no)
    return check(cfg, assistants, args.pass_no, args.require_complete)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
