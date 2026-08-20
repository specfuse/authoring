#!/bin/bash
# Redocly Validation Script
# Usage: ./scripts/specfuse/validate-redocly.sh [version]

set -e

# Resolve repo root (script lives in scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values
VERSION=${1:-"latest"}

# Resolve the spec version rather than assuming one: a project may be on v1
# today and v2 later, and this script should follow it.
if [ "$VERSION" = "latest" ]; then
    LATEST_VERSION=$(ls -d "$REPO_ROOT/api/specs/v"* 2>/dev/null | sort -V | tail -n 1 | xargs basename 2>/dev/null)
    if [ -n "$LATEST_VERSION" ]; then
        VERSION=$LATEST_VERSION
    fi
fi
SPEC_PATH="$REPO_ROOT/api/specs/$VERSION"

echo "=== Redocly Validation Script ==="
echo "Version: $VERSION"
echo "Spec Path: $SPEC_PATH"
echo ""

# Check if Redocly is installed
if ! command -v redocly &> /dev/null; then
    echo "❌ Redocly not found. Please run installation script first."
    echo "  npm install -g @redocly/cli"
    echo "  (or: yarn global add @redocly/cli)"
    exit 1
fi

REDOCLY_VERSION=$(redocly --version)
echo "✅ Redocly version: $REDOCLY_VERSION"

# Check if spec directory exists
if [ ! -d "$SPEC_PATH" ]; then
    echo "❌ Spec directory not found: $SPEC_PATH"
    echo "Available versions:"
    ls -d "$REPO_ROOT"/api/specs/v*/ 2>/dev/null || echo "No version directories found"
    exit 1
fi

echo "✅ Spec directory found: $SPEC_PATH"

# Step 1: Validate specs
echo ""
echo "=== Step 1: Validating OpenAPI specs ==="
if redocly lint "$SPEC_PATH/openapi.yaml"; then
    echo "✅ All specs pass Redocly validation"
else
    echo "❌ Redocly validation failed"
    exit 1
fi

# Step 2: Check for common issues
echo ""
echo "=== Step 2: Checking for common issues ==="

# Check for duplicate operation IDs
echo "Checking for duplicate operation IDs..."
DUPLICATE_OPS=$(grep -r "operationId:" "$SPEC_PATH" | awk '{print $2}' | sort | uniq -d)
if [ -n "$DUPLICATE_OPS" ]; then
    echo "⚠️  Duplicate operation IDs found:"
    echo "$DUPLICATE_OPS"
else
    echo "✅ No duplicate operation IDs found"
fi

echo ""
echo "=== Validation Summary ==="
echo "✅ Redocly validation passed!"
