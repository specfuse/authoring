#!/bin/bash
# Implementation-Prompts Reverse Index Builder
# Usage: ./scripts/specfuse/build-prompt-index.sh [--format json|yaml]
#
# Parses YAML front-matter from every *.md file under api/docs/implementation-prompts/
# (excluding README.md) and emits a reverse index of the form:
#   { spec-path: [ { file, relevance, phase, status, audience }, ... ] }
#
# Used by /prepare-handoff to populate §10 of the handoff manifest.
#
# Behavior:
# - Skips files with status == 'deprecated' or 'superseded'.
# - Emits warnings to stderr (does not crash) for: missing front-matter,
#   malformed YAML, target paths that don't exist on disk.
# - Exit code: 0 on success (warnings allowed), 1 on hard error (e.g., python3 missing).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMPTS_DIR="$REPO_ROOT/api/docs/implementation-prompts"

FORMAT="json"
if [ "$1" = "--format" ] && [ -n "$2" ]; then
    FORMAT="$2"
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is required but not installed." >&2
    exit 1
fi

if [ ! -d "$PROMPTS_DIR" ]; then
    # A project that has not written any implementation prompts yet is the
    # normal starting state, not an error. Emit an empty index so callers
    # (prepare-handoff) can consume the output unconditionally.
    echo "No implementation-prompts directory ($PROMPTS_DIR) — emitting an empty index." >&2
    if [ "$FORMAT" = "yaml" ]; then
        echo "{}"
    else
        echo "{}"
    fi
    exit 0
fi

python3 - "$PROMPTS_DIR" "$REPO_ROOT" "$FORMAT" <<'PYEOF'
import json
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip3 install pyyaml", file=sys.stderr)
    sys.exit(1)

prompts_dir = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
fmt = sys.argv[3]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

index = {}
files_seen = 0
files_with_frontmatter = 0
files_skipped = 0
warnings = []

for md_path in sorted(prompts_dir.glob("*.md")):
    if md_path.name == "README.md":
        continue

    files_seen += 1
    rel_path = str(md_path.relative_to(repo_root))
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        warnings.append(f"{rel_path}: failed to read ({e})")
        continue

    m = FRONTMATTER_RE.match(text)
    if not m:
        warnings.append(f"{rel_path}: missing YAML front-matter; skipping")
        continue

    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        warnings.append(f"{rel_path}: malformed YAML front-matter ({e}); skipping")
        continue

    status = meta.get("status", "active")
    if status in ("deprecated", "superseded"):
        files_skipped += 1
        continue

    targets = meta.get("targets") or []
    if not isinstance(targets, list) or not targets:
        warnings.append(f"{rel_path}: front-matter has no targets; skipping")
        continue

    files_with_frontmatter += 1

    for entry in targets:
        if not isinstance(entry, dict):
            warnings.append(f"{rel_path}: target entry is not an object: {entry!r}")
            continue
        spec_path = entry.get("path")
        relevance = entry.get("relevance", "")
        if not spec_path:
            warnings.append(f"{rel_path}: target entry missing 'path'")
            continue
        full_target = repo_root / spec_path
        if not full_target.exists():
            warnings.append(
                f"{rel_path}: target path does not exist on disk: {spec_path}"
            )
        index.setdefault(spec_path, []).append({
            "file": rel_path,
            "relevance": relevance,
            "phase": meta.get("phase"),
            "status": status,
            "audience": meta.get("audience"),
        })

for w in warnings:
    print(f"WARN: {w}", file=sys.stderr)

print(
    f"# Scanned {files_seen} files, {files_with_frontmatter} with valid front-matter, "
    f"{files_skipped} skipped (deprecated/superseded), {len(warnings)} warnings.",
    file=sys.stderr,
)

if fmt == "yaml":
    yaml.safe_dump(index, sys.stdout, sort_keys=True, default_flow_style=False)
else:
    json.dump(index, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
PYEOF
