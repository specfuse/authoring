#!/usr/bin/env python3
#
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
#
"""Fail when docs/csharp-component.html drifts from what it describes.

The C# component map keeps its facts in one JSON block (#guide-data). The
Markdown guide and the starter contract are the sources of truth, so this
check compares the block with them and fails CI instead of shipping a page
that lists a check the guide no longer has, or a rule the contract no longer
ships:

  - checklist IDs        the page's checks == the `**CS-nn ·` checks in
                         docs/csharp-component-guide.md, same order
  - contract rule IDs    the page's rules == the `id:` entries of
                         templates/component-contract/csharp/gen-contract.yml,
                         and the guide's §6 table names every block
  - guide anchors        every `#anchor` the page links into the guide is a
                         heading the guide has (GitHub slug rules)
  - relative links       every relative href on the page resolves from docs/
  - views                the nav data and the renderers agree
  - seams and patterns   every `check` they cite is a checklist ID

Usage: python3 scripts/check-csharp-page.py   (exit 1 on drift)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "csharp-component.html"
GUIDE = ROOT / "docs" / "csharp-component-guide.md"
CONTRACT = ROOT / "templates" / "component-contract" / "csharp" / "gen-contract.yml"

errors: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


def slug(heading: str) -> str:
    """GitHub's heading-to-anchor rule: lowercase, drop punctuation, spaces to dashes."""
    text = re.sub(r"`([^`]*)`", r"\1", heading).strip()
    text = text.lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


html = PAGE.read_text(encoding="utf-8")
m = re.search(r'<script type="application/json" id="guide-data">(.*?)</script>', html, re.S)
if not m:
    sys.exit("check-csharp-page: no #guide-data block in docs/csharp-component.html")
data = json.loads(m.group(1))

guide = GUIDE.read_text(encoding="utf-8")
contract = CONTRACT.read_text(encoding="utf-8")

# Checklist IDs, in order.
guide_checks = re.findall(r"^\*\*(CS-\d{2}) ·", guide, re.M)
page_checks = [c["id"] for c in data["checks"]]
check(guide_checks == page_checks,
      f"checklist: page has {page_checks}, guide has {guide_checks}")
check(len(set(page_checks)) == len(page_checks), "checklist: duplicate IDs on the page")

# Contract rule IDs.
contract_rules = re.findall(r"^\s*- id: (GEN-\d{3})", contract, re.M)
page_rules = [r["id"] for r in data["rules"]]
check(contract_rules == page_rules,
      f"rules: page has {page_rules}, contract has {contract_rules}")
ranges = [(int(a), int(b)) for a, b in re.findall(r"`GEN-(\d{3})` to `GEN-(\d{3})`", guide)]
for rid in contract_rules:
    n = int(rid[4:])
    named = f"`{rid}`" in guide or any(a <= n <= b for a, b in ranges)
    check(named, f"rules: {rid} is in the contract but the guide never names it (singly or in a range)")

# Guide anchors the page links into.
headings = re.findall(r"^#{1,6} (.+)$", guide, re.M)
anchors = {slug(h) for h in headings}
anchor_refs = {c["guide"] for c in data["checks"]} | {t["guide"] for t in data["tree"]}
anchor_refs |= set(re.findall(r'guideLink\("(#[^"]+)"', html))
for a in sorted(anchor_refs):
    check(a.lstrip("#") in anchors, f"anchor: the page links {a} but the guide has no such heading")

# Relative links resolve from docs/.
for href in set(re.findall(r'href="([^"#][^"]*)"', html)):
    if re.match(r"https?:", href) or "${" in href:   # a JS template, not a link
        continue
    target = (PAGE.parent / href.split("#")[0]).resolve()
    check(target.exists(), f"link: {href} does not resolve from docs/")

# Views: nav data and the render table agree.
view_ids = [v["id"] for v in data["views"]]
rendered = re.findall(r"const v = \{ (.*?) \}\[ui\.view\]", html)
check(bool(rendered), "views: cannot find the render table")
if rendered:
    keys = re.findall(r"(\w+): view", rendered[0])
    check(set(keys) == set(view_ids), f"views: nav has {view_ids}, renderers have {keys}")

# Seams and patterns cite real checks.
for s in data["seams"]:
    check(s["check"] in page_checks, f"seam {s['id']}: cites unknown check {s['check']}")
for p in data["patterns"]:
    check(p["check"] in page_checks, f"pattern {p['id']}: cites unknown check {p['check']}")

# The prompt on the page is the prompt in the guide.
prompt_in_guide = re.search(r"```\n(Read \S*csharp-component-guide\.md.*?)```", guide, re.S)
check(prompt_in_guide is not None and prompt_in_guide.group(1).strip() == data["prompt"].strip(),
      "prompt: the page's Claude prompt differs from the guide's")

if errors:
    print("check-csharp-page: drift between docs/csharp-component.html and its sources:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"check-csharp-page: OK ({len(page_checks)} checks, {len(page_rules)} rules, {len(anchor_refs)} anchors)")
