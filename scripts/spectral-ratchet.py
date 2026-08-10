#!/usr/bin/env python3
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
#
# spectral-ratchet.py — per-rule baseline ratchet for adopting a Spectral
# ruleset against specs that predate it.
#
# REFERENCE IMPLEMENTATION, NOT A SUPPORTED KIT TOOL. It is documented and it
# works, and it carries no compatibility guarantee across kit releases. Copy it
# into your project and own it. The kit is a spec-authoring contract; it is
# deliberately not a CI product. See `schemas/README.md` §"Turning the ruleset
# on against existing specs" for the pattern this implements.
#
# WHY
#
# Switching a lint gate on against existing specs produces a large first number.
# Blocking every PR until it reaches zero means nothing merges for weeks, so the
# gate gets disabled — which is usually how a gate ends up broken. Running it
# non-blocking means errors accumulate exactly as before. Neither converges.
#
# A ratchet commits the current count PER RULE and fails only on regression.
# Inherited debt does not block PRs; new debt does.
#
#   a rule exceeds its baseline          -> fail (regression)
#   a rule absent from the baseline fires -> fail (newly violated rule)
#   a rule is below its baseline          -> pass, and say it can be lowered
#
# Per-rule, never a single total: a total-only ratchet lets someone introduce
# three new violations while fixing three old ones and call it even.
#
# THE FAILURE MODE THIS GUARDS AGAINST
#
# The failure mode of a validation tool is silence, and a ratchet is unusually
# exposed to it. A crashed Spectral emits no findings; zero findings is under
# every baseline; so a crash reads as a clean run AND as an improvement, and
# `--update` would then rewrite every baseline to zero and lock the broken state
# in permanently. Nothing later would ever fail.
#
# So this script applies the same contract as `scripts/spectral-lint.sh` (see
# authoring #14) and adds the check that matters here:
#
#   exit >= 2 from Spectral            -> could not run
#   empty or unparseable JSON report   -> could not run
#   zero findings while the baseline   -> could not run; REFUSE to --update
#   expects some                          (this is what a crash looks like)
#
# It reads JSON rather than shelling out to `spectral-lint.sh` because it needs
# machine-readable per-rule counts, and that wrapper emits human output. The
# crash contract is the part that matters and it is reproduced here in full.
#
# RULE IDS ARE A COUPLING SURFACE
#
# A committed baseline names rule IDs. The kit renamed every rule once already
# (`rm-*` -> `specfuse-*`), and a rename turns "rule not in the baseline" into a
# hard failure on every rule at once. This script detects that shape and tells
# you to re-baseline instead of dumping 200 spurious regressions.
#
# Usage:
#   spectral-ratchet.py --ruleset <path> --baseline <path> <target> [<target>...]
#   spectral-ratchet.py ... --update      # rewrite the baseline from this run
#
# Exit codes: 0 pass, 1 regression, 2 could not run.

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

SEVERITY_ERROR = 0  # Spectral: 0=error, 1=warn, 2=info, 3=hint


