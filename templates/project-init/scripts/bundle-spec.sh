#!/bin/bash
# Bundle OpenAPI Specification Script (Mac/Linux)
# Usage: ./scripts/bundle-spec.sh [input-spec] [output-spec]
# Example: ./scripts/bundle-spec.sh api/specs/v1/openapi.yaml output/openapi-bundled.yaml
#
# If no arguments provided, uses defaults:
#   input-spec:  api/specs/v1/openapi.yaml
#   output-spec: output/openapi-bundled.yaml

set -e

# Set default values
DEFAULT_INPUT="api/specs/v1/openapi.yaml"
DEFAULT_OUTPUT="output/openapi-bundled.yaml"

# Use provided arguments or defaults
INPUT_SPEC="${1:-$DEFAULT_INPUT}"
OUTPUT_SPEC="${2:-$DEFAULT_OUTPUT}"

# Check if input spec exists
if [ ! -f "$INPUT_SPEC" ]; then
    echo "❌ Error: Input spec file not found: $INPUT_SPEC"
    exit 1
fi

# Check if redocly is installed
if ! command -v redocly &> /dev/null; then
    echo "❌ Error: redocly is not installed"
    echo ""
    echo "Please install it first:"
    echo "  npm install -g @redocly/cli"
    echo ""
    echo "Or install manually:"
    echo "  npm install -g @redocly/cli"
    echo ""
    exit 1
fi

# Create output directory if it doesn't exist
OUTPUT_DIR=$(dirname "$OUTPUT_SPEC")
mkdir -p "$OUTPUT_DIR"

# Bundle the spec (without dereferencing to preserve $ref)
if redocly bundle "$INPUT_SPEC" --output "$OUTPUT_SPEC" 2>&1 | grep -q "Created a bundle"; then
    echo "✅ Bundled: $INPUT_SPEC -> $OUTPUT_SPEC"
    exit 0
else
    echo "❌ Error: Failed to bundle spec"
    exit 1
fi
