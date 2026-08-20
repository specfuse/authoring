#!/bin/bash

# =============================================================================
# API Documentation Server
# =============================================================================
# 
# Serves the OpenAPI v3 specification using Redocly with live reloading
# Usage: ./scripts/specfuse/serve-docs.sh [port]
# Default port: 8081

set -e

# Configuration
DEFAULT_PORT=8081
SPEC_FILE="api/specs/v1/openapi.yaml"
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
    echo "❌ Error: OpenAPI spec file not found: $SPEC_FILE"
    echo "Make sure you're running this from the project root or the spec file exists."
    exit 1
fi

# Check if redocly is installed (global or local)
REDOCLY_CMD=""
if command -v redocly &> /dev/null; then
    REDOCLY_CMD="redocly"
elif [ -f "node_modules/.bin/redocly" ]; then
    REDOCLY_CMD="./node_modules/.bin/redocly"
else
    echo "❌ Error: Redocly CLI not found"
    echo ""
    echo "Please install Redocly CLI:"
    echo "  Global: npm install -g @redocly/cli"
    echo "  Local:  npm install (uses package.json)"
    echo ""
    echo "Or using yarn:"
    echo "  Global: yarn global add @redocly/cli"
    echo "  Local:  yarn install"
    exit 1
fi

# Display startup information
echo "🚀 Starting API Documentation Server"
echo "📄 Spec file: $SPEC_FILE"
echo "🌐 Port: $PORT"
echo "📍 URL: http://localhost:$PORT"
echo ""
echo "💡 The server will automatically reload when you make changes to the spec files"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

# Start the Redocly server
echo "Starting Redocly server..."

# Use the newer 'preview' command for Redocly 2.x
if $REDOCLY_CMD preview --help 2>/dev/null | grep -q "product"; then
    echo "📡 Using preview command with Redocly 2.x"
    $REDOCLY_CMD preview \
        --port "$PORT" \
        --project-dir "api/specs/v1"
else
    # Fallback for older versions that used preview-docs
    echo "⚠️  Using legacy preview-docs command"
    echo "💡 Consider updating Redocly CLI"
    $REDOCLY_CMD preview-docs "$SPEC_FILE" \
        --port "$PORT" \
        --host "0.0.0.0"
fi