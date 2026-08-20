#!/bin/bash
# Arazzo Structure & Cross-Spec Validator
# Usage: ./scripts/specfuse/validate-arazzo.sh
#
# Validates that Arazzo scenario and recipe files follow the required
# directory structure, naming conventions, and cross-spec consistency rules.
#
# Checks implemented (14 total, groups A-F):
#   A1-A5: File organization (location, naming, x-domain)
#   B6-B7: Cross-spec operationId + sourceDescriptions resolution
#   C8:    Cross-spec event name resolution
#   D9-D12: Recipe reference resolution (x-setup, extends, depth, cycles)
#   E13:   Step overlap detection (Jaccard similarity)
#   F14:   x-mcp.toolName global uniqueness

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export SPEC_DIR="$PROJECT_ROOT/api/specs/v1"

echo "=== Arazzo Structure & Cross-Spec Validator ==="
echo "Spec Directory: $SPEC_DIR"
echo ""

# Discover all Arazzo and recipe files
SCENARIO_FILES=()
while IFS= read -r f; do
    SCENARIO_FILES+=("$f")
done < <(find "$SPEC_DIR" -name "*.arazzo.yaml" -type f 2>/dev/null | sort)

RECIPE_FILES=()
while IFS= read -r f; do
    RECIPE_FILES+=("$f")
done < <(find "$SPEC_DIR" -name "*.recipe.yaml" -type f 2>/dev/null | sort)

ALL_FILES=(${SCENARIO_FILES[@]+"${SCENARIO_FILES[@]}"} ${RECIPE_FILES[@]+"${RECIPE_FILES[@]}"})

echo "Scenarios found: ${#SCENARIO_FILES[@]}"
echo "Recipes found:   ${#RECIPE_FILES[@]}"
echo ""

