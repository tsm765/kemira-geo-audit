"""Load and validate the three config files.

Runs as a precondition for every later stage:

    python -m src.config

Exits 0 if the configs are valid, 1 otherwise. Errors name the file and
what is wrong. Warnings (thin source coverage) do not fail validation.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = ROOT / "questions.yaml"
PEERS_FILE = ROOT / "peers.yaml"
SOURCES_FILE = ROOT / "sources.yaml"

# A kemira question backed by this many sources or fewer is reported as thin.
THIN_COVERAGE = 1


@dataclass
class Config:
    questions: dict
    peers: dict
    sources: dict


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    coverage: dict = field(default_factory=dict)  # question id -> [source ids]

    def error(self, path, message):
        self.errors.append(f"{path.name}: {message}")

    def warn(self, path, message):
        self.warnings.append(f"{path.name}: {message}")


def _load_yaml(path, report):
    if not path.exists():
        report.error(path, "file not found")
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        report.error(path, f"YAML parse error: {exc}")
        return None
    if not isinstance(data, dict):
        report.error(path, "top level must be a mapping")
        return None
    return data


def _check_questions(questions, report):
    for key in ("battery_version", "locked"):
        if key not in questions:
            report.error(QUESTIONS_FILE, f"missing required key '{key}'")

    items = questions.get("questions") or []
    if not items:
        report.error(QUESTIONS_FILE, "no questions defined")

    by_id = {}
    for i, q in enumerate(items):
        qid = q.get("id")
        if not qid:
            report.error(QUESTIONS_FILE, f"question #{i + 1} has no id")
            continue
        if qid in by_id:
            report.error(QUESTIONS_FILE, f"duplicate question id '{qid}'")
        if q.get("type") not in ("kemira", "open"):
            report.error(QUESTIONS_FILE, f"{qid}: type must be 'kemira' or 'open', got {q.get('type')!r}")
        if not q.get("text"):
            report.error(QUESTIONS_FILE, f"{qid}: empty text")
        by_id[qid] = q
    return by_id


def _check_sources(sources, question_ids, report):
    items = sources.get("sources") or []
    if not items:
        report.error(SOURCES_FILE, "no sources defined")

    seen = set()
    for i, s in enumerate(items):
        sid = s.get("id") or f"source #{i + 1}"
        if not s.get("id"):
            report.error(SOURCES_FILE, f"{sid} has no id")
        elif sid in seen:
            report.error(SOURCES_FILE, f"duplicate source id '{sid}'")
        seen.add(sid)

        if not s.get("url"):
            report.error(SOURCES_FILE, f"{sid}: empty url")
        if not s.get("topic"):
            report.error(SOURCES_FILE, f"{sid}: empty topic")
        if not s.get("covers"):
            report.error(SOURCES_FILE, f"{sid}: empty covers")

        for qid in s.get("answers") or []:
            if qid not in question_ids:
                report.error(SOURCES_FILE, f"{sid}: answers references unknown question '{qid}'")
            else:
                report.coverage.setdefault(qid, []).append(sid)


def _check_coverage(questions_by_id, report):
    for qid, q in questions_by_id.items():
        if q.get("type") != "kemira":
            continue
        backing = report.coverage.get(qid, [])
        if not backing:
            report.error(
                SOURCES_FILE,
                f"kemira question {qid} is not referenced by any source; "
                "it can only ever return 'unverified'",
            )
        elif len(backing) <= THIN_COVERAGE:
            report.warn(SOURCES_FILE, f"kemira question {qid} has thin coverage: {', '.join(backing)}")


def _check_peers(peers, report):
    comparators = peers.get("comparators") or []
    if not comparators:
        report.error(PEERS_FILE, "no comparators defined")

    segment_names = set()
    for seg_name, seg in (peers.get("segments") or {}).items():
        segment_names.update((seg or {}).get("peers") or [])
    if not segment_names:
        report.error(PEERS_FILE, "segments block lists no peers")

    for c in comparators:
        name = c.get("name") if isinstance(c, dict) else c
        if name not in segment_names:
            report.error(PEERS_FILE, f"comparator '{name}' does not appear in any segment's peers")


def validate():
    """Load all three configs. Returns (Config or None, Report)."""
    report = Report()
    questions = _load_yaml(QUESTIONS_FILE, report)
    peers = _load_yaml(PEERS_FILE, report)
    sources = _load_yaml(SOURCES_FILE, report)

    question_ids = {}
    if questions is not None:
        question_ids = _check_questions(questions, report)
    if sources is not None:
        _check_sources(sources, question_ids, report)
        if questions is not None:
            _check_coverage(question_ids, report)
    if peers is not None:
        _check_peers(peers, report)

    if report.errors:
        return None, report
    return Config(questions=questions, peers=peers, sources=sources), report


def load():
    """Validate and return the config, or exit non-zero. Call at the start of every stage."""
    config, report = validate()
    if config is None:
        _print(report)
        sys.exit(1)
    return config


def _print(report):
    for e in report.errors:
        print(f"ERROR   {e}")
    for w in report.warnings:
        print(f"WARNING {w}")


def main():
    config, report = validate()
    _print(report)
    if config is None:
        print(f"\nConfig invalid: {len(report.errors)} error(s).")
        return 1

    print("Source coverage per question:")
    for q in config.questions["questions"]:
        backing = report.coverage.get(q["id"], [])
        print(f"  {q['id']} ({q['type']:6}) {len(backing):2}  {', '.join(backing) or '-'}")
    print(f"\nConfig valid. {len(report.warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
