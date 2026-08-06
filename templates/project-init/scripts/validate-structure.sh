#!/bin/bash
# OpenAPI Structure Validator Script (Mac/Linux)
# Usage: ./scripts/validate-structure.sh [version]
# Example: ./scripts/validate-structure.sh v1

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

echo "=== OpenAPI Structure Validator (Mac/Linux) ==="
echo "Version: $VERSION"
echo "Spec Directory: $SPEC_DIR"
echo ""

# Check if spec directory exists
if [ ! -d "$SPEC_DIR" ]; then
    echo "❌ Spec directory not found: $SPEC_DIR"
    exit 1
fi

# Find main spec file (common names)
MAIN_SPEC=""
for candidate in "openapi-specs.yaml" "openapi-spec.yaml" "openapi.yaml" "api.yaml"; do
    if [ -f "$SPEC_DIR/$candidate" ]; then
        MAIN_SPEC="$SPEC_DIR/$candidate"
        break
    fi
done

if [ -z "$MAIN_SPEC" ]; then
    echo "⚠️  No main spec file found (looked for: openapi-specs.yaml, openapi-spec.yaml, openapi.yaml, api.yaml)"
    echo "   Skipping structure validation"
    exit 0
fi

echo "✅ Main spec file: $(basename "$MAIN_SPEC")"
echo ""

# Validate file organization
echo "=== Validating File Organization ==="
echo ""

VALIDATION_FAILED=0

# Check 1: Main spec should not have inline schema definitions
echo "📋 Checking for inline schema definitions in main spec..."
if grep -A 3 "components:" "$MAIN_SPEC" | grep -E "^\s+[A-Z][a-zA-Z0-9]*:\s*$" | head -1 | grep -v "\$ref" > /dev/null 2>&1; then
    # Check if those schemas have inline definitions
    INLINE_SCHEMAS=$(awk '/components:/,/^[^ ]/ {
        if (/^\s+[A-Z][a-zA-Z0-9]*:\s*$/) {
            schema_name=$1
            getline
            if ($0 !~ /\$ref:/) {
                print schema_name
            }
        }
    }' "$MAIN_SPEC" | head -5)
    
    if [ -n "$INLINE_SCHEMAS" ]; then
        echo "  ❌ Failed: Main spec contains inline schema definitions"
        echo ""
        echo "  Found inline schemas:"
        echo "$INLINE_SCHEMAS" | sed 's/^/    - /'
        echo ""
        echo "  Fix: Move schema definitions to domain-specific files:"
        echo "    api/specs/$VERSION/domains/{domain}/models/{Schema}.yaml"
        echo ""
        VALIDATION_FAILED=1
    else
        echo "  ✅ Passed: All schemas use \$ref"
    fi
else
    echo "  ✅ Passed: No inline schema definitions found"
fi

# Check 2: Main spec paths should not have inline operation definitions
echo ""
echo "📋 Checking for inline operation definitions in main spec..."
INLINE_OPERATIONS=$(awk '/paths:/,/^components:/ {
    if (/^\s+\/[a-zA-Z0-9\/{}:-]+:\s*$/) {
        path=$1
        in_path=1
    }
    if (in_path && /^\s+(get|post|put|patch|delete):\s*$/) {
        method=$1
        getline
        if ($0 !~ /\$ref:/) {
            if (NR > 0) print path " " method
            found=1
        }
        in_path=0
    }
}' "$MAIN_SPEC" | head -5)

if [ -n "$INLINE_OPERATIONS" ]; then
    echo "  ❌ Failed: Main spec contains inline operation definitions"
    echo ""
    echo "  Found inline operations:"
    echo "$INLINE_OPERATIONS" | sed 's/^/    - /'
    echo ""
    echo "  Fix: Move operation definitions to domain-specific files:"
    echo "    api/specs/$VERSION/domains/{domain}/operations/{operation-name}.yaml"
    echo ""
    VALIDATION_FAILED=1
else
    echo "  ✅ Passed: All operations use \$ref"
fi

# Check 3: Verify domain structure exists (if domains folder exists)
echo ""
if [ -d "$SPEC_DIR/domains" ]; then
    echo "📋 Checking domain structure..."
    DOMAIN_COUNT=$(find "$SPEC_DIR/domains" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$DOMAIN_COUNT" -gt 0 ]; then
        echo "  ✅ Found $DOMAIN_COUNT domain(s)"
        
        # List domains
        for domain_dir in "$SPEC_DIR/domains"/*; do
            if [ -d "$domain_dir" ]; then
                domain_name=$(basename "$domain_dir")
                models_count=$(find "$domain_dir/models" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
                ops_count=$(find "$domain_dir/operations" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
                echo "    - $domain_name: $models_count models, $ops_count operations"
            fi
        done
    else
        echo "  ⚠️  Warning: domains/ folder exists but is empty"
    fi
else
    echo "📋 No domains/ folder found - skipping domain structure check"
fi

# Summary
echo ""
echo "=== Validation Summary ==="
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo "✅ OpenAPI structure validation passed!"
    echo ""
    echo "File organization verified:"
    echo "  - Main spec uses \$ref for schemas"
    echo "  - Main spec uses \$ref for operations"
    echo "  - Domain-based file structure enforced"
    echo ""
    exit 0
else
    echo "❌ OpenAPI structure validation failed"
    echo ""
    echo "Required file organization:"
    echo "  - Main spec: ONLY \$ref references (no inline definitions)"
    echo "  - Schemas: domains/{domain}/models/{Schema}.yaml"
    echo "  - Operations: domains/{domain}/operations/{operation}.yaml"
    echo ""
    echo "Benefits:"
    echo "  - Enforces domain boundaries"
    echo "  - Enables parallel development"
    echo "  - Supports clean code generation"
    echo "  - Improves maintainability"
    echo ""
    exit 1
fi
