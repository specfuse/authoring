#!/bin/bash
# Bundle AsyncAPI Specification Script (Mac/Linux)
# Usage: ./scripts/bundle-async-spec.sh [input-spec] [output-spec]
# Example: ./scripts/bundle-async-spec.sh api/specs/v1/asyncapi.yaml output/asyncapi-bundled.yaml
#
# If no arguments provided, uses defaults:
#   input-spec:  api/specs/v1/asyncapi.yaml
#   output-spec: output/asyncapi-bundled.yaml

set -e

# Set default values
DEFAULT_INPUT="api/specs/v1/asyncapi.yaml"
DEFAULT_OUTPUT="output/asyncapi-bundled.yaml"

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
else
    echo "❌ Error: Failed to bundle async spec"
    exit 1
fi

# Post-bundle dedup: each operation's `channel` $ref expands to the entire
# channel inline (with its messages map), inflating the bundle ~40×. Replace
# those inlines with slim metadata-only inlines so the bundle stays under
# Specfuse's 50MB YAML parse limit. Once Specfuse follows in-document
# `#/channels/<id>` refs natively, this pass becomes redundant.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if ! python3 "$SCRIPT_DIR/dedupe-async-bundle.py" "$OUTPUT_SPEC"; then
    echo "❌ Error: post-bundle dedup failed"
    exit 1
fi

exit 0
