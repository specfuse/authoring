#!/bin/bash
# Spectral API Linting Script (Validates Bundled Spec)
# Usage: ./scripts/validate-spectral.sh [version]
# Example: ./scripts/validate-spectral.sh v1
#
# Note: Bundles the spec first, then validates the bundled output.
# This avoids issues with $ref at operation level which is not strictly
# valid OpenAPI 3.0 but is supported by bundling tools.

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
VERSION=${1:-"latest"}
# Use the kit's Spectral ruleset (casing, naming, HTTP contract, x-entity
# shape, op-extension shapes). Historical note: this once fell back to
# spectral:oas due to JSONPath parsing issues in the custom ruleset — resolved;
# the wrapper silently skipping every rm-* rule let a path-casing error ship
# (2026-07-19). Do not revert to spectral:oas.
RULESET="$PROJECT_ROOT/.specfuse/authoring/schemas/spectral/specfuse-openapi.yaml"

# Determine spec path
if [ "$VERSION" = "latest" ]; then
    # Find the latest version directory
    LATEST_VERSION=$(ls -d "$PROJECT_ROOT/api/specs/v"* 2>/dev/null | sort -V | tail -n 1 | xargs basename 2>/dev/null)
    if [ -z "$LATEST_VERSION" ]; then
        MAIN_SPEC="$PROJECT_ROOT/api/specs/openapi.yaml"
    else
        MAIN_SPEC="$PROJECT_ROOT/api/specs/$LATEST_VERSION/openapi.yaml"
        VERSION=$LATEST_VERSION
    fi
else
    MAIN_SPEC="$PROJECT_ROOT/api/specs/$VERSION/openapi.yaml"
fi

# Bundled spec output path
BUNDLED_SPEC="$PROJECT_ROOT/output/openapi-bundled.yaml"

echo "=== Spectral API Linting Script (Optimized) ==="
echo "Version: $VERSION"
echo "Main Spec: $MAIN_SPEC"
echo "Ruleset: $RULESET"
echo ""

# Vocabulary drift guard, BEFORE the lint.
#
# The ruleset closes several vendor extensions with `additionalProperties:
# false`, over a vocabulary the generator owns. When the generator adds a key
# and the ruleset does not learn about it, the first spec to declare that key
# fails lint with an `additionalProperties` error — the feature cannot be
# adopted, and the error names the spec rather than the ruleset. Running the
# check first means the drift is reported as drift.
#
# Advisory here, fatal in CI (`--require-jar`): a developer who has never run
# `generate` has no cached jar, and blocking their lint on that would be worse
# than the drift. The skip is loud, never silent.
if [ -f "$SCRIPT_DIR/check-extension-vocabulary.py" ]; then
    python3 "$SCRIPT_DIR/check-extension-vocabulary.py" || {
        echo ""
        echo "❌ Vendor-extension vocabulary drift — see above."
        echo "   Linting now would report the ruleset's gap as a spec error."
        exit 1
    }
    echo ""
fi

# Check if main spec exists
if [ ! -f "$MAIN_SPEC" ]; then
    echo "❌ Main OpenAPI spec not found: $MAIN_SPEC"
    exit 1
fi

echo "✅ Main OpenAPI spec found"

# Bundle the spec first
echo ""
echo "=== Step 1: Bundling OpenAPI Spec ==="
echo "Bundling to resolve all \$ref references..."

mkdir -p "$PROJECT_ROOT/output"
if "$SCRIPT_DIR/bundle-spec.sh" "$MAIN_SPEC" "$BUNDLED_SPEC" > /dev/null 2>&1; then
    echo "✅ Bundled spec created: $BUNDLED_SPEC"
else
    echo "❌ Failed to bundle spec"
    exit 1
fi

# Strip null values before linting.
#
# Spectral's JSONPath engine (nimma) crashes with
#   "Cannot read properties of null (reading 'enum')"
# when the document contains null values and several of the ruleset's filter
# expressions are compiled together. No single rule reproduces it in isolation,
# and bare spectral:oas is clean — it only manifests in combination, so the
# whole run dies and reports zero findings. That silence looked like a pass and
# hid 218 real errors on main.
#
# Property-level `example: null` entries were removed at the source. The
# remaining nulls are meaningful values inside example payloads (`effectiveTo:
# null` = open-ended, `roleId: null` = unfiltered), which are worth keeping in
# the published spec — so they are stripped here, for linting only. The
# committed specs are untouched.
#
# Remove this once the upstream nimma bug is fixed.
LINT_INPUT="$PROJECT_ROOT/output/openapi-bundled.lint.yaml"
if python3 - "$BUNDLED_SPEC" "$LINT_INPUT" <<'PYSTRIP'
import sys, yaml
src, dst = sys.argv[1], sys.argv[2]
def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if v is not None}
    if isinstance(o, list):
        return [strip(v) for v in o if v is not None]
    return o
yaml.safe_dump(strip(yaml.safe_load(open(src))), open(dst, "w"), sort_keys=False)
PYSTRIP
then
    echo "✅ Null-stripped lint input created (nimma crash workaround)"
    BUNDLED_SPEC="$LINT_INPUT"
else
    echo "⚠️  Null-strip failed; linting the raw bundle (may crash)"
fi

# Check if Spectral is installed
if ! command -v spectral &> /dev/null; then
    echo "❌ Spectral not found. Please run installation script first."
    echo "  npm install -g @stoplight/spectral-cli"
    echo "  (or: yarn global add @stoplight/spectral-cli)"
    exit 1
fi

SPECTRAL_VERSION=$(spectral --version)
echo "✅ Spectral version: $SPECTRAL_VERSION"
echo "✅ Using ruleset: $RULESET"
echo ""

# Run Spectral linting on bundled spec
echo ""
echo "=== Step 2: Running Spectral Lint ==="
echo "Linting bundled OpenAPI specification..."
echo ""

# Initialize error tracking
LINT_FAILED=0

echo "📄 Linting: $(basename "$BUNDLED_SPEC")"
echo ""

if spectral lint "$BUNDLED_SPEC" --ruleset "$RULESET" --format stylish; then
    echo ""
    echo "✅ Spectral validation passed"
    LINT_FAILED=0
else
    echo ""
    echo "❌ Spectral validation failed"
    LINT_FAILED=1
fi

# Summary
echo "=== Validation Summary ==="
if [ $LINT_FAILED -eq 0 ]; then
    echo "✅ All OpenAPI specs pass Spectral validation!"
    echo ""
    echo "Your API specifications comply with:"
    echo "  - API Handbook standards"
    echo "  - Resource naming conventions (PascalCase schemas, camelCase properties)"
    echo "  - HTTP contract requirements (status codes, headers)"
    echo "  - Concurrency control (ETags, If-Match)"
    echo "  - Authorization metadata (x-roles, x-scopes)"
    echo "  - DDD architecture (x-entity, aggregate boundaries)"
    echo "  - AI agent integration patterns (validateOnly, idempotency)"
    echo ""
    exit 0
else
    echo "❌ Spectral validation failed for one or more specs"
    echo ""
    echo "Common fixes:"
    echo "  - Check role names against allowed values"
    echo "  - Ensure proper x-entity metadata on main resources"
    echo "  - Verify HTTP status codes and headers"
    echo "  - Review error response structures"
    echo "  - Confirm pagination parameter consistency"
    echo ""
    echo "See above output for specific errors and warnings."
    exit 1
fi
