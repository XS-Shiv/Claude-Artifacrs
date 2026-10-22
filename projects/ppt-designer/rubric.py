"""Score a deck on the skill's five-criterion rubric and list the weakest first.

The skill scores every finished deck on Clarity, Feasibility, Evidence, Story and
Q&A readiness, each at 1, 3 or 5, and asks for anything under 5 to be fixed.
This turns the scores into a short report: weakest criteria first, what the
current level looks like and what a 5 needs.

Usage:
    python rubric.py clarity=5 feasibility=3 evidence=1 story=3 qa=5
    python rubric.py clarity=5 feasibility=3 evidence=1 story=3 qa=5 --strict
"""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

# criterion key -> (label, {level: description}), copied from the table in SKILL.md
RUBRIC: dict[str, tuple[str, dict[int, str]]] = {
    "clarity": ("Clarity", {1: "Hard to follow", 3: "Mostly clear", 5: "Crisp and answer-first"}),
    "feasibility": ("Feasibility", {1: "Unclear execution", 3: "Some plan", 5: "Cost, owners and timeline clear"}),
    "evidence": ("Evidence", {1: "Claims only", 3: "Some backing", 5: "Numbers and sources"}),
    "story": ("Story", {1: "Disconnected", 3: "Logical sequence", 5: "Memorable narrative"}),
    "qa": ("Q&A readiness", {1: "Weak backup", 3: "Some answers", 5: "Appendix-ready"}),
}
LEVELS = (1, 3, 5)


def parse_scores(pairs: Sequence[str]) -> dict[str, int]:
    """Turn ["clarity=5", ...] into {"clarity": 5, ...}; every criterion, once, at 1, 3 or 5."""
    scores: dict[str, int] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        key = key.strip().lower().replace("&", "").replace(" ", "")
        if not sep or key not in RUBRIC:
            raise ValueError(f"expected one of {', '.join(RUBRIC)} as name=score, got {pair!r}")
        if key in scores:
            raise ValueError(f"{key} is scored twice")
        try:
            level = int(value)
        except ValueError:
            raise ValueError(f"{key} score must be 1, 3 or 5, got {value!r}") from None
        if level not in LEVELS:
            raise ValueError(f"{key} score must be 1, 3 or 5, got {level}")
        scores[key] = level
    missing = [k for k in RUBRIC if k not in scores]
    if missing:
        raise ValueError(f"missing scores for: {', '.join(missing)}")
    return scores


def ranked(scores: dict[str, int]) -> list[str]:
    """Criteria weakest first; ties keep the rubric's own order."""
    order = list(RUBRIC)
    return sorted(scores, key=lambda k: (scores[k], order.index(k)))


def report(scores: dict[str, int]) -> str:
    total = sum(scores.values())
    to_fix = [k for k in ranked(scores) if scores[k] < 5]
    lines = [f"RUBRIC  {total}/25  |  {len(to_fix)} of 5 under 5", ""]
    for key in ranked(scores):
        label, levels = RUBRIC[key]
        level = scores[key]
        line = f"{level}  {label:<14} {levels[level]}"
        if level < 5:
            line += f"  ->  needs: {levels[5]}"
        lines.append(line)
    if to_fix:
        lines += ["", "Fix first: " + RUBRIC[to_fix[0]][0]]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score a deck on the skill's rubric.")
    ap.add_argument("scores", nargs="+", help="name=score for clarity, feasibility, evidence, story, qa")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any criterion is under 5")
    args = ap.parse_args(argv)
    try:
        scores = parse_scores(args.scores)
    except ValueError as exc:
        ap.error(str(exc))
    print(report(scores))
    return 1 if args.strict and min(scores.values()) < 5 else 0


if __name__ == "__main__":
    sys.exit(main())