if [ ${#ALL_FILES[@]} -eq 0 ]; then
    echo "No Arazzo or recipe files found. Nothing to validate."
    exit 0
fi

# Run all 14 checks via a single python3 invocation for structured YAML parsing.
# Output format: CHECK_ID|STATUS|MESSAGE (one line per check result)
# STATUS: PASS, FAIL, WARN
# Additional detail lines prefixed with DETAIL|

RESULTS=$(python3 << 'PYEOF'
import yaml
import os
import sys
import re
from collections import defaultdict

SPEC_DIR = os.environ.get("SPEC_DIR", "")
if not SPEC_DIR:
    print("ERROR|SPEC_DIR not set", file=sys.stderr)
    sys.exit(1)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_yaml(path):
    """Load a YAML file, returning None on failure."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception:
        return None

def rel(path):
    """Return path relative to SPEC_DIR for display."""
    return os.path.relpath(path, SPEC_DIR)

def emit(check_id, status, message):
    """Print a check result line."""
    print(f"{check_id}|{status}|{message}")

def detail(message):
    """Print a detail line for the most recent check."""
    print(f"DETAIL|{message}")

# ─── Discovery ───────────────────────────────────────────────────────────────

scenario_files = []
recipe_files = []
for root, dirs, files in os.walk(SPEC_DIR):
    for fname in sorted(files):
        fpath = os.path.join(root, fname)
        if fname.endswith(".arazzo.yaml"):
            scenario_files.append(fpath)
        elif fname.endswith(".recipe.yaml"):
            recipe_files.append(fpath)

all_files = scenario_files + recipe_files

# Valid domain directories
valid_domains = set()
domains_dir = os.path.join(SPEC_DIR, "domains")
if os.path.isdir(domains_dir):
    for d in os.listdir(domains_dir):
        if os.path.isdir(os.path.join(domains_dir, d)):
            valid_domains.add(d)

# ─── Pre-parse all files ────────────────────────────────────────────────────

parsed = {}  # path -> parsed YAML
for fpath in all_files:
    doc = load_yaml(fpath)
    if doc is not None:
        parsed[fpath] = doc
    else:
        detail(f"WARNING: could not parse {rel(fpath)}")

# ═══════════════════════════════════════════════════════════════════════════════
# GROUP A — File Organization
# ═══════════════════════════════════════════════════════════════════════════════

# A1: Scenario files must be in domains/{domain}/scenarios/ or scenarios/cross-domain/
a1_errors = []
for fpath in scenario_files:
    relpath = os.path.relpath(fpath, SPEC_DIR)
    parts = relpath.split(os.sep)
    # Valid: domains/{domain}/scenarios/{file}
    # Valid: scenarios/cross-domain/{file}
    if len(parts) == 4 and parts[0] == "domains" and parts[2] == "scenarios":
        continue
    elif len(parts) == 3 and parts[0] == "scenarios" and parts[1] == "cross-domain":
        continue
    else:
        a1_errors.append(rel(fpath))

if not a1_errors:
    emit("A1", "PASS", "Scenario files in correct directories")
else:
    emit("A1", "FAIL", f"{len(a1_errors)} scenario file(s) in wrong location")
    for e in a1_errors:
        detail(f"  {e} -- must be under domains/{{domain}}/scenarios/ or scenarios/cross-domain/")

# A2: Recipe files must be in setup-recipes/foundational/ or setup-recipes/domain-specific/{domain}/
a2_errors = []
for fpath in recipe_files:
    relpath = os.path.relpath(fpath, SPEC_DIR)
    parts = relpath.split(os.sep)
    # Valid: scenarios/setup-recipes/foundational/{file}
    if (len(parts) == 4 and parts[0] == "scenarios"
            and parts[1] == "setup-recipes" and parts[2] == "foundational"):
        continue
    # Valid: scenarios/setup-recipes/domain-specific/{domain}/{file}
    elif (len(parts) == 5 and parts[0] == "scenarios"
            and parts[1] == "setup-recipes" and parts[2] == "domain-specific"):
        continue
    else:
        a2_errors.append(rel(fpath))

if not a2_errors:
    emit("A2", "PASS", "Recipe files in correct directories")
else:
    emit("A2", "FAIL", f"{len(a2_errors)} recipe file(s) in wrong location")
    for e in a2_errors:
        detail(f"  {e} -- must be under scenarios/setup-recipes/foundational/ or scenarios/setup-recipes/domain-specific/{{domain}}/")

# A3: Scenario file names are kebab-case + .arazzo.yaml
KEBAB_ARAZZO = re.compile(r"^[a-z][a-z0-9]+(-[a-z0-9]+)*\.arazzo\.yaml$")
a3_errors = []
for fpath in scenario_files:
    fname = os.path.basename(fpath)
    if not KEBAB_ARAZZO.match(fname):
        a3_errors.append(fname)

if not a3_errors:
    emit("A3", "PASS", "Scenario file names are kebab-case")
else:
    emit("A3", "FAIL", f"{len(a3_errors)} scenario file(s) with invalid name")
    for e in a3_errors:
        detail(f"  {e} -- must match {{kebab-case}}.arazzo.yaml")

# A4: Recipe file names are kebab-case + .recipe.yaml
KEBAB_RECIPE = re.compile(r"^[a-z][a-z0-9]+(-[a-z0-9]+)*\.recipe\.yaml$")
a4_errors = []
for fpath in recipe_files:
    fname = os.path.basename(fpath)
    if not KEBAB_RECIPE.match(fname):
        a4_errors.append(fname)

if not a4_errors:
    emit("A4", "PASS", "Recipe file names are kebab-case")
else:
    emit("A4", "FAIL", f"{len(a4_errors)} recipe file(s) with invalid name")
    for e in a4_errors:
        detail(f"  {e} -- must match {{kebab-case}}.recipe.yaml")

# A5: x-domain value matches existing domain directory (or is cross-domain)
VALID_DOMAINS_WITH_CROSS = valid_domains | {"cross-domain"}
a5_errors = []
for fpath in all_files:
    doc = parsed.get(fpath)
    if not doc:
        continue
    domain = doc.get("x-domain")
    if not domain:
        continue  # Spectral checks for required x-domain
    if domain not in VALID_DOMAINS_WITH_CROSS:
        a5_errors.append(f"{rel(fpath)}: x-domain '{domain}' does not match any domain directory")
    # cross-domain must only be used under scenarios/cross-domain/
    if domain == "cross-domain":
        relpath = os.path.relpath(fpath, SPEC_DIR)
        if not relpath.startswith(os.path.join("scenarios", "cross-domain")):
            a5_errors.append(f"{rel(fpath)}: x-domain 'cross-domain' only valid under scenarios/cross-domain/")

if not a5_errors:
    emit("A5", "PASS", "x-domain values match existing domain directories")
else:
    emit("A5", "FAIL", f"{len(a5_errors)} x-domain issue(s)")
    for e in a5_errors:
        detail(f"  {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# GROUP B — Cross-spec: operationId resolution
# ═══════════════════════════════════════════════════════════════════════════════

# Collect all operationIds from OpenAPI operation files
# Each operation file starts with an HTTP method key containing operationId.
all_operation_ids = set()
for root, dirs, files in os.walk(os.path.join(SPEC_DIR, "domains")):
    # Only look in operations/ directories
    if os.path.basename(root) != "operations":
        continue
    for fname in files:
        if fname.endswith(".yaml"):
            op_path = os.path.join(root, fname)
            op_doc = load_yaml(op_path)
            if op_doc and isinstance(op_doc, dict):
                for method_key in ("get", "post", "put", "patch", "delete", "head", "options"):
                    method = op_doc.get(method_key)
                    if method and isinstance(method, dict) and "operationId" in method:
                        all_operation_ids.add(method["operationId"])

# B6: Every operationId referenced in steps must exist in OpenAPI
def extract_operation_ids_from_doc(doc):
    """Extract all operationId values from workflows.steps and x-async.poll."""
    ids = []
    workflows = doc.get("workflows", [])
    if not isinstance(workflows, list):
        return ids
    for wf in workflows:
        if not isinstance(wf, dict):
            continue
        steps = wf.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            # Direct operationId on step
            op_id = step.get("operationId")
            if op_id:
                ids.append(op_id)
            # operationId inside x-async.poll
            x_async = step.get("x-async")
            if isinstance(x_async, dict):
                poll = x_async.get("poll")
                if isinstance(poll, dict):
                    poll_op = poll.get("operationId")
                    if poll_op:
                        ids.append(poll_op)
    return ids

b6_errors = []
for fpath in all_files:
    doc = parsed.get(fpath)
    if not doc:
        continue
    op_ids = extract_operation_ids_from_doc(doc)
    for op_id in op_ids:
        if op_id not in all_operation_ids:
            b6_errors.append(f"{rel(fpath)}: operationId '{op_id}' not found in OpenAPI specs")

if not b6_errors:
    emit("B6", "PASS", f"All step operationIds exist in OpenAPI ({len(all_operation_ids)} known)")
else:
    emit("B6", "FAIL", f"{len(b6_errors)} unresolved operationId reference(s)")
    for e in b6_errors:
        detail(f"  {e}")

# B7: Every sourceDescriptions[*].url resolves to an existing file
b7_errors = []
for fpath in all_files:
    doc = parsed.get(fpath)
    if not doc:
        continue
    sources = doc.get("sourceDescriptions", [])
    if not isinstance(sources, list):
        continue
    file_dir = os.path.dirname(fpath)
    for src in sources:
        if not isinstance(src, dict):
            continue
        url = src.get("url", "")
        if not url:
            continue
        # Resolve relative to the file's directory
        resolved = os.path.normpath(os.path.join(file_dir, url))
        if not os.path.isfile(resolved):
            b7_errors.append(f"{rel(fpath)}: sourceDescriptions URL '{url}' does not resolve (expected {os.path.relpath(resolved, SPEC_DIR)})")

if not b7_errors:
    emit("B7", "PASS", "All sourceDescriptions URLs resolve to existing files")
else:
    emit("B7", "FAIL", f"{len(b7_errors)} unresolved sourceDescriptions URL(s)")
    for e in b7_errors:
        detail(f"  {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# GROUP C — Cross-spec: event name resolution
# ═══════════════════════════════════════════════════════════════════════════════

# Collect all {Entity}.{Action} pairs from AsyncAPI messages (x-label)
async_event_names = set()
for root, dirs, files in os.walk(os.path.join(SPEC_DIR, "domains")):
    if os.path.basename(root) != "messages":
        continue
    for fname in files:
        if fname.endswith(".yaml"):
            msg_path = os.path.join(root, fname)
            msg_doc = load_yaml(msg_path)
            if msg_doc and isinstance(msg_doc, dict):
                x_label = msg_doc.get("x-label")
                if isinstance(x_label, dict):
                    entity = x_label.get("entity", "")
                    action = x_label.get("action", "")
                    if entity and action:
                        async_event_names.add(f"{entity}.{action}")

# Also collect event names from OpenAPI x-emits declarations (secondary source).
# An event referenced in Arazzo may have an OpenAPI x-emits declaration even if
# the AsyncAPI message definition has not been created yet. We collect these as
# a fallback to avoid false positives for legitimate events.
openapi_emits = set()
for root, dirs, files in os.walk(os.path.join(SPEC_DIR, "domains")):
    if os.path.basename(root) != "operations":
        continue
    for fname in files:
        if fname.endswith(".yaml"):
            op_path = os.path.join(root, fname)
            op_doc = load_yaml(op_path)
            if op_doc and isinstance(op_doc, dict):
                for method_key in ("get", "post", "put", "patch", "delete"):
                    method = op_doc.get(method_key)
                    if method and isinstance(method, dict):
                        x_emits = method.get("x-emits", [])
                        if isinstance(x_emits, list):
                            for entry in x_emits:
                                if isinstance(entry, dict):
                                    evt = entry.get("event", "")
                                    if evt:
                                        openapi_emits.add(evt)

known_events = async_event_names | openapi_emits

# C8: Every event name in x-async.emit/await must match a known event
def extract_event_names_from_doc(doc):
    """Extract all event names from x-async.emit and x-async.await in all workflows."""
    events = []
    workflows = doc.get("workflows", [])
    if not isinstance(workflows, list):
        return events
    for wf in workflows:
        if not isinstance(wf, dict):
            continue
        steps = wf.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            x_async = step.get("x-async")
            if not isinstance(x_async, dict):
                continue
            # emit array
            emit_list = x_async.get("emit", [])
            if isinstance(emit_list, list):
                for entry in emit_list:
                    if isinstance(entry, dict):
                        evt = entry.get("event", "")
                        if evt:
                            events.append(evt)
            # await object
            await_obj = x_async.get("await")
            if isinstance(await_obj, dict):
                evt = await_obj.get("event", "")
                if evt:
                    events.append(evt)
    return events

c8_errors = []
c8_warnings = []
for fpath in all_files:
    doc = parsed.get(fpath)
    if not doc:
        continue
    event_names = extract_event_names_from_doc(doc)
    for evt in event_names:
        if evt in async_event_names:
            continue  # Found in AsyncAPI messages -- best case
        elif evt in openapi_emits:
            # Found in OpenAPI x-emits but missing AsyncAPI message definition.
            # This is valid but the AsyncAPI message should be created.
            c8_warnings.append(f"{rel(fpath)}: event '{evt}' found in OpenAPI x-emits but has no AsyncAPI message definition")
        else:
            c8_errors.append(f"{rel(fpath)}: event '{evt}' not found in AsyncAPI messages or OpenAPI x-emits")

if not c8_errors and not c8_warnings:
    emit("C8", "PASS", f"All x-async event names match known events ({len(async_event_names)} async + {len(openapi_emits - async_event_names)} OpenAPI-only)")
elif not c8_errors and c8_warnings:
    emit("C8", "PASS", f"All event names resolved ({len(c8_warnings)} found in OpenAPI x-emits only, missing AsyncAPI message)")
    for w in c8_warnings:
        detail(f"  NOTE: {w}")
else:
    emit("C8", "FAIL", f"{len(c8_errors)} unresolved event name(s)")
    for e in c8_errors:
        detail(f"  {e}")
    for w in c8_warnings:
        detail(f"  NOTE: {w}")

# ═══════════════════════════════════════════════════════════════════════════════
# GROUP D — Recipe reference resolution
# ═══════════════════════════════════════════════════════════════════════════════

# Build recipe stem -> filepath map
recipe_stem_map = {}
for fpath in recipe_files:
    stem = os.path.basename(fpath).replace(".recipe.yaml", "")
    recipe_stem_map[stem] = fpath

# D9: Every x-setup.recipe references an existing recipe file
d9_errors = []
for fpath in scenario_files:
    doc = parsed.get(fpath)
    if not doc:
        continue
    x_setup = doc.get("x-setup")
    if not isinstance(x_setup, dict):
        continue
    recipe_name = x_setup.get("recipe", "")
    if recipe_name and recipe_name not in recipe_stem_map:
        d9_errors.append(f"{rel(fpath)}: x-setup.recipe '{recipe_name}' does not match any recipe file")

if not d9_errors:
    emit("D9", "PASS", "All x-setup.recipe references resolve")
else:
    emit("D9", "FAIL", f"{len(d9_errors)} unresolved x-setup.recipe reference(s)")
    for e in d9_errors:
        detail(f"  {e}")

# D10: Every x-recipe.extends[] references an existing recipe file
d10_errors = []
for fpath in recipe_files:
    doc = parsed.get(fpath)
    if not doc:
        continue
    x_recipe = doc.get("x-recipe")
    if not isinstance(x_recipe, dict):
        continue
    extends = x_recipe.get("extends", [])
    if not isinstance(extends, list):
        continue
    for parent_name in extends:
        if parent_name not in recipe_stem_map:
            d10_errors.append(f"{rel(fpath)}: x-recipe.extends '{parent_name}' does not match any recipe file")

if not d10_errors:
    emit("D10", "PASS", "All x-recipe.extends references resolve")
else:
    emit("D10", "FAIL", f"{len(d10_errors)} unresolved x-recipe.extends reference(s)")
    for e in d10_errors:
        detail(f"  {e}")

# D11 + D12: Extends chain depth <= 6 and acyclic
def get_extends_chain(stem, depth=0, visited=None):
    """Walk the extends chain for a recipe stem. Returns (depth, cycle_detected, chain)."""
    if visited is None:
        visited = []
    if stem in visited:
        return depth, True, visited + [stem]
    visited = visited + [stem]
    fpath = recipe_stem_map.get(stem)
    if not fpath:
        return depth, False, visited
    doc = parsed.get(fpath)
    if not doc:
        return depth, False, visited
    x_recipe = doc.get("x-recipe")
    if not isinstance(x_recipe, dict):
        return depth, False, visited
    extends = x_recipe.get("extends", [])
    if not isinstance(extends, list) or not extends:
        return depth, False, visited
    # Walk up the chain (extends is an ordered chain, not multiple parents)
    max_depth = depth
    for parent in extends:
        d, cycle, chain = get_extends_chain(parent, depth + 1, visited)
        if cycle:
            return d, True, chain
        max_depth = max(max_depth, d)
        visited = chain  # Continue with the full chain
    return max_depth, False, visited

d11_errors = []
d12_errors = []
checked_stems = set()
for fpath in recipe_files:
    stem = os.path.basename(fpath).replace(".recipe.yaml", "")
    if stem in checked_stems:
        continue
    checked_stems.add(stem)
    depth, has_cycle, chain = get_extends_chain(stem)
    if has_cycle:
        cycle_str = " -> ".join(chain)
        d12_errors.append(f"Cycle detected: {cycle_str}")
    elif depth > 6:
        d11_errors.append(f"Recipe '{stem}' has extends chain depth {depth} (max 6)")

if not d11_errors:
    emit("D11", "PASS", "Recipe extends chain depth <= 6")
else:
    emit("D11", "FAIL", f"{len(d11_errors)} recipe(s) exceed max extends depth")
    for e in d11_errors:
        detail(f"  {e}")

if not d12_errors:
    emit("D12", "PASS", "Recipe extends chains are acyclic")
else:
    emit("D12", "FAIL", f"{len(d12_errors)} cycle(s) detected in extends chains")
    for e in d12_errors:
        detail(f"  {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# GROUP E — Cross-file granularity
# ═══════════════════════════════════════════════════════════════════════════════

# E13: Step overlap detection (Jaccard similarity on ordered operationId sequences)
# Compare workflows across different scenario files in the same domain.

def extract_workflow_opid_sequences(doc):
    """Extract operationId sequences per workflow from a document."""
    sequences = {}
    workflows = doc.get("workflows", [])
    if not isinstance(workflows, list):
        return sequences
    for wf in workflows:
        if not isinstance(wf, dict):
            continue
        wf_id = wf.get("workflowId", "unknown")
        op_ids = []
        steps = wf.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            op_id = step.get("operationId")
            if op_id:
                op_ids.append(op_id)
            # Also capture x-async.poll operationId
            x_async = step.get("x-async")
            if isinstance(x_async, dict):
                poll = x_async.get("poll")
                if isinstance(poll, dict) and "operationId" in poll:
                    op_ids.append(poll["operationId"])
        if op_ids:
            sequences[wf_id] = op_ids
    return sequences

def jaccard_similarity(list_a, list_b):
    """Jaccard similarity on multisets of operationIds."""
    if not list_a and not list_b:
        return 0.0
    set_a = set(list_a)
    set_b = set(list_b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return intersection / union

# Group scenario files by domain
domain_scenarios = defaultdict(list)
for fpath in scenario_files:
    doc = parsed.get(fpath)
    if not doc:
        continue
    domain = doc.get("x-domain", "unknown")
    domain_scenarios[domain].append((fpath, doc))

e13_errors = []
e13_warnings = []
for domain, file_docs in domain_scenarios.items():
    if len(file_docs) < 2:
        continue
    # Collect all workflows with their file provenance
    all_workflows = []
    for fpath, doc in file_docs:
        sequences = extract_workflow_opid_sequences(doc)
        for wf_id, op_ids in sequences.items():
            all_workflows.append((fpath, wf_id, op_ids))
    # Compare workflows from different files
    for i in range(len(all_workflows)):
        for j in range(i + 1, len(all_workflows)):
            f_i, wf_i, ops_i = all_workflows[i]
            f_j, wf_j, ops_j = all_workflows[j]
            if f_i == f_j:
                continue  # Only compare across different files
            sim = jaccard_similarity(ops_i, ops_j)
            if sim >= 0.80:
                e13_errors.append(
                    f"domain '{domain}': {rel(f_i)}:{wf_i} vs {rel(f_j)}:{wf_j} "
                    f"-- {sim:.0%} overlap (>= 80% threshold)"
                )
            elif sim >= 0.60:
                e13_warnings.append(
                    f"domain '{domain}': {rel(f_i)}:{wf_i} vs {rel(f_j)}:{wf_j} "
                    f"-- {sim:.0%} overlap (60-80% review zone)"
                )

if not e13_errors and not e13_warnings:
    emit("E13", "PASS", "No scenario step-overlap >= 80% within same domain")
elif not e13_errors and e13_warnings:
    emit("E13", "PASS", f"No >= 80% overlap ({len(e13_warnings)} pair(s) in 60-80% review zone)")
    for w in e13_warnings:
        detail(f"  REVIEW: {w}")
else:
    emit("E13", "FAIL", f"{len(e13_errors)} scenario pair(s) with >= 80% step overlap")
    for e in e13_errors:
        detail(f"  {e}")
    for w in e13_warnings:
        detail(f"  REVIEW: {w}")

# ═══════════════════════════════════════════════════════════════════════════════
# GROUP F — Global uniqueness
# ═══════════════════════════════════════════════════════════════════════════════

# F14: x-mcp.toolName must be globally unique across all scenario files
tool_names = defaultdict(list)
for fpath in scenario_files:
    doc = parsed.get(fpath)
    if not doc:
        continue
    # Check root-level x-mcp
    x_mcp = doc.get("x-mcp")
    if isinstance(x_mcp, dict):
        tn = x_mcp.get("toolName")
        if tn:
            tool_names[tn].append(rel(fpath))
    # Check workflow-level x-mcp
    workflows = doc.get("workflows", [])
    if isinstance(workflows, list):
        for wf in workflows:
            if not isinstance(wf, dict):
                continue
            wf_mcp = wf.get("x-mcp")
            if isinstance(wf_mcp, dict):
                tn = wf_mcp.get("toolName")
                if tn:
                    tool_names[tn].append(f"{rel(fpath)}:{wf.get('workflowId', '?')}")

f14_errors = []
for name, locations in tool_names.items():
    if len(locations) > 1:
        f14_errors.append(f"toolName '{name}' appears in: {', '.join(locations)}")

if not f14_errors:
    emit("F14", "PASS", "x-mcp.toolName values are globally unique")
else:
    emit("F14", "FAIL", f"{len(f14_errors)} duplicate toolName(s)")
    for e in f14_errors:
        detail(f"  {e}")

PYEOF
)

# ─── Format and display results ──────────────────────────────────────────────

TOTAL=0
PASSED=0
FAILED=0
WARNED=0
CURRENT_GROUP=""
EXIT_CODE=0

while IFS= read -r line; do
    if [[ "$line" == DETAIL\|* ]]; then
        msg="${line#DETAIL|}"
        echo "    $msg"
        continue
    fi

    IFS='|' read -r check_id status message <<< "$line"

    # Determine group header
    group="${check_id:0:1}"
    case "$group" in
        A) group_name="Group A: File Organization" ;;
        B) group_name="Group B: Cross-Spec operationId Resolution" ;;
        C) group_name="Group C: Cross-Spec Event Name Resolution" ;;
        D) group_name="Group D: Recipe Reference Resolution" ;;
        E) group_name="Group E: Cross-File Granularity" ;;
        F) group_name="Group F: Global Uniqueness" ;;
        *) group_name="Unknown Group" ;;
    esac

    if [ "$group" != "$CURRENT_GROUP" ]; then
        echo ""
        echo "--- $group_name ---"
        CURRENT_GROUP="$group"
    fi

    TOTAL=$((TOTAL + 1))
    case "$status" in
        PASS)
            echo -e "  \033[0;32m[PASS]\033[0m $check_id: $message"
            PASSED=$((PASSED + 1))
            ;;
        FAIL)
            echo -e "  \033[0;31m[FAIL]\033[0m $check_id: $message"
            FAILED=$((FAILED + 1))
            EXIT_CODE=1
            ;;
        WARN)
            echo -e "  \033[1;33m[WARN]\033[0m $check_id: $message"
            WARNED=$((WARNED + 1))
            ;;
    esac
done <<< "$RESULTS"

# ─── Summary ─────────────────────────────────────────────────────────────────

echo ""
echo "=== Validation Summary ==="
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\033[0;32m$TOTAL checks: $PASSED passed, $FAILED failed, $WARNED warnings\033[0m"
    echo ""
    echo "Arazzo structure and cross-spec validation passed."
    echo "  - File organization verified"
    echo "  - operationId references resolved against OpenAPI"
    echo "  - Event names resolved against AsyncAPI messages"
    echo "  - Recipe references and extends chains validated"
    echo "  - Step overlap within acceptable thresholds"
    echo "  - x-mcp.toolName uniqueness confirmed"
else
    echo -e "\033[0;31m$TOTAL checks: $PASSED passed, $FAILED failed, $WARNED warnings\033[0m"
    echo ""
    echo "Fix the failures above and re-run."
fi

exit $EXIT_CODE
