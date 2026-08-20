#!/bin/bash
# =============================================================================
# AsyncAPI Documentation Server
# =============================================================================
#
# Serves the AsyncAPI specification using AsyncAPI Studio with live reloading
# Usage: ./scripts/specfuse/serve-async-docs.sh [port]
# Default port: 8082
#
# Prerequisites:
#   npm install -g @asyncapi/cli

set -e

# Configuration
DEFAULT_PORT=8082
SPEC_FILE="api/specs/v1/asyncapi.yaml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse command line arguments
PORT=${1:-$DEFAULT_PORT}

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
    echo "❌ Error: Port must be a number between 1024 and 65535"
    echo "Usage: $0 [port]"
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

# Check if spec file exists
if [ ! -f "$SPEC_FILE" ]; then
    echo "❌ Error: AsyncAPI spec file not found: $SPEC_FILE"
    echo "Make sure you're running this from the project root or the spec file exists."
    exit 1
fi

# Check if asyncapi CLI is installed
if command -v asyncapi &> /dev/null; then
    ASYNCAPI_CMD="asyncapi"
elif [ -f "node_modules/.bin/asyncapi" ]; then
    ASYNCAPI_CMD="./node_modules/.bin/asyncapi"
else
    echo "❌ Error: AsyncAPI CLI not found"
    echo ""
    echo "Please install AsyncAPI CLI:"
    echo "  npm install -g @asyncapi/cli"
    echo ""
    echo "Or install locally:"
    echo "  npm install @asyncapi/cli"
    echo ""
    exit 1
fi

# Bundle the spec first for preview
echo "📦 Bundling AsyncAPI spec for preview..."
BUNDLED_SPEC="output/asyncapi-bundled.yaml"
mkdir -p output
if "$SCRIPT_DIR/bundle-async-spec.sh" "$SPEC_FILE" "$BUNDLED_SPEC" > /dev/null 2>&1; then
    echo "✅ Bundled spec ready"
else
    echo "⚠️  Bundle failed, using unbundled spec for preview"
    BUNDLED_SPEC="$SPEC_FILE"
fi

# Display startup information
echo ""
echo "🚀 Starting AsyncAPI Documentation Server"
echo "📄 Spec file: $SPEC_FILE"
echo "🌐 Port: $PORT"
echo "📍 URL: http://localhost:$PORT"
echo ""
echo "💡 Press Ctrl+C to stop the server"
echo ""

# Start AsyncAPI Studio
echo "Starting AsyncAPI Studio..."
$ASYNCAPI_CMD start studio --file "$BUNDLED_SPEC" --port "$PORT"
