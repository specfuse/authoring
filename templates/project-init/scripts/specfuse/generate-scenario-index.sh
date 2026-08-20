#!/usr/bin/env bash
set -euo pipefail

# generate-scenario-index.sh
#
# Post-generation script that adds cross-links from operationIds and event
# names in generated scenario docs to their source YAML files.
#
# Called automatically by generate-scenario-docs.sh after Specfuse generation.
#
# Usage:
#   ./scripts/specfuse/generate-scenario-index.sh [--skip-crosslinks]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FLOWS_DIR="${ROOT_DIR}/api/docs/flows"
SPECS_DIR="${ROOT_DIR}/api/specs/v1"

SKIP_CROSSLINKS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-crosslinks) SKIP_CROSSLINKS=true; shift ;;
    *) shift ;;
  esac
done

# ── Cross-linking ──────────────────────────────────────────────────────────

add_crosslinks() {
  local file="$1"

  # Extract domain from metadata line (line 3)
  local domain
  domain=$(sed -n '3p' "$file" | sed -n 's/.*\*\*Domain:\*\* *\([a-z-]*\).*/\1/p')
  [[ -z "$domain" ]] && return

  local ops_dir="${SPECS_DIR}/domains/${domain}/operations"
  local msgs_dir="${SPECS_DIR}/domains/${domain}/messages"
  local rel_ops="../../../../specs/v1/domains/${domain}/operations"
  local rel_msgs="../../../../specs/v1/domains/${domain}/messages"

  # Skip if already cross-linked (idempotency)
  if grep -q '\[`[a-z].*`\](.*operations/.*\.yaml)' "$file" 2>/dev/null; then
    return
  fi

  # Build sed commands for all replacements in one pass
  local sed_args=()

  # Find backtick-wrapped camelCase identifiers (operationIds)
  local op_ids
  op_ids=$(grep -oE '`[a-z][a-zA-Z]+`' "$file" | sort -u | tr -d '`')

  for op_id in $op_ids; do
    local kebab
    kebab=$(echo "$op_id" | sed -E 's/([a-z0-9])([A-Z])/\1-\2/g' | tr '[:upper:]' '[:lower:]')

    if [[ -f "${ops_dir}/${kebab}.yaml" ]]; then
      sed_args+=(-e "s|\`${op_id}\`|[\`${op_id}\`](${rel_ops}/${kebab}.yaml)|g")
    fi
  done

  # Find backtick-wrapped Entity.Action event names
  local events
  events=$(grep -oE '`[A-Z][a-zA-Z]+\.[A-Z][a-zA-Z]+`' "$file" 2>/dev/null | sort -u | tr -d '`' || true)

  for event in $events; do
    local msg_filename="${event//.}.yaml"

    if [[ -f "${msgs_dir}/${msg_filename}" ]]; then
      sed_args+=(-e "s|\`${event}\`|[\`${event}\`](${rel_msgs}/${msg_filename})|g")
    fi
  done

  if [[ ${#sed_args[@]} -gt 0 ]]; then
    sed -i '' "${sed_args[@]}" "$file"
  fi
}

# ── Main ───────────────────────────────────────────────────────────────────

if [[ "${SKIP_CROSSLINKS}" == true ]]; then
  echo "Cross-linking skipped."
  exit 0
fi

echo "Adding cross-links to generated scenario docs..."
COUNT=0
while IFS= read -r doc; do
  add_crosslinks "$doc"
  COUNT=$((COUNT + 1))
done < <(find "${FLOWS_DIR}" -path "*/scenarios/*.md" -not -name "index.md" 2>/dev/null)

echo "Cross-linked ${COUNT} scenario doc(s)."
