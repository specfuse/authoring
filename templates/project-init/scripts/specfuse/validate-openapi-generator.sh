#!/bin/bash
# OpenAPI Generator Validator Script (Mac/Linux)
# Usage: ./scripts/specfuse/validate-openapi-generator.sh [version]
# Example: ./scripts/specfuse/validate-openapi-generator.sh v1

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
VERSION=${1:-"latest"}

# Determine spec path
if [ "$VERSION" = "latest" ]; then
    # Find the latest version directory
    LATEST_VERSION=$(ls -d "$PROJECT_ROOT/api/specs/v"* 2>/dev/null | sort -V | tail -n 1 | xargs basename 2>/dev/null)
    if [ -z "$LATEST_VERSION" ]; then
        SPEC_DIR="$PROJECT_ROOT/api/specs"
    else
        VERSION=$LATEST_VERSION
        SPEC_DIR="$PROJECT_ROOT/api/specs/$VERSION"
    fi
else
    SPEC_DIR="$PROJECT_ROOT/api/specs/$VERSION"
fi

echo "=== OpenAPI Generator Validator (Mac/Linux) ==="
echo "Version: $VERSION"
echo "Spec Directory: $SPEC_DIR"
echo ""

# Check if spec directory exists
if [ ! -d "$SPEC_DIR" ]; then
    echo "❌ Spec directory not found: $SPEC_DIR"
    exit 1
fi

# Check if openapi-generator-cli is installed
if ! command -v openapi-generator-cli &> /dev/null; then
    echo "❌ openapi-generator-cli is not installed"
    echo ""
    echo "Please install it first:"
    echo "  npm install -g @openapitools/openapi-generator-cli"
    echo ""
    exit 1
fi

# Get generator version
GENERATOR_VERSION=$(openapi-generator-cli version 2>/dev/null || echo "unknown")
echo "✅ OpenAPI Generator CLI version: $GENERATOR_VERSION"
echo ""

# Find OpenAPI spec files.
#
# Selecting by extension is wrong here: the documented layout puts BOTH roots
# side by side at the spec root --
#
#   api/specs/v1/
#   ├── openapi.yaml     # OpenAPI 3.0.3
#   └── asyncapi.yaml    # AsyncAPI 3.0.0
#
# -- so a *.yaml glob hands the AsyncAPI document to openapi-generator, which
# rejects it by construction. The layer could then never pass in any project
# with async specs, and validate-specs.sh aggregates it.
#
# Identify OpenAPI documents by their content instead: a top-level `openapi:`
# key (or "openapi": in JSON). That also tolerates extra roots and any future
# file added beside them.
#
# The parentheses matter: `-name a -o -name b` without them binds so that
# -maxdepth applies only to the first term, and the rest match at any depth.
CANDIDATES=$(find "$SPEC_DIR" -maxdepth 1 \( -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) 2>/dev/null | sort)

SPEC_FILES=""
SKIPPED=""
for candidate in $CANDIDATES; do
    if head -n 20 "$candidate" | grep -qE '^[[:space:]]*"?openapi"?[[:space:]]*:'; then
        SPEC_FILES="${SPEC_FILES}${candidate}"$'\n'
    else
        SKIPPED="${SKIPPED}  - $(basename "$candidate")"$'\n'
    fi
done
SPEC_FILES=$(printf '%s' "$SPEC_FILES")

if [ -z "$SPEC_FILES" ]; then
    echo "❌ No OpenAPI spec files found in: $SPEC_DIR"
    echo "   Looked for a top-level 'openapi:' key in *.yaml, *.yml, *.json"
    exit 1
fi

# Count spec files
SPEC_COUNT=$(echo "$SPEC_FILES" | wc -l | tr -d ' ')
echo "✅ Found $SPEC_COUNT OpenAPI spec file(s)"
if [ -n "$SKIPPED" ]; then
    echo "   Skipped (not OpenAPI documents):"
    printf '%s' "$SKIPPED"
fi
echo ""

# Validate each spec file
echo "=== Validating OpenAPI Specifications ==="
echo ""

VALIDATION_FAILED=0
FAILED_FILES=()

while IFS= read -r spec_file; do
    if [ -z "$spec_file" ]; then
        continue
    fi
    
    filename=$(basename "$spec_file")
    echo "📄 Validating: $filename"
    
    # Create temp directory for bundled spec
    TEMP_DIR=$(mktemp -d)
    BUNDLED_SPEC="$TEMP_DIR/bundled-${filename}"
    
    # Bundle the spec first (dereference all $refs)
    echo "  📦 Bundling spec (dereferencing \$refs)..."
    if "$SCRIPT_DIR/bundle-spec.sh" "$spec_file" "$BUNDLED_SPEC" > /dev/null 2>&1; then
        echo "  ✅ Bundled successfully"
        
        # Run openapi-generator-cli validate on bundled spec
        echo "  🔍 Validating with OpenAPI Generator..."
        if openapi-generator-cli validate -i "$BUNDLED_SPEC" 2>&1 | tee /tmp/openapi-generator-output.log; then
            # Check if there are any errors in the output
            if grep -q "\[error\]" /tmp/openapi-generator-output.log; then
                echo "  ❌ Failed: Validation errors found"
                VALIDATION_FAILED=1
                FAILED_FILES+=("$filename")
            else
                echo "  ✅ Passed"
            fi
        else
            echo "  ❌ Failed: Validation command failed"
            VALIDATION_FAILED=1
            FAILED_FILES+=("$filename")
        fi
    else
        echo "  ❌ Failed: Could not bundle spec"
        VALIDATION_FAILED=1
        FAILED_FILES+=("$filename")
    fi
    
    # Cleanup temp directory
    rm -rf "$TEMP_DIR"
    echo ""
done <<< "$SPEC_FILES"

# Summary
echo "=== Validation Summary ==="
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo "✅ All OpenAPI specs are valid!"
    echo ""
    echo "OpenAPI Generator validation passed:"
    echo "  - Schema structure validated"
    echo "  - OpenAPI 3.0 compliance verified"
    echo "  - Reference integrity checked"
    echo "  - Generator compatibility confirmed"
    echo ""
    exit 0
else
    echo "❌ OpenAPI Generator validation failed"
    echo ""
    echo "Failed files:"
    for file in "${FAILED_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "Common issues:"
    echo "  - Invalid schema definitions"
    echo "  - Broken \$ref references"
    echo "  - Missing required fields"
    echo "  - Invalid OpenAPI 3.0 syntax"
    echo ""
    echo "Run validation on individual files for detailed errors:"
    echo "  openapi-generator-cli validate -i <spec-file>"
    echo ""
    exit 1
fi
