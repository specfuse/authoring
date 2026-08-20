#!/bin/bash
# Arazzo Spectral Linting Script
# Usage: ./scripts/specfuse/validate-arazzo-spectral.sh
#
# Discovers all Arazzo scenario (*.arazzo.yaml) and recipe (*.recipe.yaml) files,
# runs Spectral lint with the kit's Arazzo ruleset on each, and reports
# aggregated results.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPEC_DIR="$PROJECT_ROOT/api/specs/v1"
RULESET="$PROJECT_ROOT/.specfuse/authoring/schemas/spectral/specfuse-arazzo.yaml"

echo "=== Arazzo Spectral Linting Script ==="
echo "Spec Directory: $SPEC_DIR"
echo "Ruleset: $RULESET"
echo ""

# Check if Spectral is installed
if ! command -v spectral &> /dev/null; then
    echo "[FAIL] Spectral not found. Please install:"
    echo "  npm install -g @stoplight/spectral-cli"
    exit 1
fi

SPECTRAL_VERSION=$(spectral --version)
echo "[OK] Spectral version: $SPECTRAL_VERSION"

# Check if ruleset exists
if [ ! -f "$RULESET" ]; then
    echo "[FAIL] Arazzo Spectral ruleset not found: $RULESET"
    echo "  This file is created by WU-1.1. Run that work unit first."
    exit 1
fi

echo "[OK] Arazzo ruleset found"
echo ""

# Discover all Arazzo and recipe files
ARAZZO_FILES=()
while IFS= read -r f; do
    ARAZZO_FILES+=("$f")
done < <(find "$SPEC_DIR" -name "*.arazzo.yaml" -type f 2>/dev/null | sort)

RECIPE_FILES=()
while IFS= read -r f; do
    RECIPE_FILES+=("$f")
done < <(find "$SPEC_DIR" -name "*.recipe.yaml" -type f 2>/dev/null | sort)

ALL_FILES=(${ARAZZO_FILES[@]+"${ARAZZO_FILES[@]}"} ${RECIPE_FILES[@]+"${RECIPE_FILES[@]}"})

echo "Scenario files: ${#ARAZZO_FILES[@]}"
echo "Recipe files:   ${#RECIPE_FILES[@]}"
echo "Total files:    ${#ALL_FILES[@]}"
echo ""

if [ ${#ALL_FILES[@]} -eq 0 ]; then
    echo "No Arazzo or recipe files found. Nothing to lint."
    exit 0
fi

# Run Spectral on each file
echo "=== Running Spectral Lint ==="
echo ""

TOTAL_FILES=0
PASSED_FILES=0
FAILED_FILES=0
TOTAL_ERRORS=0
TOTAL_WARNINGS=0

for file in "${ALL_FILES[@]}"; do
    TOTAL_FILES=$((TOTAL_FILES + 1))
    rel_path="${file#"$SPEC_DIR"/}"
    echo "--- $rel_path ---"

    # Capture spectral output and exit code
    LINT_OUTPUT=""
    LINT_EXIT=0
    LINT_OUTPUT=$(spectral lint "$file" --ruleset "$RULESET" --format stylish 2>&1) || LINT_EXIT=$?

    if [ $LINT_EXIT -eq 0 ]; then
        echo "  [PASS] No issues"
        PASSED_FILES=$((PASSED_FILES + 1))
    else
        echo "$LINT_OUTPUT" | sed 's/^/  /'
        FAILED_FILES=$((FAILED_FILES + 1))

        # Count errors and warnings from the output
        file_errors=$(echo "$LINT_OUTPUT" | grep -c " error " 2>/dev/null || true)
        file_warnings=$(echo "$LINT_OUTPUT" | grep -c " warning " 2>/dev/null || true)
        TOTAL_ERRORS=$((TOTAL_ERRORS + file_errors))
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + file_warnings))
    fi
    echo ""
done

# Summary
echo "=== Validation Summary ==="
echo "Files linted: $TOTAL_FILES"
echo "  Passed: $PASSED_FILES"
echo "  Failed: $FAILED_FILES"

if [ $TOTAL_ERRORS -gt 0 ] || [ $TOTAL_WARNINGS -gt 0 ]; then
    echo "  Total errors:   $TOTAL_ERRORS"
    echo "  Total warnings: $TOTAL_WARNINGS"
fi

echo ""

if [ $FAILED_FILES -eq 0 ]; then
    echo "Arazzo Spectral validation passed."
    echo ""
    echo "All files comply with:"
    echo "  - Document-level extensions (x-version, x-domain)"
    echo "  - Workflow-level extensions (x-actors, x-setup, x-mcp, x-recipe)"
    echo "  - Step-level extensions (x-as, x-async, x-ui)"
    echo "  - Recipe/scenario exclusion rules"
    echo "  - File homogeneity rules"
    exit 0
else
    echo "Arazzo Spectral validation failed."
    echo ""
    echo "See above output for specific errors and warnings."
    echo "Reference: .specfuse/authoring/handbooks/Arazzo_Handbook.md"
    exit 1
fi
