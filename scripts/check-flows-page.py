#!/usr/bin/env python3
"""Fail when docs/flows.html drifts from the kit it describes.

The flows page ships into every project as .specfuse/authoring/docs/flows.html
and keeps its facts in one JSON block (#kit-data). This check compares that
block with the sources it summarises, so a kit change that would make the page
wrong fails CI instead of shipping a stale map:

  - skills and agents       against plugins/specfuse-authoring/{skills,agents}
  - the skill finder        covers every skill and names no unknown one
  - backlog states          against the State: line of the backlog template,
                            and the idea state machine against those states
  - no-orchestrator table   covers every skill
  - readiness checklist     against the idea dossier template
  - validation layers       against LAYERS in scripts/specfuse/validate-specs.sh
  - Spectral rule names     against the kit's rulesets
  - upgrade overlay         against scaffold.OVERLAY, and the simulator's quoted
                            output against the strings scaffold.py prints
  - relative links          resolve both in this repo and in an installed project

Usage: python3 scripts/check-flows-page.py   (exit 1 on drift)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "flows.html"
INSTALLED_PAGE = PurePosixPath(".specfuse/authoring/docs/flows.html")

sys.path.insert(0, str(ROOT))
from specfuse.authoring import scaffold  # noqa: E402

errors: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


def same_set(label: str, page: set[str], source: set[str]) -> None:
    if missing := source - page:
        errors.append(f"{label}: missing from the page: {sorted(missing)}")
    if extra := page - source:
        errors.append(f"{label}: on the page but not in the kit: {sorted(extra)}")


html = PAGE.read_text(encoding="utf-8")
m = re.search(r'<script type="application/json" id="kit-data">(.*?)</script>', html, re.S)
if not m:
    sys.exit("check-flows-page: no #kit-data block in docs/flows.html")
data = json.loads(m.group(1))

# Skills and agents.
plugin = ROOT / "plugins" / "specfuse-authoring"
skill_dirs = {p.parent.name for p in (plugin / "skills").glob("*/SKILL.md")}
agent_files = {p.stem for p in (plugin / "agents").glob("*.md")}
same_set("skills", set(data["skills"]), skill_dirs)
same_set("agents", set(data["agents"]), agent_files)

intent_skills = {s for g in data["intents"] for _, s in g["items"] if s}
same_set("skill finder", intent_skills, skill_dirs)
for lc in data["lifecycles"]:
    for st in lc["stages"]:
        for s in filter(None, [st.get("skill"), *st.get("also", [])]):
            check(s in skill_dirs, f"lifecycle {lc['id']!r} stage {st['t']!r} names unknown skill {s!r}")
        check(st["state"] in data["backlogStates"], f"lifecycle stage {st['t']!r} has unknown state {st['state']!r}")
for name, agent in data["agents"].items():
    for s in agent["by"]:
        check(s in skill_dirs, f"agent {name!r} is used by unknown skill {s!r}")

# State machine: the idea machine draws exactly the template's states, every
# transition names a real skill, and the no-orchestrator table covers every skill.
machine = data["machine"]
same_set("idea state machine", set(machine["backlog"]["states"]), set(data["backlogStates"]))
for key in ("backlog", "registry"):
    states = machine[key]["states"]
    for e in machine[key]["edges"]:
        check(e["from"] in states or e["from"] == "start", f"{key} edge {e['id']!r} starts at unknown state {e['from']!r}")
        check(e["to"] in states, f"{key} edge {e['id']!r} ends at unknown state {e['to']!r}")
        if e.get("by"):
            check(e["by"] in skill_dirs, f"{key} edge {e['id']!r} names unknown skill {e['by']!r}")
same_set("no-orchestrator table", {r[0] for r in data["standalone"]}, skill_dirs)
for name, status, _ in data["standalone"]:
    check(status in {"works", "degrades", "unavailable", "idle"}, f"no-orchestrator table: {name!r} has unknown status {status!r}")

# Backlog states: "State: `idea` → `shaping` → … (or `delivered` / `parked` / `dropped`)".
backlog = (ROOT / "templates" / "initiative-backlog.template.md").read_text(encoding="utf-8")
state_line = next((para.replace("\n", " ") for para in backlog.split("\n\n") if para.startswith("State: `")), "")
state_line = state_line.split(". ", 1)[0]
check(bool(state_line), "backlog template has no 'State: `…`' line")
source_states = re.findall(r"`([a-z]+)`", state_line)
check(data["backlogStates"] == source_states,
      f"backlog states {data['backlogStates']} != template {source_states}")
side = re.search(r"\(or (.*?)\)", state_line)
check(bool(side) and set(data["backlogSide"]) == set(re.findall(r"`([a-z]+)`", side.group(1))),
      "backlogSide does not match the template's '(or …)' states")

# Readiness checklist.
dossier = (ROOT / "templates" / "initiative-idea-dossier.template.md").read_text(encoding="utf-8")
section = dossier.split("## Readiness", 1)[1].split("\n## ", 1)[0] if "## Readiness" in dossier else ""
source_ready = re.findall(r"^- \[ \] (.+)$", section, re.M)
check(data["readiness"] == source_ready, f"readiness {data['readiness']} != dossier template {source_ready}")

# Validation layers, in order.
suite = (ROOT / "templates/project-init/scripts/specfuse/validate-specs.sh").read_text(encoding="utf-8")
block = re.search(r"LAYERS=\((.*?)\n\)", suite, re.S)
source_layers = re.findall(r'"([^"]+?)::\$SCRIPT_DIR/([\w.-]+)', block.group(1)) if block else []
page_layers = [(l["label"], l["script"]) for l in data["layers"]]
check(page_layers == source_layers, f"validation layers {page_layers} != validate-specs.sh {source_layers}")
for mk in data["mistakes"]:
    for i in mk["hit"] + mk.get("cascade", []):
        check(0 <= i < len(data["layers"]), f"mistake {mk['t']!r} points at layer {i}, which does not exist")

rulesets = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "schemas" / "spectral").glob("specfuse-*.yaml"))
for mk in data["mistakes"]:
    if rule := mk.get("rule"):
        check(re.search(rf"^  {re.escape(rule)}:$", rulesets, re.M) is not None,
              f"mistake {mk['t']!r} cites Spectral rule {rule!r}, which no kit ruleset defines")

# Upgrade overlay and the simulator's quoted output.
same_set("upgrade overlay", set(data["overlay"]), {dest for _, dest in scaffold.OVERLAY})
# Join implicitly concatenated literals ("…locally-"\n f"modified…") so quoted output matches.
scaffold_src = re.sub(r'"\s*\n\s*f?"', "", Path(scaffold.__file__).read_text(encoding="utf-8"))
for key, text in data["warnings"].items():
    check(text in scaffold_src, f"simulator quotes {text!r} ({key}), which scaffold.py no longer prints")

# Links: relative ones must resolve here and in an installed project.
hrefs = re.findall(r'link\(\[\s*"[^"]*",\s*"([^"]+)"', html)
hrefs += re.findall(r'href="([^"$]+)"', html)
hrefs += [h for p in data["planes"] for _, h in p["links"]]
hrefs += [n["link"][1] for n in data["tree"] if "link" in n]
installed = {PurePosixPath(rel) for rel, _ in scaffold.overlay_files()}
for href in sorted(set(hrefs)):
    if href.startswith(("http://", "https://", "#")):
        continue
    path = href.split("#", 1)[0]
    check((PAGE.parent / path).resolve().is_file(), f"link {href!r} does not resolve from docs/")
    parts: list[str] = []
    for part in (INSTALLED_PAGE.parent / path).parts:
        if part == "..":
            parts.pop()
        else:
            parts.append(part)
    check(PurePosixPath(*parts) in installed,
          f"link {href!r} would be broken in an installed project: the kit does not ship {PurePosixPath(*parts)}")

if errors:
    print("docs/flows.html has drifted from the kit:", file=sys.stderr)
    for e in errors:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(1)
print(f"docs/flows.html matches the kit ({len(skill_dirs)} skills, {len(agent_files)} agents, "
      f"{len(source_layers)} validation layers, {len(data['overlay'])} overlay entries).")
