#!/usr/bin/env python3
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
#
# spectral-overlay-diff.py — classify a project Spectral ruleset against the
# kit's, so an overlay that FORKED from the kit can be reduced safely.
#
# KIT-OWNED, AND SHIPPED INTO PROJECTS. It lives in `scripts/specfuse/`, which
# `specfuse authoring upgrade` replaces wholesale — edits here are overwritten on
# the next upgrade. That is the opposite of `spectral-ratchet.py`, which stays a
# copy-it-and-own-it reference implementation in the kit repo, and the difference
# is deliberate: the ratchet is run for months inside a project's own CI, where
# local ownership is the point, while this one is run DURING an upgrade — the
# moment when telling someone to go fetch a file from another repository is worst.
#
# In a project:
#
#   python3 scripts/specfuse/spectral-overlay-diff.py \
#     --kit-ruleset     .specfuse/authoring/schemas/spectral/specfuse-openapi.yaml \
#     --project-ruleset api/spectral.myproject.yaml
#
# See `.specfuse/authoring/schemas/README.md` §"Reducing an overlay that forked
# from the kit" for the procedure this supports.
#
# WHY
#
# `schemas/README.md` documents adopting the rulesets FRESH: extend them, add
# your value-set overlays, done. The case that actually occurs is the other one.
# The kit's rulesets were generalised from a real project by renaming `rm-*` to
# `specfuse-*`, so that project — and every project bootstrapped from a copy of
# its ruleset — holds a fork of the kit's own rules under different ids. For
# them, adopting the kit means DELETING duplicates, not adding rules. A naive
# `extends:` double-reports every shared rule: two ids, one finding each, same
# violation.
#
# Which of your rules the kit now owns is the entire decision, and it is not
# visible by reading either file. Against the source project's own OpenAPI
# overlay it comes out as 89 rules against 111: 50 exact duplicates, 32 the same
# rule with a drifted body, 7 genuinely the project's, and 29 kit rules it has
# never run. Doing that by eye is how a rule that still mattered gets deleted
# along with the duplicates — and how the 32 get deleted as if they were the 50.
#
# WHAT IT DOES
#
# Every rule the project DECLARES lands in exactly one bucket:
#
#   redundant         the kit owns it, and the two bodies select and check the
#                     same thing. Safe to delete once you extend the kit.
#   diverged          the kit owns the id, but the bodies differ. NOT safe to
#                     delete blind — the difference is printed, read it. Most
#                     often the kit's `given` is the repaired one (authoring
#                     #73) and yours has been inert.
#   project-specific  no kit counterpart. Keep. Usually a value-set overlay of
#                     a shape-only kit rule — the rename map names which one.
#
# and, in the other direction:
#
#   kit-only-new      a kit rule you have no equivalent of. Real new coverage
#                     and real new findings on the day you extend.
#
# Ids are matched through `schemas/spectral/rule-renames.yaml`, because the
# fork predates the rename and a same-id match alone would find nothing.
#
# THE FAILURE MODE THIS GUARDS AGAINST
#
# The same one as everything else here: silence. "No redundant rules" is both
# the success state and what this script emits if it was pointed at the wrong
# pair of files, handed a stale rename map, or given a ruleset it could not
# parse. So each of those is a hard `could not run` rather than a clean report:
#
#   either ruleset declares no rules            -> exit 2
#   the rename map names ids the kit dropped    -> exit 2 (stale map)
#   nothing matches AND the project does not    -> exit 2 (wrong pair)
#     already extend the kit ruleset
#
# The last one is the important one. A project that has finished the reduction
# extends the kit and shares nothing else, which is legitimately zero overlap;
# a project that has not, and shares nothing, was compared against the wrong
# file. Only the `extends` edge tells those two apart.
#
# The project ruleset is read WITHOUT following `extends`, deliberately: the
# question is which rules the project itself declares, and following the chain
# after adoption would report the kit's own rules back as the project's.
#
# Usage (from the kit repo; see above for the in-project form):
#   spectral-overlay-diff.py \
#     --kit-ruleset schemas/spectral/specfuse-openapi.yaml \
#     --project-ruleset api/spectral.myproject.yaml \
#     [--rule-renames <path>] [--json out.json] [--report-only]
#
# Exit codes: 0 nothing redundant, 1 redundant rules found, 2 could not run.

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced to the operator, not handled
    sys.exit("spectral-overlay-diff: PyYAML is required (pip install PyYAML)")

