#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# The generator is resolved, checksum-verified and run by the kit CLI against
# the version pinned in generator.lock -- there is no jar to keep next to this
# script. Override with SPECFUSE_AUTHORING to point at a different CLI.
SPECFUSE="${SPECFUSE_AUTHORING:-specfuse-authoring}"
# `specfuse-authoring generate` runs the PINNED GENERATOR JAR with whatever
# follows it, so the jar's own verb (generate / validate / validate-source) is
# passed explicitly as the first argument below. Dropping it silently runs the
# jar with no subcommand.
RUN_GENERATOR=("${SPECFUSE}" generate)

# The project file is named after the project (<name>-project.json), so find it
# rather than hardcoding one project's name.
CONFIG_FILE=""
for candidate in "${ROOT_DIR}"/*-project.json; do
  if [[ -f "$candidate" ]]; then
    CONFIG_FILE="$candidate"
    break
  fi
done

CLEAN=false
SKIP_INDEX=false
SKIP_CROSSLINKS=false
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean)
      CLEAN=true
      shift
      ;;
    --skip-index)
      SKIP_INDEX=true
      shift
      ;;
    --skip-crosslinks)
      SKIP_CROSSLINKS=true
      shift
      ;;
    -*)
      ARGS+=("$1")
      shift
      ;;
    *)
      CONFIG_FILE="$1"
      shift
      ARGS+=("$@")
      break
      ;;
  esac
done

if ! command -v "${SPECFUSE}" >/dev/null 2>&1; then
  echo "specfuse-authoring not found on PATH." >&2
  echo "Install it:  pipx install specfuse-authoring" >&2
  exit 1
fi

if [[ -z "${CONFIG_FILE}" || ! -f "${CONFIG_FILE}" ]]; then
  echo "Project file not found: expected <name>-project.json in ${ROOT_DIR}" >&2
  exit 1
fi

if [[ "${CLEAN}" == true ]]; then
  echo "Cleaning generated scenario docs..."
  find "${ROOT_DIR}/api/docs/flows" -path "*/scenarios/*.md" -delete 2>/dev/null || true
  echo "Cleaning generated technical reference docs..."
  rm -rf "${ROOT_DIR}/docs/generated" 2>/dev/null || true
fi

echo "Bundling OpenAPI specs..."
"${SCRIPT_DIR}/bundle-spec.sh" "${ROOT_DIR}/api/specs/v1/openapi.yaml" "${ROOT_DIR}/output/openapi-bundled.yaml"

echo "Bundling AsyncAPI specs..."
"${SCRIPT_DIR}/bundle-async-spec.sh" "${ROOT_DIR}/api/specs/v1/asyncapi.yaml" "${ROOT_DIR}/output/asyncapi-bundled.yaml"

echo "Generating scenario documentation..."
cd "${ROOT_DIR}"
"${RUN_GENERATOR[@]}" generate --progress --group "Documentation - Scenarios" ${ARGS[@]+"${ARGS[@]}"} "${CONFIG_FILE}"

echo "Generating technical reference documentation..."
"${RUN_GENERATOR[@]}" generate --progress --group "Documentation - Technical References" ${ARGS[@]+"${ARGS[@]}"} "${CONFIG_FILE}"

# Post-generation: cross-links + index
INDEX_ARGS=()
if [[ "${SKIP_CROSSLINKS}" == true ]]; then
  INDEX_ARGS+=("--skip-crosslinks")
fi

if [[ "${SKIP_INDEX}" == false ]]; then
  echo ""
  "${SCRIPT_DIR}/generate-scenario-index.sh" "${INDEX_ARGS[@]+"${INDEX_ARGS[@]}"}"
fi

# Summary
echo ""
echo "Generated scenario docs:"
find "${ROOT_DIR}/api/docs/flows" -path "*/scenarios/*.md" -not -name "index.md" | sort | while read -r f; do
  echo "  ${f#${ROOT_DIR}/}"
done
COUNT=$(find "${ROOT_DIR}/api/docs/flows" -path "*/scenarios/*.md" -not -name "index.md" 2>/dev/null | wc -l | tr -d ' ')
echo ""
echo "Total: ${COUNT} scenario doc(s) generated."

echo ""
echo "Generated technical reference docs:"
if [[ -d "${ROOT_DIR}/docs/generated" ]]; then
  find "${ROOT_DIR}/docs/generated" -name "*.md" | sort | while read -r f; do
    echo "  ${f#${ROOT_DIR}/}"
  done
  REF_COUNT=$(find "${ROOT_DIR}/docs/generated" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  echo ""
  echo "Total: ${REF_COUNT} technical reference doc(s) generated."
fi
