#!/bin/bash
# Full Specification Validation Suite (Mac/Linux)
# Usage: ./scripts/specfuse/validate-specs.sh [version]
# Example: ./scripts/specfuse/validate-specs.sh v1
#
# Orchestrates EVERY validation layer — OpenAPI, AsyncAPI, Arazzo, and the
# cross-spec link rules that bind them. Each layer is a self-contained
# sub-script (it bundles its own input and checks its own toolchain).
#
# Behavior:
#   - Runs ALL layers; does NOT short-circuit on first failure, so one run
#     surfaces every broken layer instead of one-at-a-time.
#   - FAIL HARD: a missing toolchain (java / spectral / redocly /
#     openapi-generator-cli / python3) counts as a failure, not a skip —
#     guarantees full coverage every run.
#   - Cross-spec (project.json) runs LAST: it presumes each single-spec layer
#     already passed.
#   - Exits non-zero if any layer fails.
#
# To validate a single layer during focused edits, call its sub-script directly
# (e.g. ./scripts/specfuse/validate-async-structure.sh).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION=${1:-"latest"}

echo "=========================================="
echo " Specfuse — Full Spec Validation Suite"
echo " Version: $VERSION"
echo "=========================================="
echo ""

# Ordered layer list. Each entry: "Label::command [args...]"
# Order is dependency-correct; cross-spec link validation runs last.
# NOTE on the generator layer: the SpecFuse generator's `validate project.json`
# runs the full OpenAPI DDD ruleset AND the async cross-spec (ASYNC_*) rules in
# one pass — a strict superset of the old per-spec `validate --spec`. So there is
# ONE generator layer (validate-generator.sh: bundle + validate-source + validate
# project.json), not three. It runs LAST since it is the cross-spec gate and
# presumes the single-tool lint layers below already passed.
LAYERS=(
    "OpenAPI structure::$SCRIPT_DIR/validate-structure.sh $VERSION"
    "OpenAPI generator compat::$SCRIPT_DIR/validate-openapi-generator.sh"
    "OpenAPI Spectral lint::$SCRIPT_DIR/validate-spectral.sh $VERSION"
    "OpenAPI Redocly::$SCRIPT_DIR/validate-redocly.sh $VERSION"
    "AsyncAPI structure::$SCRIPT_DIR/validate-async-structure.sh"
    "AsyncAPI Spectral lint::$SCRIPT_DIR/validate-async-spectral.sh"
    "Arazzo structure::$SCRIPT_DIR/validate-arazzo.sh"
    "Arazzo Spectral lint::$SCRIPT_DIR/validate-arazzo-spectral.sh"
    "Generator validation (OpenAPI DDD + async cross-spec + source-tree)::$SCRIPT_DIR/validate-generator.sh"
)

RESULT_LABELS=()
RESULT_STATUS=()
ANY_FAILED=0

for entry in "${LAYERS[@]}"; do
    label="${entry%%::*}"
    cmd="${entry##*::}"

    echo ""
    echo "──────────────────────────────────────────"
    echo "▶ $label"
    echo "  \$ $cmd"
    echo "──────────────────────────────────────────"

    if [ ! -x "${cmd%% *}" ] && [ ! -f "${cmd%% *}" ]; then
        echo "❌ Sub-script not found: ${cmd%% *}"
        RESULT_LABELS+=("$label")
        RESULT_STATUS+=("MISSING-SCRIPT")
        ANY_FAILED=1
        continue
    fi

    # Run the layer. Sub-scripts already fail-hard on missing toolchain,
    # so a non-zero exit here covers both real violations and absent tools.
    bash $cmd
    status=$?

    if [ $status -eq 0 ]; then
        RESULT_LABELS+=("$label")
        RESULT_STATUS+=("PASS")
    else
        RESULT_LABELS+=("$label")
        RESULT_STATUS+=("FAIL")
        ANY_FAILED=1
    fi
done

echo ""
echo "=========================================="
echo " Validation Summary"
echo "=========================================="
for i in "${!RESULT_LABELS[@]}"; do
    st="${RESULT_STATUS[$i]}"
    case "$st" in
        PASS) icon="✅" ;;
        *)    icon="❌" ;;
    esac
    printf "  %s  %-32s %s\n" "$icon" "${RESULT_LABELS[$i]}" "$st"
done
echo "=========================================="

if [ $ANY_FAILED -ne 0 ]; then
    echo "❌ One or more validation layers failed. See output above."
    exit 1
fi

echo "✅ All validation layers passed — specs are ready for code generation."
exit 0
