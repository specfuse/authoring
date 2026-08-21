#!/usr/bin/env python3
#
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
#
# spectral-rule-coverage.py — prove that every rule's `given` selects something.
#
# WHY THIS EXISTS
#
# A Spectral rule only speaks when a document violates it. A rule whose `given`
# selects zero nodes is therefore INDISTINGUISHABLE from a rule that passes: a
# conformant spec and a dead rule produce the identical clean run. No amount of
# green CI surfaces the difference, because the signal CI reads — "no findings"
# — is exactly what a dead rule emits.
#
# That is not hypothetical. Authoring issue #73 led to thirteen inert rules,
# eleven of them `severity: error`. Twelve had a `given` of this shape:
#
#     $.paths[*][get,post,put,patch,delete][?(@ && @.security)]
#
# which reads as "every secured operation" and evaluates as "every CHILD of an
# operation that itself has a .security" — the empty set, in every valid OpenAPI
# document ever written. The 400/401/403/404 error-envelope gates, the
# authorization metadata gates and the pagination gate had never fired in any
# consuming project. The thirteenth had a working `given` and was dead for the
# resolution reason under WHAT THIS DOES NOT DO, below.
#
# WHAT THIS DOES
#
# For each rule in a ruleset it synthesises a probe rule with the SAME `given`
# and `resolved` setting, but a `then` that fails against literally any value:
#
#     then: { function: schema, functionOptions: { schema: { not: {} } } }
#
# `not: {}` matches nothing, so every selected node reports. Running the probe
# ruleset over a corpus therefore yields, per rule, the number of nodes its
# `given` actually selects. Zero means the rule is inert.
#
# The batch pass is not trusted on its own. Spectral compiles every rule's
# JSONPath into one traversal program (nimma), and structurally similar
# expressions can suppress one another: probing `specfuse-404-predefined`
# alongside `specfuse-400-predefined` makes the first report zero nodes, while
# probing it by itself reports eleven. A harness that read that batch result
# literally would announce a live rule as dead — the same "silence means
# nothing is there" mistake it exists to catch, one level up. So every
# zero-match from the batch pass is re-probed ALONE before it is believed.
#
# A `given` can also legitimately select nothing because the corpus contains no
# instance of the construct it targets (no DELETE operations, no `info.x-services`).
# Those are declared in a coverage allowlist with a reason. The allowlist is
# checked in BOTH directions: an undeclared zero-match fails the build, and so
# does a declared entry that now matches, so the allowlist cannot quietly rot
# into a list of everything.
#
# WHAT THIS DOES NOT DO
#
# It proves a rule SELECTS. It does not prove the rule REJECTS: a `then` can be
# silent on a live `given` too — `function: pattern` reports nothing when the
# field is absent, and a `field: $ref` check on a resolved document sees an
# already-inlined ref. Both of those also shipped in this ruleset, on five rules
# between them. Catching them needs per-rule violating fixtures, which is the
# layer above this one — see fixtures/inert-rules-regression.yaml.
#
# Usage:
#   scripts/spectral-rule-coverage.py \
#     --ruleset schemas/spectral/specfuse-openapi.yaml \
#     --allowlist schemas/spectral/coverage-allowlist.yaml \
#     <target> [target ...]
#
# Targets may be files or glob patterns. Exit 0 = every rule accounted for.

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced to the operator, not handled
    sys.exit("spectral-rule-coverage: PyYAML is required (pip install PyYAML)")

PROBE_PREFIX = "coverage-probe--"
# Matches no value of any type, so every node the `given` selects reports.
UNIVERSAL_FAIL = {"function": "schema", "functionOptions": {"schema": {"not": {}}}}


def rule_givens(ruleset: dict) -> dict[str, list[tuple[str, bool]]]:
    """Map rule name -> [(given, resolved), ...] for every enabled rule."""
    out: dict[str, list[tuple[str, bool]]] = {}
    for name, body in (ruleset.get("rules") or {}).items():
        # `rule: off` / `rule: false` disable an inherited rule and carry no given.
        if not isinstance(body, dict):
            continue
        given = body.get("given")
        if given is None:
            continue
        resolved = body.get("resolved", True)
        givens = given if isinstance(given, list) else [given]
        out[name] = [(g, resolved) for g in givens if isinstance(g, str)]
    return out


def build_probe(ruleset: dict, givens: dict[str, list[tuple[str, bool]]]) -> dict:
    """A ruleset of universal-fail probes, one per (rule, given) pair.

    `extends` is deliberately dropped: inherited rules are not ours to audit and
    would drown the report. `formats` IS carried over, because a probe whose
    format does not match the target is silently skipped and would read as a
    zero-match — the very false negative this script exists to prevent.
    """
    probes: dict[str, dict] = {}
    for name, entries in givens.items():
        for idx, (given, resolved) in enumerate(entries):
            key = name if len(entries) == 1 else f"{name}#{idx}"
            probe = {
                "description": "coverage probe",
                "severity": "warn",
                "given": given,
                "then": UNIVERSAL_FAIL,
            }
            if not resolved:
                probe["resolved"] = False
            probes[PROBE_PREFIX + key] = probe
    out: dict = {"rules": probes}
    if "formats" in ruleset:
        out["formats"] = ruleset["formats"]
    return out


