#!/bin/bash
# AsyncAPI Spectral Linting Script
# Usage: ./scripts/specfuse/validate-async-spectral.sh
#
# Bundles the AsyncAPI spec first, then validates with the
# the kit's AsyncAPI Spectral ruleset.

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Paths
MAIN_SPEC="$PROJECT_ROOT/api/specs/v1/asyncapi.yaml"
BUNDLED_SPEC="$PROJECT_ROOT/output/asyncapi-bundled.yaml"
RULESET="$PROJECT_ROOT/.specfuse/authoring/schemas/spectral/specfuse-asyncapi.yaml"

echo "=== AsyncAPI Spectral Linting Script ==="
echo "Main Spec: $MAIN_SPEC"
echo "Ruleset: $RULESET"
echo ""

# Check if main spec exists
if [ ! -f "$MAIN_SPEC" ]; then
    echo "❌ AsyncAPI spec not found: $MAIN_SPEC"
    exit 1
fi

echo "✅ AsyncAPI spec found"

# Check if ruleset exists
if [ ! -f "$RULESET" ]; then
    echo "❌ Spectral ruleset not found: $RULESET"
    exit 1
fi

echo "✅ Spectral ruleset found"

# Step 1: Bundle the spec
echo ""
echo "=== Step 1: Bundling AsyncAPI Spec ==="
echo "Bundling to resolve all \$ref references..."

mkdir -p "$PROJECT_ROOT/output"
BUNDLE_LOG="$PROJECT_ROOT/output/.async-bundle.log"
if "$SCRIPT_DIR/bundle-async-spec.sh" "$MAIN_SPEC" "$BUNDLED_SPEC" > "$BUNDLE_LOG" 2>&1; then
    echo "✅ Bundled spec created: $BUNDLED_SPEC"
else
    echo "❌ Failed to bundle async spec"
    # Show why. Discarding the bundler's output turns a missing dependency or a
    # spec error into an unactionable one-line failure.
    echo ""
    sed 's/^/    /' "$BUNDLE_LOG"
    echo ""
    exit 1
fi

# Check if Spectral is installed
if ! command -v spectral &> /dev/null; then
    echo "❌ Spectral not found. Please run installation script first."
    echo "  (or: yarn global add @stoplight/spectral-cli)"
    exit 1
fi

SPECTRAL_VERSION=$(spectral --version)
echo "✅ Spectral version: $SPECTRAL_VERSION"
echo ""

# Step 2: Run Spectral linting
echo "=== Step 2: Running Spectral Lint ==="
echo "Linting bundled AsyncAPI specification..."
echo ""

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
echo ""
echo "=== Validation Summary ==="
if [ $LINT_FAILED -eq 0 ]; then
    echo "✅ AsyncAPI specs pass Spectral validation!"
    echo ""
    echo "Your async specifications comply with:"
    echo "  - AsyncAPI Handbook standards"
    echo "  - Channel conventions (x-domain, x-channelType, address format)"
    echo "  - Message conventions (x-messageCategory, naming, payloads)"
    echo "  - Worker metadata (x-worker, handler names, namespaces)"
    echo "  - Saga orchestration rules"
    echo "  - Delivery guarantee metadata"
    echo ""
    exit 0
else
    echo "❌ AsyncAPI Spectral validation failed"
    echo ""
    echo "Common fixes:"
    echo "  - Ensure x-domain and x-channelType on all channels"
    echo "  - Ensure x-messageCategory on all messages"
    echo "  - Events need x-sourceAggregate and x-event"
    echo "  - Commands need x-targetAggregate and x-command"
    echo "  - Jobs need x-scheduledJob with cron"
    echo "  - Operations need x-worker with type, handlerName, namespace"
    echo ""
    echo "See above output for specific errors and warnings."
    exit 1
fi
