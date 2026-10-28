#!/usr/bin/env python3
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
"""Every relative link in a doc the kit ships into projects must resolve there.

The overlay (`scaffold.OVERLAY`) copies a handful of files from docs/ into
`.specfuse/authoring/docs/` of every project. A relative link in one of them
that works in this repo (`../compatibility.md`) is broken in a project, where
only the overlay exists. This check reads every Markdown and HTML file the
overlay ships from docs/, and asserts each relative link resolves twice: here,
and against the set of files an installed project receives. Links to the rest
of the kit repo belong on GitHub as absolute URLs.

docs/flows.html has its own, richer check (check-flows-page.py); its links are
covered here too, which is harmless.

Usage: python3 scripts/check-shipped-docs.py   (exit 1 on a broken link)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from specfuse.authoring import scaffold  # noqa: E402

LINK = re.compile(r'(?:\]\(|href=")([^)"\s]+)')

installed = {PurePosixPath(rel) for rel, _ in scaffold.overlay_files()}
shipped = [(src, dest) for src, dest in scaffold.OVERLAY
           if src.startswith("docs/") and src.endswith((".md", ".html"))]

errors: list[str] = []
checked = 0
for src, dest in shipped:
    text = (ROOT / src).read_text(encoding="utf-8")
    for href in sorted(set(LINK.findall(text))):
        if re.match(r"(https?:|mailto:|#|\$\{)", href):
            continue
        path = href.split("#", 1)[0]
        if not path:
            continue
        checked += 1
        if not (ROOT / src).parent.joinpath(path).resolve().exists():
            errors.append(f"{src}: {href!r} does not resolve in the kit repo")
            continue
        parts: list[str] = []
        for part in (PurePosixPath(dest).parent / path).parts:
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        target = PurePosixPath(*parts)
        if not any(target == f or target in f.parents for f in installed):
            errors.append(f"{src}: {href!r} would be broken in an installed project "
                          f"(the kit does not ship {target}); link it on GitHub instead")

if errors:
    print("check-shipped-docs: links that break once the overlay is installed:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
print(f"check-shipped-docs: OK ({len(shipped)} shipped docs, {checked} relative links)")
