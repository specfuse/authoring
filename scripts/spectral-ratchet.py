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
# Re-baselining, though, is the blunt fix: it accepts today's counts as the new
# floor and throws away the record of what you had already paid down. The sharp
# fix is to REKEY the baseline you have. `--migrate-rule-ids` does that, through
# `schemas/spectral/rule-renames.yaml`, and reports each baselined rule as:
#
#   renamed         the map names a successor; the count moves across
#   unchanged       already canonical; kept as-is
#   no counterpart  project-specific; the kit does not own it; kept as-is
#   retired         deleted with no successor; the key is DROPPED
#
# plus, in the other direction, every rule the kit defines that the baseline has
# no entry for. Those are new coverage: they will fail on the first run, and
# they need a deliberate seed rather than a surprise.
#
# The migration is held to the same standard as everything else here: a
# migration that leaves the baseline empty is refused, because an empty baseline
# is indistinguishable from a working one until the day it should have fired.
#
# Usage:
#   spectral-ratchet.py --ruleset <path> --baseline <path> <target> [<target>...]
#   spectral-ratchet.py ... --update             # rewrite the baseline from this run
#   spectral-ratchet.py --ruleset <path> --baseline <path> --migrate-rule-ids
#
# Exit codes: 0 pass, 1 regression, 2 could not run.

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import textwrap
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


# ---------------------------------------------------------------------------
# --migrate-rule-ids: rekey a committed baseline through the kit's rename map.
# Everything below is reached only by that flag, and PyYAML is imported lazily
# so the ratchet proper stays stdlib-only for anyone who copies it.
# ---------------------------------------------------------------------------

RENAME_MAP_NAME = "rule-renames.yaml"


def _yaml():
    try:
        import yaml  # noqa: PLC0415 — deliberately lazy, see above
    except ImportError:
        die(
            "--migrate-rule-ids needs PyYAML to read the rename map and the ruleset.",
            "  pip install PyYAML",
            "The ratchet itself is stdlib-only; this import is deliberately lazy",
            "so copying the script into a project does not add a dependency.",
        )
    return yaml


def _load_yaml(path: Path, what: str) -> dict:
    if not path.exists():
        die(f"no {what} at {path}.")
    try:
        doc = _yaml().safe_load(path.read_text())
    except Exception as exc:  # yaml.YAMLError, but yaml is imported lazily
        die(f"{what} {path} is not valid YAML ({exc}).")
    if not isinstance(doc, dict):
        die(f"{what} {path} must be a mapping.")
    return doc


def ruleset_rule_ids(path: Path, seen: set[Path] | None = None) -> set[str]:
    """Every rule id a ruleset declares, following its local `extends` files.

    A rule set to `off`/`false` is an inherited rule being DISABLED, not
    coverage — counting it would report a switched-off rule as new coverage the
    baseline is missing.
    """
    seen = seen if seen is not None else set()
    path = path.resolve()
    if path in seen:
        return set()
    seen.add(path)

    doc = _load_yaml(path, "ruleset")
    ids = {
        name
        for name, body in (doc.get("rules") or {}).items()
        if body not in (False, "off", None)
    }

    extends = doc.get("extends")
    for entry in extends if isinstance(extends, list) else [extends]:
        # `extends` entries are either a path, or a [path, severity] pair. The
        # built-in rulesets ("spectral:oas") are not ours to audit.
        target = entry[0] if isinstance(entry, (list, tuple)) and entry else entry
        if not isinstance(target, str) or target.startswith("spectral:"):
            continue
        child = (path.parent / target).resolve()
        if child.exists():
            ids |= ruleset_rule_ids(child, seen)
    return ids