RENAME_MAP_NAME = "rule-renames.yaml"

# A rule set to any of these is an inherited rule being switched OFF. It carries
# no `given`, so it cannot be compared field by field — but "we both disable the
# same upstream rule" is a genuine redundancy, so it gets its own comparable
# value rather than being skipped.
OFF_VALUES = (False, None, "off")
OFF = "<off>"

# The fields that decide what a rule SELECTS and what it CHECKS. `description`,
# `message` and `severity` are deliberately excluded: they change how a finding
# reads, not whether it happens, and a project that only reworded a rule has a
# duplicate, not a divergence. Severity is reported separately, because deleting
# a `warn` copy of an `error` rule tightens the gate and that is worth knowing.
SEMANTIC_FIELDS = ("given", "then", "resolved", "formats")


def die(msg: str, *extra: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    for line in extra:
        print(f"       {line}", file=sys.stderr)
    raise SystemExit(2)


def load_yaml(path: Path, what: str) -> dict:
    if not path.exists():
        die(f"no {what} at {path}.")
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        die(f"{what} {path} is not valid YAML ({exc}).")
    if not isinstance(doc, dict):
        die(f"{what} {path} must be a mapping.")
    return doc


def declared_rules(doc: dict) -> dict[str, object]:
    """Rule id -> body, with disabled rules collapsed to a comparable marker."""
    return {
        name: (OFF if body in OFF_VALUES else body)
        for name, body in (doc.get("rules") or {}).items()
    }


def extends_paths(doc: dict, base: Path) -> list[Path]:
    """Local files a ruleset extends. Built-ins ('spectral:oas') are not ours."""
    extends = doc.get("extends")
    out = []
    for entry in extends if isinstance(extends, list) else [extends]:
        target = entry[0] if isinstance(entry, (list, tuple)) and entry else entry
        if not isinstance(target, str) or target.startswith("spectral:"):
            continue
        out.append((base.parent / target).resolve())
    return out


def semantics(body: object) -> str:
    """A canonical string for what a rule selects and checks.

    Whitespace inside a JSONPath is collapsed so that a reflowed `given` does
    not read as a behaviour change. Nothing beyond that is normalised: this
    comparison decides whether a rule is safe to DELETE, so a false 'identical'
    costs a live rule while a false 'diverged' costs one reading of a diff.
    """
    if body == OFF:
        return OFF
    if not isinstance(body, dict):
        return json.dumps(body, sort_keys=True)

    def collapse(value):
        if isinstance(value, str):
            return " ".join(value.split())
        if isinstance(value, list):
            return [collapse(v) for v in value]
        if isinstance(value, dict):
            return {k: collapse(v) for k, v in value.items()}
        return value

    fields = {}
    for key in SEMANTIC_FIELDS:
        if key == "resolved":
            fields[key] = body.get("resolved", True)  # Spectral's default
        elif key in body:
            value = collapse(body[key])
            # A single `given` and a one-element list of the same `given` are
            # the same rule; Spectral accepts both spellings.
            if key == "given" and not isinstance(value, list):
                value = [value]
            fields[key] = value
    return json.dumps(fields, sort_keys=True)


def severity_of(body: object) -> str:
    if body == OFF:
        return "off"
    return str((body or {}).get("severity", "warn")) if isinstance(body, dict) else "?"


def load_rename_map(path: Path, kit: Path) -> tuple[dict, dict, dict, str | None]:
    doc = load_yaml(path, "rename map")
    surfaces = doc.get("rulesets")
    if not isinstance(surfaces, dict) or not surfaces:
        die(f"rename map {path} declares no `rulesets:`.")

    renames: dict[str, str] = {}
    non_mechanical: dict[str, dict] = {}
    retained: dict[str, dict] = {}
    surface: str | None = None
    for name, body in surfaces.items():
        if not isinstance(body, dict):
            die(f"rename map {path}: surface `{name}` must be a mapping.")
        renames.update(body.get("renames") or {})
        non_mechanical.update(body.get("non_mechanical") or {})
        retained.update(body.get("retained") or {})
        if Path(str(body.get("kit", ""))).name == kit.name:
            surface = name

    if surface is not None:
        # Only this surface can be checked: the others name rules the kit file
        # under comparison legitimately does not define.
        targets = set((surfaces[surface].get("renames") or {}).values())
        kit_ids = set(declared_rules(load_yaml(kit, "kit ruleset")))
        missing = sorted(targets - kit_ids)
        if missing:
            die(
                f"the rename map is stale for surface `{surface}`.",
                f"It maps onto {len(missing)} id(s) {kit.name} does not define:",
                "  " + ", ".join(missing[:8]),
                "Every classification below it would be wrong in the same",
                "direction — rules reported as project-specific because their",
                "counterpart was looked up under a dead name. Fix the map first.",
            )
    return renames, non_mechanical, retained, surface


def wrap(text: str, indent: str = "      ") -> str:
    return textwrap.fill(" ".join(text.split()), width=78,
                         initial_indent=indent, subsequent_indent=indent,
                         break_on_hyphens=False, break_long_words=False)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="spectral-overlay-diff.py",
        description="Classify a forked project ruleset against the kit's.",
    )
    ap.add_argument("--kit-ruleset", required=True, type=Path)
    ap.add_argument("--project-ruleset", required=True, type=Path)
    ap.add_argument("--rule-renames", type=Path, default=None,
                    help=f"rename map (default: {RENAME_MAP_NAME} beside --kit-ruleset)")
    ap.add_argument("--json", type=Path, default=None,
                    help="also write the classification as JSON")
    ap.add_argument("--report-only", action="store_true",
                    help="exit 0 even when redundant rules are found")
    args = ap.parse_args()

    kit_doc = load_yaml(args.kit_ruleset, "kit ruleset")
    proj_doc = load_yaml(args.project_ruleset, "project ruleset")
    kit_rules = declared_rules(kit_doc)
    proj_rules = declared_rules(proj_doc)

    # A ruleset with no rules is not a clean comparison, it is a parse that went
    # somewhere unexpected — and it would report every kit rule as new coverage
    # or every project rule as project-specific, both of them confidently.
    if not kit_rules:
        die(f"{args.kit_ruleset} declares no rules — nothing to compare against.")
    if not proj_rules:
        die(f"{args.project_ruleset} declares no rules.",
            "If the overlay is already reduced to nothing but `extends`, there is",
            "no overlay left to diff.")

    map_path = args.rule_renames or (args.kit_ruleset.parent / RENAME_MAP_NAME)
    renames, non_mechanical, retained, surface = load_rename_map(map_path, args.kit_ruleset)

    already_extends = args.kit_ruleset.resolve() in extends_paths(
        proj_doc, args.project_ruleset.resolve())

    redundant, diverged, specific = [], [], []
    matched_kit: set[str] = set()

    for name, body in sorted(proj_rules.items()):
        counterpart = name if name in kit_rules else renames.get(name)
        if counterpart not in kit_rules:
            entry = retained.get(name) or {}
            specific.append((name, entry))
            continue
        matched_kit.add(counterpart)
        same = semantics(body) == semantics(kit_rules[counterpart])
        row = (name, counterpart, severity_of(body), severity_of(kit_rules[counterpart]))
        (redundant if same else diverged).append(row)

    kit_only = sorted(set(kit_rules) - matched_kit)

    if not matched_kit and not already_extends:
        die(
            f"not one of {len(proj_rules)} project rules matched any of "
            f"{len(kit_rules)} kit rules.",
            f"{args.project_ruleset.name} also does not extend "
            f"{args.kit_ruleset.name}, so this is not a reduced overlay —",
            "it is almost certainly the wrong pair of files (the OpenAPI",
            "ruleset against the AsyncAPI overlay, say). Reporting 'nothing is",
            "redundant' here would be a clean bill of health for a comparison",
            "that never happened.",
        )

    print(f"==> {args.project_ruleset} vs {args.kit_ruleset}")
    print(f"    surface: {surface or '(not declared in the rename map)'}"
          f"    map: {map_path}")
    print(f"    {len(proj_rules)} project rule(s), {len(kit_rules)} kit rule(s), "
          f"{len(matched_kit)} matched")
    if already_extends:
        print(f"    {args.project_ruleset.name} already extends {args.kit_ruleset.name}.")

    print(f"\n--- REDUNDANT ({len(redundant)}) — the kit owns these; delete them once "
          f"you extend it")
    for name, kit_name, ps, ks in redundant:
        tail = f"   [severity {ps} -> {ks}]" if ps != ks else ""
        print(f"  ✂  {name}  ->  {kit_name}{tail}")
    if any(ps != ks for _, _, ps, ks in redundant):
        print(wrap("A severity change is not a reason to keep the rule, but it is a "
                   "reason to expect the finding count to move: deleting a `warn` copy "
                   "of an `error` rule turns those findings into gate failures."))

    print(f"\n--- DIVERGED ({len(diverged)}) — same rule, different body; READ THE DIFF")
    for name, kit_name, ps, ks in diverged:
        print(f"  ⚠  {name}  ->  {kit_name}"
              + (f"   [severity {ps} -> {ks}]" if ps != ks else ""))
        for field in SEMANTIC_FIELDS:
            mine = json.loads(semantics(proj_rules[name])).get(field) \
                if semantics(proj_rules[name]) != OFF else OFF
            theirs = json.loads(semantics(kit_rules[kit_name])).get(field) \
                if semantics(kit_rules[kit_name]) != OFF else OFF
            if mine != theirs:
                print(f"       {field}:")
                print(f"         yours: {json.dumps(mine)[:160]}")
                print(f"         kit:   {json.dumps(theirs)[:160]}")
        if name in non_mechanical:
            print(wrap("NON-MECHANICAL RENAME. " +
                       (non_mechanical[name].get("note") or ""), indent="       "))

    print(f"\n--- PROJECT-SPECIFIC ({len(specific)}) — no kit counterpart; KEEP")
    for name, entry in specific:
        if entry.get("overlay_for"):
            tail = f"   (value set for the kit's shape-only {entry['overlay_for']})"
        elif entry.get("partially_superseded_by"):
            tail = f"   (PARTLY covered by the kit's {entry['partially_superseded_by']})"
        else:
            tail = ""
        print(f"  ●  {name}{tail}")
        if entry.get("note"):
            print(wrap(entry["note"], indent="       "))

    if already_extends:
        # The overlay already inherits these, so they are not pending coverage —
        # calling them "new" would send someone off to seed a baseline for rules
        # that have been running all along.
        print(f"\n--- INHERITED ({len(kit_only)}) — kit rules with no local twin, "
              f"already running via `extends`")
    else:
        print(f"\n--- KIT-ONLY, NEW ({len(kit_only)}) — coverage you have never run")
        for name in kit_only:
            print(f"  +  {name}")
        if kit_only:
            print(wrap("These fire for the first time on the day you extend the kit. "
                       "Seed them into the baseline deliberately — `spectral-ratchet.py "
                       "--migrate-rule-ids` lists exactly this set for the same reason."))

    if args.json:
        args.json.write_text(json.dumps({
            "kit_ruleset": str(args.kit_ruleset),
            "project_ruleset": str(args.project_ruleset),
            "surface": surface,
            "already_extends_kit": already_extends,
            "redundant": [
                {"project": n, "kit": k, "project_severity": ps, "kit_severity": ks}
                for n, k, ps, ks in redundant],
            "diverged": [
                {"project": n, "kit": k, "project_severity": ps, "kit_severity": ks}
                for n, k, ps, ks in diverged],
            "project_specific": [dict(rule=n, **e) for n, e in specific],
            "kit_only_new": kit_only,
        }, indent=2) + "\n")
        print(f"\n==> classification written to {args.json}")

    print(f"\n==> {len(redundant)} redundant, {len(diverged)} diverged, "
          f"{len(specific)} project-specific, {len(kit_only)} "
          f"{'inherited from' if already_extends else 'new from'} the kit.")

    if redundant and not args.report_only:
        print("\n❌ The overlay still duplicates rules the kit owns. Extending the kit "
              "as-is\n   double-reports every one of them. See "
              "schemas/README.md §\"Reducing an overlay\n   that forked from the kit\" "
              "(shipped at .specfuse/authoring/schemas/README.md)\n   for the order to "
              "do this in.", file=sys.stderr)
        return 1

    print("\n✅ Nothing in this overlay duplicates a kit rule.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
