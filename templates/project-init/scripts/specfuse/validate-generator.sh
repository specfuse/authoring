#!/bin/bash
# SpecFuse Generator Validation (Mac/Linux)
# Usage: ./scripts/specfuse/validate-generator.sh
#
# Single entrypoint for ALL generator-side validation. The generator's
# `validate <project.json>` runs the full OpenAPI DDD ruleset (aggregate
# boundaries, x-entity, value objects, operations) AND the AsyncAPI cross-spec
# link rules (ASYNC_*) in one pass — it is a strict superset of the old
# per-spec `validate --spec`, which is why that call was dropped.
#
# Steps:
#   1. Bundle OpenAPI + AsyncAPI (project.json reads ./output/*-bundled.yaml)
#   2. validate-source on the un-bundled tree — catches path rules the bundler
#      erases (snapshot folder placement). Different subcommand, NOT covered by
#      project.json.
#   3. validate project.json — the unified OpenAPI + async cross-spec gate.
#
# Trusts the generator's exit code: non-zero = must-fix errors.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# The generator is resolved and checksum-verified by the kit CLI against the
# version pinned in generator.lock; there is no jar to keep beside this script.
# The suite is driven through the single `specfuse` command. The flat
# `specfuse-authoring` script is a deprecated alias, kept working for standalone
# installs until 1.0.0 — so prefer the subcommand, fall back to the alias, and
# let SPECFUSE_AUTHORING override either (it may name a full path).
if [ -n "${SPECFUSE_AUTHORING:-}" ]; then
    SPECFUSE_CLI=("${SPECFUSE_AUTHORING}")
elif command -v specfuse &> /dev/null; then
    SPECFUSE_CLI=(specfuse authoring)
else
    SPECFUSE_CLI=(specfuse-authoring)
fi
# `specfuse authoring generate` runs the PINNED GENERATOR JAR with whatever
# follows it, so the jar's own verb (generate / validate / validate-source) is
# passed explicitly as the first argument below. Dropping it silently runs the
# jar with no subcommand.
RUN_GENERATOR=("${SPECFUSE_CLI[@]}" generate)

# The project file is named after the project, so find it rather than
# hardcoding one project's name.
PROJECT_CONFIG=""
for candidate in "$PROJECT_ROOT"/*-project.json; do
    if [ -f "$candidate" ]; then
        PROJECT_CONFIG="$candidate"
        break
    fi
done

# Follow the project's spec version rather than assuming one.
VERSION=${1:-"latest"}
if [ "$VERSION" = "latest" ]; then
    LATEST_VERSION=$(ls -d "$PROJECT_ROOT/api/specs/v"* 2>/dev/null | sort -V | tail -n 1 | xargs basename 2>/dev/null)
    if [ -n "$LATEST_VERSION" ]; then
        VERSION=$LATEST_VERSION
    fi
fi
SOURCE_ROOT="$PROJECT_ROOT/api/specs/$VERSION"
OPENAPI_SPEC="$SOURCE_ROOT/openapi.yaml"
ASYNC_SPEC="$SOURCE_ROOT/asyncapi.yaml"
OPENAPI_BUNDLE="$PROJECT_ROOT/output/openapi-bundled.yaml"
ASYNC_BUNDLE="$PROJECT_ROOT/output/asyncapi-bundled.yaml"

if ! command -v java &> /dev/null; then
    echo "❌ Java not found. Install Java 21+."
    exit 1
fi
if ! command -v "${SPECFUSE_CLI[0]}" &> /dev/null; then
    echo "❌ ${SPECFUSE_CLI[*]} not found on PATH."
    echo "   Install the suite:  pipx install specfuse   (or: uv tool install specfuse)"
    exit 1
fi
if [ -z "$PROJECT_CONFIG" ] || [ ! -f "$PROJECT_CONFIG" ]; then
    echo "❌ Project file not found: expected <name>-project.json in $PROJECT_ROOT"
    exit 1
fi

cd "$PROJECT_ROOT"

echo "=== SpecFuse Generator Validation ==="
echo "Project: $PROJECT_CONFIG"
echo ""

# Step 1 — bundle both specs (project.json references the bundled outputs)
echo "📦 Bundling OpenAPI + AsyncAPI specs..."
"$SCRIPT_DIR/bundle-spec.sh" "$OPENAPI_SPEC" "$OPENAPI_BUNDLE" > /dev/null
"$SCRIPT_DIR/bundle-async-spec.sh" "$ASYNC_SPEC" "$ASYNC_BUNDLE" > /dev/null
echo "  ✅ Bundled"
echo ""

# Step 2 — source-tree rules (un-bundled; catches what bundling erases)
echo "🔍 Source-tree validation (validate-source)..."
"${RUN_GENERATOR[@]}" validate-source "$SOURCE_ROOT"
echo "  ✅ Source-tree passed"
echo ""

# Step 3 — unified OpenAPI + async cross-spec gate
echo "🔍 Project validation (validate project.json)..."
"${RUN_GENERATOR[@]}" validate --ai-agent "$PROJECT_CONFIG" --overflow-summary
echo ""
echo "✅ Generator validation passed."
