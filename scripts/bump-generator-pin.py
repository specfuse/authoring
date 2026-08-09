#!/usr/bin/env python3
#
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
#
# bump-generator-pin.py — pin a newly-released generator jar in generator.lock.
#
# This is the KIT-SIDE half of a generator release. The generator's own release
# script publishes the jar to Specfuse/generator-dist and prints a version +
# SHA-256; this script writes that pin into the kit so `specfuse authoring generate`
# resolves and verifies the new jar.
#
# It updates ONLY the mechanical, deterministic part (generator.lock). Bumping
# the kit package version, adding the compatibility.md row, and publishing the
# kit patch are judgment steps the wrapping skill walks you through.
#
# Usage:
#   scripts/bump-generator-pin.py --version 1.4.0 --sha256 <64-hex>
#   scripts/bump-generator-pin.py --version 1.4.0 --sha256 <hex> --dry-run
#   scripts/bump-generator-pin.py --version 1.4.0 --sha256 <hex> --repo Specfuse/generator-dist

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pin a released generator jar in generator.lock.")
    p.add_argument("--version", required=True, help="Generator semver, e.g. 1.4.0")
    p.add_argument("--sha256", required=True, help="SHA-256 (64 lowercase hex) of the published jar")
    p.add_argument("--asset", help="Asset filename (default: specfuse-generator-<version>.jar)")
    p.add_argument("--tag", help="Release tag (default: v<version>)")
    p.add_argument("--repo", help="Override release_repo (default: keep existing)")
    p.add_argument("--lock", default="generator.lock", help="Path to generator.lock")
    p.add_argument("--dry-run", action="store_true", help="Print the result without writing")
    ns = p.parse_args(argv)

    version = ns.version.strip()
    sha = ns.sha256.strip().lower()
    if not SEMVER_RE.match(version):
        fail(f"--version '{version}' is not valid semver (X.Y.Z)")
    if not SHA256_RE.match(sha):
        fail("--sha256 must be 64 lowercase hex characters")

    asset = ns.asset or f"specfuse-generator-{version}.jar"
    tag = ns.tag or f"v{version}"
    if version not in asset:
        print(f"warning: asset '{asset}' does not contain version '{version}'", file=sys.stderr)
    if version not in tag:
        print(f"warning: tag '{tag}' does not contain version '{version}'", file=sys.stderr)

    lock_path = Path(ns.lock)
    if not lock_path.is_file():
        fail(f"{lock_path} not found (run from the kit repo root)")
    try:
        lock = json.loads(lock_path.read_text())
    except json.JSONDecodeError as e:
        fail(f"{lock_path} is not valid JSON: {e}")

    gen = lock.setdefault("generator", {})
    before = dict(gen)
    gen["version"] = version
    gen["asset"] = asset
    gen["sha256"] = sha
    gen["release_tag"] = tag
    if ns.repo:
        gen["release_repo"] = ns.repo
    gen.setdefault("release_repo", "Specfuse/generator-dist")

    rendered = json.dumps(lock, indent=2) + "\n"

    print("Pinning generator in", lock_path)
    for k in ("version", "asset", "sha256", "release_tag", "release_repo"):
        old = before.get(k, "—")
        new = gen.get(k, "—")
        mark = "  " if old == new else "* "
        print(f"  {mark}{k}: {old}  ->  {new}")

    if ns.dry_run:
        print("\n--dry-run: not written. Resulting generator.lock:\n")
        print(rendered)
        return 0

    lock_path.write_text(rendered)
    print(f"\nWrote {lock_path}.")
    print(
        "\nRemaining lockstep (NOT done by this script):\n"
        f"  1. Bump the kit package version (pyproject.toml, generator.lock kit_version, README).\n"
        f"  2. Add a compatibility.md row mapping kit <-> generator {version}.\n"
        "  3. Commit, then publish the matching kit patch to PyPi.\n"
        "Until the kit patch ships, clients still resolve the previously-pinned jar."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
