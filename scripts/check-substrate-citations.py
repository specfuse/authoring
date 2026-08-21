#!/usr/bin/env python3
#
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
#
# check-substrate-citations.py — the skills' substrate citations must resolve.
#
# WHY THIS EXISTS
#
# The specs agent's skills cite the shared methodology contract by path. Until
# authoring #55 those paths were unqualified — `shared/rules/never-touch.md` —
# and resolved only inside an orchestrator checkout, which is why the one
# working deployment depended on the orchestrator sitting BESIDE the specs repo
# on disk. `specfuse/specfuse#136` ships `methodology/` in the core wheel and
# provisions it into a repo, so those citations now point at
# `.specfuse/methodology/...` and resolve from the repo the agent is in.
#
# The failure mode of that repoint is silent. A citation naming a file core does
# not provision does not break a build — it breaks at runtime, inside a session,
# when an agent tries to read it. Nothing in CI reads these files, so nothing in
# CI notices. Same shape as the inert Spectral rules in #73: the signal for
# "wrong" and the signal for "fine" are both silence.
#
# So this checks against the real thing: CI installs the core `specfuse`
# package, runs `specfuse init` into a scratch directory, and points this script
# at the result. No hardcoded list of what core ships — the provisioner is the
# authority, and if core changes what it lays down, this notices.
#
# Note the dependency direction: core is a TEST-TIME dependency of the authoring
# kit, never a runtime one. Authoring depends on core; core depends on nothing
# here. That is the direction `decision-authoring-execution-boundary.md`
# follow-up #3 requires, and the reason the substrate had to ship from core
# rather than being vendored into this repo.
#
# Two directions, because both are ways to be wrong:
#
#   1. A `.specfuse/methodology/...` citation that does NOT resolve — the
#      repoint named something core does not provision.
#   2. A legacy `shared/...` citation that WOULD resolve under
#      `.specfuse/methodology/` — core has started shipping it and the citation
#      is now stale in the other direction. This is what will flag the moment
#      the remaining gaps close, so the repoint does not have to be remembered.
#
# Known blind spot, stated rather than papered over: direction 2 matches on
# path, so it cannot see a contract core ships under a DIFFERENT name. The live
# example is `shared/rules/state-vocabulary.md`, whose content is canonical in
# core's `methodology/glossary.md` §"Lifecycle states" — held back from
# provisioning because the loop scaffold ships a diverged `glossary.md`
# (`specfuse/specfuse#137`). When that lands, the repoint is manual.
#
# Usage:
#   specfuse init "$SCRATCH"
#   scripts/check-substrate-citations.py --provisioned "$SCRATCH"

from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path

# `.specfuse/methodology/schemas/events/x.schema.json`, `.specfuse/methodology/rules/y.md`
CITED = re.compile(r"\.specfuse/methodology/((?:rules|schemas)/[A-Za-z0-9/._-]+)")
# `shared/rules/y.md`, `/shared/schemas/x.json` — the pre-#55 form.
LEGACY = re.compile(r"(?<![\w./-])/?shared/((?:rules|schemas|templates)/[A-Za-z0-9/._-]+)")

SOURCES = "plugins/**/*.md"


def scan(pattern: re.Pattern) -> dict[str, list[str]]:
    """Map cited subpath -> ["file:line", ...]."""
    found: dict[str, list[str]] = {}
    for path in sorted(glob.glob(SOURCES, recursive=True)):
        for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
            for sub in pattern.findall(line):
                found.setdefault(sub, []).append(f"{path}:{lineno}")
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--provisioned",
        required=True,
        help="A directory `specfuse init` has been run in (the parent of .specfuse/).",
    )
    args = ap.parse_args()

    root = Path(args.provisioned) / ".specfuse" / "methodology"
    if not root.is_dir():
        print(
            f"::error::{root} does not exist. Run `specfuse init` in "
            f"{args.provisioned} before this check — an absent substrate would make "
            "every citation look broken and tell you nothing.",
            file=sys.stderr,
        )
        return 1

    cited = scan(CITED)
    legacy = scan(LEGACY)
    if not cited:
        print(
            "::error::No `.specfuse/methodology/...` citations found at all. Either the "
            "skills regressed to the pre-#55 unqualified paths, or this script's pattern "
            "has drifted from how they are written. Both are failures.",
            file=sys.stderr,
        )
        return 1

    # Direction 1: everything we point at must actually be there.
    unresolved = {s: w for s, w in cited.items() if not (root / s).is_file()}
    # Direction 2: anything still cited the old way that core now provisions.
    shippable = {s: w for s, w in legacy.items() if (root / s).is_file()}

    print("==> substrate citations")
    print(f"    {len(cited) - len(unresolved)}/{len(cited)} repointed citations resolve under {root}")
    print(f"    {len(legacy)} legacy `shared/...` citation(s) remain, {len(shippable)} now shippable")

    if unresolved:
        print(
            "\n::error::These citations name a file the core provisioner does not lay down.\n"
            "They will fail at runtime, inside a session, where CI cannot see them.\n"
            "Either core stopped shipping the file, or the path is a typo.\n",
            file=sys.stderr,
        )
        for sub, where in sorted(unresolved.items()):
            print(f"      .specfuse/methodology/{sub}", file=sys.stderr)
            for w in where:
                print(f"          {w}", file=sys.stderr)

    if shippable:
        print(
            "\n::error::These are still cited as `shared/...`, but core NOW provisions them.\n"
            "Repoint them to `.specfuse/methodology/...` — see authoring #55. The gap they\n"
            "were waiting on has closed.\n",
            file=sys.stderr,
        )
        for sub, where in sorted(shippable.items()):
            print(f"      shared/{sub}  ->  .specfuse/methodology/{sub}", file=sys.stderr)
            for w in where:
                print(f"          {w}", file=sys.stderr)

    if unresolved or shippable:
        return 1

    print("==> every substrate citation is accounted for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