def die(msg: str, *extra: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    for line in extra:
        print(f"       {line}", file=sys.stderr)
    raise SystemExit(2)


def run_spectral(ruleset: Path, targets: list[str]) -> list[dict]:
    """Run Spectral and return its findings, or exit 2 if it did not run."""
    if shutil.which("spectral") is None:
        die(
            "spectral is not on PATH.",
            "npm install -g @stoplight/spectral-cli",
        )

    cmd = ["spectral", "lint", "--ruleset", str(ruleset), "--format", "json", *targets]
    proc = subprocess.run(cmd, capture_output=True, text=True)

    # Spectral exits 0 for clean, 1 for findings at/above fail-severity, and 2+
    # for "I could not run". Only the first two are verdicts about the spec.
    if proc.returncode >= 2:
        die(
            f"spectral exited {proc.returncode} — it FAILED TO RUN.",
            "This is not a clean spec. No findings were produced because no",
            "linting happened. Do not treat this as a pass.",
            (proc.stderr or proc.stdout).strip()[:500],
        )

    out = proc.stdout.strip()
    if not out:
        die(
            "spectral produced no output — treat as a failure, not a clean run.",
            "An empty report is what a crash looks like to a ratchet.",
        )

    try:
        findings = json.loads(out)
    except json.JSONDecodeError as exc:
        die(
            f"spectral output was not valid JSON ({exc}).",
            "Treating an unparseable report as a crash, not as zero findings.",
            out[:300],
        )

    if not isinstance(findings, list):
        die("spectral JSON was not a list of findings.")
    return findings


def counts_by_rule(findings: list[dict]) -> Counter:
    """Error-severity findings only — warnings are not what a gate blocks on."""
    return Counter(
        f.get("code", "<no-code>")
        for f in findings
        if f.get("severity", SEVERITY_ERROR) == SEVERITY_ERROR
    )


def load_baseline(path: Path) -> dict[str, int]:
    if not path.exists():
        die(
            f"no baseline at {path}.",
            "Create one from a clean run:",
            f"  {sys.argv[0]} --ruleset <r> --baseline {path} <target> --update",
        )
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        die(f"baseline {path} is not valid JSON ({exc}).")
    if not isinstance(data, dict) or not all(isinstance(v, int) for v in data.values()):
        die(f"baseline {path} must be an object of rule-id -> integer count.")
    return data


def looks_like_a_rename(baseline: dict[str, int], counts: Counter) -> bool:
    """Every baselined rule silent, and unknown rules firing instead.

    That is what a ruleset-wide rule rename looks like from in here, and it is
    worth naming: the alternative is reporting every rule as both cleared and
    newly violated at the same time.
    """
    if not baseline or not counts:
        return False
    baselined_all_silent = all(counts.get(rule, 0) == 0 for rule in baseline)
    unknown = [rule for rule in counts if rule not in baseline]
    return baselined_all_silent and len(unknown) >= max(2, len(baseline) // 2)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="spectral-ratchet.py",
        description="Per-rule Spectral baseline ratchet (reference implementation).",
    )
    ap.add_argument("--ruleset", required=True, type=Path)
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--update", action="store_true",
                    help="rewrite the baseline from this run")
    ap.add_argument("--force", action="store_true",
                    help="allow --update through the too-good-to-be-true guard")
    ap.add_argument("targets", nargs="+")
    args = ap.parse_args()

    counts = counts_by_rule(run_spectral(args.ruleset, args.targets))
    total = sum(counts.values())

    # --update on a first run has no baseline to protect; --update afterwards
    # must not be allowed to lock in a crash.
    baseline = load_baseline(args.baseline) if args.baseline.exists() else {}
    expected = sum(baseline.values())

    if expected > 0 and total == 0:
        die(
            f"0 error findings, but the baseline expects {expected}.",
            "A ratchet cannot tell a fixed codebase from a crashed linter, and",
            "this is the shape of a crash. Refusing to pass or to --update.",
            "If the specs really are clean, delete the baseline and re-create it.",
        )

    if looks_like_a_rename(baseline, counts):
        print(f"Errors: {total} (baseline {expected})")
        die(
            "every baselined rule is silent and unknown rules are firing.",
            "That is the shape of a ruleset-wide rule rename, not a regression.",
            "Re-baseline against the new rule IDs after confirming the counts:",
            f"  {sys.argv[0]} --ruleset {args.ruleset} --baseline {args.baseline} "
            f"{' '.join(args.targets)} --update",
        )

    regressions, new_rules, improvements = [], [], []
    for rule in sorted(set(baseline) | set(counts)):
        now, was = counts.get(rule, 0), baseline.get(rule)
        if was is None:
            if now:
                new_rules.append((rule, now))
        elif now > was:
            regressions.append((rule, was, now))
        elif now < was:
            improvements.append((rule, was, now))

    print(f"Errors: {total} (baseline {expected})")
    for rule, was, now in improvements:
        label = "CLEARED" if now == 0 else "improved"
        print(f"  ✅ {label}  {rule}: {was} -> {now}")
    for rule, was, now in regressions:
        print(f"  ❌ REGRESSION  {rule}: {was} -> {now}  (+{now - was})")
    for rule, now in new_rules:
        print(f"  ❌ NEW RULE VIOLATED  {rule}: {now}  (not in the baseline)")

    if args.update:
        # A total of zero is caught above, but a *near*-total collapse is the
        # same hazard one step short of it: a partially crashed run, or a
        # mistyped target that lints almost nothing, both look like a triumphant
        # cleanup. --update is the irreversible direction, so it is the one that
        # asks. A real cleanup passes --force and loses nothing.
        cleared = [r for r, was in baseline.items() if was > 0 and counts.get(r, 0) == 0]
        baselined = [r for r, was in baseline.items() if was > 0]
        if not args.force and len(baselined) >= 2 and len(cleared) >= max(2, len(baselined) / 2):
            die(
                f"{len(cleared)} of {len(baselined)} baselined rules went to zero at once.",
                "That is a real cleanup or a run that did not lint what you think",
                "it did — and --update cannot be undone from inside CI.",
                "Confirm the targets are right, then re-run with --force.",
                "Cleared: " + ", ".join(sorted(cleared)[:8]),
            )
        args.baseline.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n")
        print(f"\n==> baseline written to {args.baseline} ({total} errors across "
              f"{len(counts)} rule(s)).")
        return 0

    if regressions or new_rules:
        print("\n❌ Ratchet failed. Inherited debt does not block; new debt does.",
              file=sys.stderr)
        return 1

    print("\n✅ No regressions.", end="")
    if improvements:
        # Without this prompt the baseline silently retains headroom for errors
        # that no longer exist, and the ratchet stops ratcheting.
        print(" The count improved — run with --update to lock the gain in,")
        print("   otherwise the ratchet keeps allowing errors you have already fixed.")
    else:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
