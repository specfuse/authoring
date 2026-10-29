#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# The generator is resolved, checksum-verified and run by the kit CLI against
# the version pinned in generator.lock -- there is no jar to keep next to this
# script. Override with SPECFUSE_AUTHORING to point at a different CLI.
#
# The suite is driven through the single `specfuse` command; the flat
# `specfuse-authoring` script is a deprecated alias kept working for standalone
# installs until 1.0.0. Prefer the subcommand, fall back to the alias.
if [ -n "${SPECFUSE_AUTHORING:-}" ]; then
  SPECFUSE_CLI=("${SPECFUSE_AUTHORING}")
elif command -v specfuse >/dev/null 2>&1; then
  SPECFUSE_CLI=(specfuse authoring)
else
  SPECFUSE_CLI=(specfuse-authoring)
fi
# `specfuse authoring generate` runs the PINNED GENERATOR JAR with whatever
# follows it, so the jar's own verb (generate / validate / validate-source) is
# passed explicitly as the first argument below. Dropping it silently runs the
# jar with no subcommand.
RUN_GENERATOR=("${SPECFUSE_CLI[@]}" generate)

# The groups to run and where they write come from the project file: every
# group with `"language": "markdown"`, read by the same helper generate.sh uses.
# shellcheck source=project-file.sh
. "${SCRIPT_DIR}/project-file.sh"

# The project file is named after the project (<name>-project.json), so find it
# rather than hardcoding one project's name.
CONFIG_FILE="$(find_project_file "${ROOT_DIR}")"

# Scenario specs live here, so it is cleaned file by file, never removed.
FLOWS_DIR="${ROOT_DIR}/api/docs/flows"

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

if [[ -z "${CONFIG_FILE}" || ! -f "${CONFIG_FILE}" ]]; then
  echo "Project file not found: expected <name>-project.json in ${ROOT_DIR}" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found (needed to read the project file)." >&2
  exit 1
fi
CONFIG="${CONFIG_FILE}"

MD_GROUPS=()
MD_DESTS=()
while IFS=$'\t' read -r name lang dest _; do
  if [[ "$(canon_lang "$lang")" == "markdown" ]]; then
    MD_GROUPS+=("$name")
    MD_DESTS+=("${dest:-.}")
  fi
done < <(groups_tsv)

if [[ ${#MD_GROUPS[@]} -eq 0 ]]; then
  echo "No Markdown group in $(basename "${CONFIG_FILE}"): nothing to generate." >&2
  echo "Add a group with \"language\": \"markdown\" (see Project_File.md, groups[])." >&2
  exit 1
fi

if ! command -v "${SPECFUSE_CLI[0]}" >/dev/null 2>&1; then
  echo "${SPECFUSE_CLI[*]} not found on PATH." >&2
  echo "Install the suite:  pipx install specfuse   (or: uv tool install specfuse)" >&2
  exit 1
fi

# abs_dest <destination> — the destination as an absolute path, resolved from
# the project root the way the generator resolves it.
abs_dest() {
  python3 -c 'import os, sys; print(os.path.normpath(os.path.join(sys.argv[1], sys.argv[2])))' "${ROOT_DIR}" "$1"
}

# Whether a destination may be removed whole: inside this repo, not its root,
# and not holding the scenario specs or the specs themselves.
removable_dest() {
  case "$1/" in
    "${ROOT_DIR}"/?*) ;;
    *) return 1 ;;
  esac
  case "${FLOWS_DIR}/" in "$1"/*) return 1 ;; esac
  case "${ROOT_DIR}/api/specs/" in "$1"/*) return 1 ;; esac
  return 0
}

echo "Markdown groups in $(basename "${CONFIG_FILE}"):"
for i in "${!MD_GROUPS[@]}"; do
  echo "  - ${MD_GROUPS[$i]} -> ${MD_DESTS[$i]}"
done

if [[ "${CLEAN}" == true ]]; then
  echo "Cleaning generated scenario docs..."
  find "${FLOWS_DIR}" -path "*/scenarios/*.md" -delete 2>/dev/null || true
  for i in "${!MD_GROUPS[@]}"; do
    dest="$(abs_dest "${MD_DESTS[$i]}")"
    if removable_dest "$dest"; then
      echo "Cleaning ${MD_DESTS[$i]} (${MD_GROUPS[$i]})..."
      rm -rf "$dest" 2>/dev/null || true
    else
      echo "Not cleaning ${MD_DESTS[$i]} (${MD_GROUPS[$i]}): outside this repo, its root, or holds the specs."
    fi
  done
fi

echo "Bundling OpenAPI specs..."
"${SCRIPT_DIR}/bundle-spec.sh" "${ROOT_DIR}/api/specs/v1/openapi.yaml" "${ROOT_DIR}/output/openapi-bundled.yaml"

echo "Bundling AsyncAPI specs..."
"${SCRIPT_DIR}/bundle-async-spec.sh" "${ROOT_DIR}/api/specs/v1/asyncapi.yaml" "${ROOT_DIR}/output/asyncapi-bundled.yaml"

cd "${ROOT_DIR}"
for g in "${MD_GROUPS[@]}"; do
  echo "Generating ${g}..."
  "${RUN_GENERATOR[@]}" generate --progress --group "$g" ${ARGS[@]+"${ARGS[@]}"} "${CONFIG_FILE}"
done

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
COUNT=0
if [[ -d "${FLOWS_DIR}" ]]; then
  find "${FLOWS_DIR}" -path "*/scenarios/*.md" -not -name "index.md" | sort | while read -r f; do
    echo "  ${f#"${ROOT_DIR}"/}"
  done
  COUNT=$(find "${FLOWS_DIR}" -path "*/scenarios/*.md" -not -name "index.md" | wc -l | tr -d ' ')
fi
echo ""
echo "Total: ${COUNT} scenario doc(s) generated."

# A destination holding the scenario folder is covered by the count above;
# listing every Markdown file under it would also list hand-written docs.
for i in "${!MD_GROUPS[@]}"; do
  dest="$(abs_dest "${MD_DESTS[$i]}")"
  case "${FLOWS_DIR}/" in "$dest"/*) continue ;; esac
  [[ -d "$dest" ]] || continue
  echo ""
  echo "Generated ${MD_GROUPS[$i]} docs (${MD_DESTS[$i]}):"
  find "$dest" -name "*.md" | sort | while read -r f; do
    echo "  ${f#"${ROOT_DIR}"/}"
  done
  REF_COUNT=$(find "$dest" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  echo ""
  echo "Total: ${REF_COUNT} ${MD_GROUPS[$i]} doc(s) generated."
done