def expand(targets: list[str]) -> list[str]:
    files: list[str] = []
    for t in targets:
        hits = sorted(glob.glob(t, recursive=True)) if any(c in t for c in "*?[") else [t]
        if not hits:
            sys.exit(f"spectral-rule-coverage: target matched no files: {t}")
        files.extend(hits)
    return files


def run_probe(probe_path: str, targets: list[str]) -> tuple[set[str], str | None]:
    """Return the set of probe codes that fired, or an error string."""
    proc = subprocess.run(
        ["spectral", "lint", "--ruleset", probe_path, "-f", "json", *targets],
        capture_output=True,
        text=True,
    )
    where = ", ".join(targets) if len(targets) < 4 else f"{len(targets)} targets"
    # Spectral exits 0 (clean) or 1 (findings at/above fail severity). Anything
    # higher means it could not run, and an empty report from a crash must never
    # be read as "these rules selected nothing" — that is a silent all-clear.
    if proc.returncode >= 2:
        return set(), f"spectral exited {proc.returncode} on {where}:\n{proc.stderr.strip()}"
    if not proc.stdout.strip():
        return set(), f"spectral produced no output on {where} — treat as a crash, not a clean run."
    # With several targets the CLI can emit one JSON array PER DOCUMENT rather
    # than one array overall, so the stream is a concatenation of values, not a
    # single document. Decode it incrementally instead of assuming either shape.
    findings: list = []
    decoder, text, pos, decoded = json.JSONDecoder(), proc.stdout, 0, False
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            break
        try:
            value, pos = decoder.raw_decode(text, pos)
        except json.JSONDecodeError as exc:
            # On a clean run the CLI appends a human line after the JSON
            # ("No results with a severity of 'error' found!"). Trailing prose
            # after at least one decoded array is that, and is not an error.
            # Prose with NOTHING decoded is a crash and must stay fatal.
            if decoded:
                break
            return set(), f"could not parse the Spectral report for {where}: {exc}"
        decoded = True
        if isinstance(value, list):
            findings.extend(value)
    return {
        f["code"][len(PROBE_PREFIX):]
        for f in findings
        if isinstance(f.get("code"), str) and f["code"].startswith(PROBE_PREFIX)
    }, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ruleset", required=True)
    ap.add_argument("--allowlist", required=True)
    ap.add_argument("targets", nargs="+")
    args = ap.parse_args()

    if shutil.which("spectral") is None:
        sys.exit("spectral-rule-coverage: the `spectral` CLI is not on PATH")

    with open(args.ruleset) as fh:
        ruleset = yaml.safe_load(fh)
    givens = rule_givens(ruleset)
    if not givens:
        sys.exit(f"spectral-rule-coverage: {args.ruleset} declares no rules with a `given`")

    allow: dict[str, str] = {}
    if os.path.exists(args.allowlist):
        with open(args.allowlist) as fh:
            loaded = yaml.safe_load(fh) or {}
        allow = (loaded.get(os.path.basename(args.ruleset)) or {}) if isinstance(loaded, dict) else {}

    probe = build_probe(ruleset, givens)
    expected = set(probe["rules"].keys())
    expected = {k[len(PROBE_PREFIX):] for k in expected}

    targets = expand(args.targets)

    def probe_run(rules: dict) -> set[str]:
        payload = dict(probe, rules=rules)
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
            yaml.safe_dump(payload, fh, sort_keys=True)
            path = fh.name
        try:
            hits, err = run_probe(path, targets)
        finally:
            os.unlink(path)
        if err:
            print(f"::error::spectral-rule-coverage: {err}", file=sys.stderr)
            raise SystemExit(1)
        return hits

    matched = probe_run(probe["rules"])

    # Re-probe each apparent zero-match on its own. See the nimma note above:
    # a batched probe can be suppressed by an unrelated sibling, and believing
    # that would report a working rule as dead.
    suspect = sorted(expected - matched)
    if suspect:
        print(f"    re-probing {len(suspect)} apparent zero-match(es) in isolation...")
    for name in suspect:
        key = PROBE_PREFIX + name
        if probe_run({key: probe["rules"][key]}):
            matched.add(name)

    inert = sorted(expected - matched - set(allow))
    stale = sorted(k for k in allow if k in matched)
    covered = len(expected & matched)

    print(f"==> rule coverage: {args.ruleset}")
    print(f"    {covered}/{len(expected)} givens selected at least one node")
    print(f"    {len(allow)} declared as absent from the corpus")

    if inert:
        print(
            "\n::error::These `given` expressions selected NOTHING anywhere in the corpus.\n"
            "A rule that selects nothing enforces nothing, and reports clean while doing it.\n"
            "Either the JSONPath is wrong (see authoring #73), or the construct is genuinely\n"
            "absent from the corpus — in which case add the rule to the coverage allowlist\n"
            "WITH A REASON, or extend the corpus with a fixture that exercises it.\n",
            file=sys.stderr,
        )
        for name in inert:
            print(f"      {name}", file=sys.stderr)

    if stale:
        print(
            "\n::error::These rules are on the coverage allowlist but DO now select nodes.\n"
            "The allowlist is checked in both directions on purpose: entries that stop being\n"
            "true must be removed, or the list decays into a blanket exemption.\n",
            file=sys.stderr,
        )
        for name in stale:
            print(f"      {name}  (declared: {allow[name]})", file=sys.stderr)

    if inert or stale:
        return 1

    print("==> every rule's `given` is accounted for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