def load_rename_map(path: Path, ruleset: Path) -> tuple[dict, dict, dict, set, str | None]:
    """Flatten the per-surface map, and say which surface `ruleset` is.

    Rule ids are globally unique across the three surfaces, so a baseline that
    spans them migrates correctly against the flattened map. The surface is
    still identified, because it is what makes the staleness check possible:
    only the surface matching `--ruleset` can be checked against it.
    """
    doc = _load_yaml(path, "rename map")
    surfaces = doc.get("rulesets")
    if not isinstance(surfaces, dict) or not surfaces:
        die(f"rename map {path} declares no `rulesets:`.")

    renames: dict[str, str] = {}
    non_mechanical: dict[str, dict] = {}
    retained: dict[str, dict] = {}
    retired: set[str] = set()
    surface: str | None = None

    for name, body in surfaces.items():
        if not isinstance(body, dict):
            die(f"rename map {path}: surface `{name}` must be a mapping.")
        for legacy, canonical in (body.get("renames") or {}).items():
            if renames.get(legacy, canonical) != canonical:
                die(
                    f"rename map {path}: `{legacy}` maps to two different ids "
                    f"({renames[legacy]} and {canonical}).",
                    "Rule ids are global; an id cannot have two successors.",
                )
            renames[legacy] = canonical
        non_mechanical.update(body.get("non_mechanical") or {})
        retained.update(body.get("retained") or {})
        retired.update(body.get("retired") or [])
        if Path(str(body.get("kit", ""))).name == ruleset.name:
            surface = name

    if not renames:
        die(f"rename map {path} declares no renames — nothing to migrate through.")
    return renames, non_mechanical, retained, retired, surface


def check_map_is_live(path: Path, surfaces_doc: dict, surface: str | None,
                      ruleset: Path, kit_ids: set[str]) -> None:
    """Refuse a stale map rather than migrating a baseline onto dead rule ids.

    Only the surface whose `kit:` file matches `--ruleset` can be checked: the
    other surfaces name rules this ruleset legitimately does not define.
    """
    if surface is None:
        print(f"    note: {path} declares no surface for {ruleset.name}, so its "
              f"targets could not be checked against it.")
        return
    targets = set((surfaces_doc[surface].get("renames") or {}).values())
    missing = sorted(targets - kit_ids)
    if missing:
        die(
            f"the rename map is stale for surface `{surface}`.",
            f"It maps onto {len(missing)} rule id(s) that {ruleset} does not define:",
            "  " + ", ".join(missing[:8]),
            "Migrating through it would move counts onto rules that no longer",
            "exist, which is silence with extra steps. Fix the map first.",
        )


