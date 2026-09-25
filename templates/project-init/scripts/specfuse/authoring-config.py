#!/usr/bin/env python3
"""Read one value out of `.specfuse/authoring/config.yml`.

The authoring plane's per-install settings: where the orchestration repo is,
and which GitHub repo carries backlog ideas. Skills shell out to this rather
than each parsing the file, so the precedence and — more importantly — the
*reporting* of an absent value are written once.

    authoring-config.py repos.orchestrator
    authoring-config.py github.ideas.repo --required
    authoring-config.py github.ideas.label

Exit codes:
    0  value resolved; printed on stdout
    1  the key is unset and `--required` was given, or the file is malformed
    2  the key is not one this file defines (a typo, not a missing value)

WHY AN UNKNOWN KEY IS AN ERROR

The generator project file silently drops unknown fields, which is precisely
why a setting could not live there: a typo'd key disables a feature with no
signal. That is the same defect as the project file's `encryption` block being
absent — no compliance floors apply, silently, and a project with no floors
reads exactly like one whose floors all pass. Every path through this script
distinguishes "unset, here is the default" from "unset, the feature is off"
from "that key does not exist", because a caller cannot act on them the same
way and a human cannot debug them the same way.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment problem, not a config one
    sys.stderr.write("PyYAML is required to read .specfuse/authoring/config.yml\n")
    raise SystemExit(1)

CONFIG_PATH = Path(".specfuse/authoring/config.yml")

# The closed set. A key absent from here is a typo, and saying so beats
# returning an empty string that the caller reads as "not configured".
#
# default: what an unset key resolves to.
# feature: when a key has no default, the capability it gates — named in the
#          message so an operator learns what turning it on would enable.
KNOWN: dict[str, dict[str, object]] = {
    "repos.orchestrator": {
        "default": "../orchestrator",
        "note": "a convention, not a layout requirement",
    },
    "github.ideas.repo": {
        "default": None,
        "feature": "idea intake from GitHub issues, and publishing ideas to them",
    },
    "github.ideas.label": {"default": "specfuse:idea"},
    "github.ideas.project": {
        "default": None,
        "feature": "adding published ideas to a GitHub Project",
    },
}


def load() -> dict:
    if not CONFIG_PATH.exists():
        # Not an error. A project scaffolded before this file existed, or one
        # that deleted it, gets defaults — and every caller is told which.
        return {}
    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sys.stderr.write(f"{CONFIG_PATH} is not valid YAML: {exc}\n")
        raise SystemExit(1)
    if data is None:
        return {}
    if not isinstance(data, dict):
        sys.stderr.write(f"{CONFIG_PATH} must be a mapping at the top level.\n")
        raise SystemExit(1)
    return data


def dig(data: dict, key: str):
    node = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("key", help="dotted key, e.g. repos.orchestrator")
    ap.add_argument(
        "--required",
        action="store_true",
        help="exit 1 when the key has no configured value and no default",
    )
    args = ap.parse_args()

    spec = KNOWN.get(args.key)
    if spec is None:
        sys.stderr.write(
            f"'{args.key}' is not a key {CONFIG_PATH} defines. Known keys:\n  "
            + "\n  ".join(sorted(KNOWN))
            + "\n"
        )
        return 2

    value = dig(load(), args.key)
    if value is not None:
        print(value)
        return 0

    default = spec.get("default")
    if default is not None:
        note = spec.get("note")
        sys.stderr.write(
            f"{args.key} is unset; using the default {default!r}"
            + (f" ({note})" if note else "")
            + f". Set it in {CONFIG_PATH} to change it.\n"
        )
        print(default)
        return 0

    feature = spec.get("feature", "this capability")
    sys.stderr.write(
        f"{args.key} is unset, so {feature} is off. "
        f"Set it in {CONFIG_PATH} to enable it.\n"
    )
    return 1 if args.required else 0


if __name__ == "__main__":
    raise SystemExit(main())