def migrate_rule_ids(args) -> int:
    baseline = load_baseline(args.baseline)
    if not baseline:
        die(
            f"baseline {args.baseline} is empty — there is nothing to migrate.",
            "An empty baseline is not a starting point; it is a gate with no floor.",
        )

    map_path = args.rule_renames or (args.ruleset.parent / RENAME_MAP_NAME)
    renames, non_mechanical, retained, retired, surface = load_rename_map(
        map_path, args.ruleset)
    kit_ids = ruleset_rule_ids(args.ruleset)
    if not kit_ids:
        die(f"{args.ruleset} declares no rules — refusing to migrate against it.")

    print(f"==> migrating {args.baseline} through {map_path}")
    print(f"    {len(baseline)} baselined rule(s); {args.ruleset.name} defines {len(kit_ids)}")
    check_map_is_live(map_path, _load_yaml(map_path, "rename map")["rulesets"],
                      surface, args.ruleset, kit_ids)

    migrated: dict[str, int] = {}
    sources: dict[str, list[str]] = {}
    dropped: list[tuple[str, int]] = []
    flagged: list[str] = []

    for rule, count in sorted(baseline.items()):
        if rule in retired:
            dropped.append((rule, count))
            print(f"  🗑  RETIRED         {rule}: {count} — no successor; key dropped")
            continue
        target = renames.get(rule)
        if target is not None:
            note = non_mechanical.get(rule)
            if note:
                flagged.append(rule)
                print(f"  ⚠️  RENAMED*        {rule} -> {target}  "
                      f"(NOT a prefix swap, kind: {note.get('kind', 'renamed')})")
            else:
                print(f"  ↦  renamed         {rule} -> {target}")
        elif rule in kit_ids:
            target = rule
            print(f"  ·  unchanged       {rule} — already canonical")
        else:
            target = rule
            entry = retained.get(rule) or {}
            overlay = entry.get("overlay_for") or entry.get("partially_superseded_by")
            tail = f" (the kit's {overlay} covers the shape only)" if overlay else ""
            print(f"  ▸  no counterpart  {rule} — project-specific; kept{tail}")
        migrated[target] = migrated.get(target, 0) + count
        sources.setdefault(target, []).append(rule)

    collisions = {t: s for t, s in sources.items() if len(s) > 1}
    if collisions:
        die(
            f"{len(collisions)} rule id(s) would be written twice by this migration.",
            *[f"  {t} <- {', '.join(s)}" for t, s in sorted(collisions.items())],
            "That happens when a rule was MERGED into another one and both legacy",
            "ids carry a count. Summing them double-counts and taking one of them",
            "discards debt, so neither is safe to guess. Resolve the entries by",
            "hand — or re-seed those rules with --update and read the diff.",
        )

    # Silence is failure, and it is failure here too. A migration that leaves
    # nothing behind produces a baseline that can never fail, which is exactly
    # the state --update refuses to write for the same reason.
    if not migrated or sum(migrated.values()) == 0:
        die(
            f"the migration would leave the baseline empty ({len(baseline)} rule(s) in, "
            f"{len(migrated)} out).",
            "An empty baseline never fails, so this cannot be distinguished from a",
            "working gate until the day it should have fired. Refusing to write it.",
            "Dropped: " + ", ".join(r for r, _ in dropped[:8]) if dropped else
            "Every entry migrated to a zero count.",
        )

    new_in_kit = sorted(kit_ids - set(migrated))
    print(f"\n==> {len(migrated)} rule(s) after migration "
          f"({sum(migrated.values())} errors carried).")

    if flagged:
        print(f"\n⚠️  {len(flagged)} rename(s) were NOT a prefix swap. A mechanical "
              f"rewrite gets these wrong,")
        print("   and the successor's semantics may differ — re-read the count "
              "rather than trusting it:")
        for rule in flagged:
            print(f"     {rule} -> {renames[rule]}")
            note = " ".join((non_mechanical[rule].get("note") or "").split())
            if note:
                print(textwrap.fill(note, width=78, initial_indent="       ",
                                    subsequent_indent="       "))

    if new_in_kit:
        print(f"\n📋 {len(new_in_kit)} rule(s) are defined by {args.ruleset.name} with "
              f"no baseline entry.")
        print("   These are new coverage. Any of them that fires will fail the ratchet")
        print("   on the first run — which is correct, but it should be a decision and")
        print("   not a surprise. Seed them deliberately: run once without --update,")
        print("   read what fires, fix what should be fixed, then --update the rest.")
        for rule in new_in_kit:
            print(f"     {rule}")

    if args.dry_run:
        print(f"\n(--dry-run: {args.baseline} not written.)")
        return 0

    args.baseline.write_text(json.dumps(dict(sorted(migrated.items())), indent=2) + "\n")
    print(f"\n==> {args.baseline} rekeyed. Commit it with the ruleset bump, "
          f"not separately.")
    return 0


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
    ap.add_argument("--migrate-rule-ids", action="store_true",
                    help="rekey the baseline through the ruleset's rule-renames.yaml "
                         "instead of linting; does not run Spectral")
    ap.add_argument("--rule-renames", type=Path, default=None,
                    help=f"rename map (default: {RENAME_MAP_NAME} beside --ruleset)")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --migrate-rule-ids, report without writing")
    ap.add_argument("targets", nargs="*")
    args = ap.parse_args()

    if args.migrate_rule_ids:
        if args.update:
            die("--migrate-rule-ids and --update do opposite things.",
                "--update accepts today's counts as the new floor; --migrate-rule-ids",
                "carries the counts you already have onto the new ids. Pick one.")
        if args.targets:
            die("--migrate-rule-ids does not lint, so it takes no targets.",
                f"Unexpected: {' '.join(args.targets)}")
        return migrate_rule_ids(args)

    if args.dry_run or args.rule_renames:
        # Silently ignoring a flag is how someone believes a run was a dry one.
        die("--dry-run and --rule-renames only apply to --migrate-rule-ids.",
            "A lint run does not read the rename map and --update is not a dry",
            "operation, so accepting these here would promise something false.")

    if not args.targets:
        die("no targets given — nothing to lint.",
            "Pass the specs to lint, or --migrate-rule-ids to rekey the baseline.")

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
            "Rekey the baseline you have — it keeps the debt you already paid down:",
            f"  {sys.argv[0]} --ruleset {args.ruleset} --baseline {args.baseline} "
            f"--migrate-rule-ids",
            "That maps every id through the ruleset's rule-renames.yaml and names",
            "the renames a prefix swap gets wrong. Only if no map covers this",
            "ruleset, re-baseline from scratch and read the diff:",
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
