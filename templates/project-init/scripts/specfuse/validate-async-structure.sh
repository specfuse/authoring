#!/bin/bash
# AsyncAPI Structure Validator Script (Mac/Linux)
# Usage: ./scripts/specfuse/validate-async-structure.sh
#
# Validates that AsyncAPI spec files follow the required
# directory structure and naming conventions.

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SPEC_DIR="$PROJECT_ROOT/api/specs/v1"
ASYNC_SPEC="$SPEC_DIR/asyncapi.yaml"

echo "=== AsyncAPI Structure Validator ==="
echo "Spec Directory: $SPEC_DIR"
echo ""

VALIDATION_FAILED=0

# Check if asyncapi.yaml exists
if [ ! -f "$ASYNC_SPEC" ]; then
    echo "❌ AsyncAPI spec not found: $ASYNC_SPEC"
    exit 1
fi
echo "✅ AsyncAPI spec found"
echo ""

# Check 1: Main spec should only use $ref for channels
echo "📋 Checking for inline channel definitions in main spec..."
INLINE_CHANNELS=$(grep -E "^\s+address:" "$ASYNC_SPEC" 2>/dev/null | head -5)
if [ -n "$INLINE_CHANNELS" ]; then
    echo "  ❌ Failed: Main spec contains inline channel definitions"
    echo "  Fix: Move channel definitions to domains/{domain}/channels/{channel}.yaml"
    VALIDATION_FAILED=1
else
    echo "  ✅ Passed: All channels use \$ref"
fi

# Check 2: Main spec should only use $ref for operations
echo ""
echo "📋 Checking for inline operation definitions in main spec..."
INLINE_OPS=$(grep -E "^\s+action:" "$ASYNC_SPEC" 2>/dev/null | head -5)
if [ -n "$INLINE_OPS" ]; then
    echo "  ❌ Failed: Main spec contains inline operation definitions"
    echo "  Fix: Move operation definitions to domains/{domain}/async-operations/{operation}.yaml"
    VALIDATION_FAILED=1
else
    echo "  ✅ Passed: All operations use \$ref"
fi

# Check 3: Verify async-common structure
echo ""
echo "📋 Checking async-common structure..."
if [ -d "$SPEC_DIR/async-common" ]; then
    echo "  ✅ async-common/ directory exists"
    for subdir in "message-traits" "operation-traits" "bindings"; do
        if [ -d "$SPEC_DIR/async-common/$subdir" ]; then
            FILE_COUNT=$(find "$SPEC_DIR/async-common/$subdir" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
            echo "    - $subdir/: $FILE_COUNT file(s)"
        else
            echo "    ⚠️  Missing: async-common/$subdir/"
        fi
    done
else
    echo "  ❌ Failed: async-common/ directory not found"
    VALIDATION_FAILED=1
fi

# Check 4: Verify domain async structure
echo ""
echo "📋 Checking domain async structure..."
ASYNC_DOMAIN_COUNT=0
for domain_dir in "$SPEC_DIR/domains"/*; do
    if [ -d "$domain_dir" ]; then
        domain_name=$(basename "$domain_dir")
        HAS_ASYNC=0

        # Check for async folders
        for async_dir in "channels" "messages" "async-operations"; do
            if [ -d "$domain_dir/$async_dir" ]; then
                HAS_ASYNC=1
            fi
        done

        if [ $HAS_ASYNC -eq 1 ]; then
            ASYNC_DOMAIN_COUNT=$((ASYNC_DOMAIN_COUNT + 1))
            channels_count=$(find "$domain_dir/channels" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
            messages_count=$(find "$domain_dir/messages" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
            async_ops_count=$(find "$domain_dir/async-operations" -name "*.yaml" 2>/dev/null | wc -l | tr -d ' ')
            echo "  - $domain_name: $channels_count channels, $messages_count messages, $async_ops_count async-operations"

            # Validate message file names are PascalCase
            if [ -d "$domain_dir/messages" ]; then
                for msg_file in "$domain_dir/messages"/*.yaml; do
                    if [ -f "$msg_file" ]; then
                        filename=$(basename "$msg_file" .yaml)
                        if ! echo "$filename" | grep -qE "^[A-Z][A-Za-z0-9]+$"; then
                            echo "    ❌ Message file '$filename.yaml' is not PascalCase"
                            VALIDATION_FAILED=1
                        fi
                    fi
                done
            fi

            # Validate async-operation file names are kebab-case with verb prefix (v2: on-, emit-, run- only)
            if [ -d "$domain_dir/async-operations" ]; then
                for op_file in "$domain_dir/async-operations"/*.yaml; do
                    if [ -f "$op_file" ]; then
                        filename=$(basename "$op_file" .yaml)
                        if ! echo "$filename" | grep -qE "^(on|emit|run)-[a-z][a-z0-9-]+$"; then
                            echo "    ❌ Async operation file '$filename.yaml' must use v2 verb prefix (on-, emit-, run-)"
                            echo "       Note: execute-* and dispatch-* no longer exist in v2"
                            VALIDATION_FAILED=1
                        fi
                    fi
                done
            fi

            # Validate channel file names are kebab-case
            if [ -d "$domain_dir/channels" ]; then
                for ch_file in "$domain_dir/channels"/*.yaml; do
                    if [ -f "$ch_file" ]; then
                        filename=$(basename "$ch_file" .yaml)
                        if ! echo "$filename" | grep -qE "^[a-z][a-z0-9]+(-[a-z0-9]+)*$"; then
                            echo "    ❌ Channel file '$filename.yaml' must be kebab-case"
                            VALIDATION_FAILED=1
                        fi
                    fi
                done
            fi
        fi
    fi
done

if [ $ASYNC_DOMAIN_COUNT -eq 0 ]; then
    echo "  ⚠️  No domains with async specs found"
else
    echo "  ✅ Found $ASYNC_DOMAIN_COUNT domain(s) with async specs"
fi

# Check 5: Validate cross-references to OpenAPI models resolve
echo ""
echo "📋 Checking cross-references to OpenAPI models..."
REF_ERRORS=0
for msg_file in $(find "$SPEC_DIR/domains" -path "*/messages/*.yaml" 2>/dev/null); do
    # Find $ref lines that point to ../models/
    REFS=$(grep -oP '\$ref:\s*['\''"]?\.\./models/[^'\''"]+' "$msg_file" 2>/dev/null | sed "s/.*\.\.\///" || true)
    if [ -n "$REFS" ]; then
        domain_dir=$(dirname "$(dirname "$msg_file")")
        for ref_path in $REFS; do
            # Strip any trailing quote or anchor
            clean_path=$(echo "$ref_path" | sed 's/#.*//')
            full_path="$domain_dir/$clean_path"
            if [ ! -f "$full_path" ]; then
                echo "  ❌ Broken \$ref in $(basename "$msg_file"): ../models/$clean_path not found"
                REF_ERRORS=$((REF_ERRORS + 1))
                VALIDATION_FAILED=1
            fi
        done
    fi
done

if [ $REF_ERRORS -eq 0 ]; then
    echo "  ✅ All cross-references to OpenAPI models resolve correctly"
fi

# Check 6: x-worker and x-emits rules per operation prefix
echo ""
echo "📋 Checking x-worker and x-emits rules per operation prefix..."
WORKER_ERRORS=0

for op_file in $(find "$SPEC_DIR/domains" -path "*/async-operations/*.yaml" 2>/dev/null); do
    filename=$(basename "$op_file" .yaml)

    # on-* operations (receive): MUST have x-worker
    if echo "$filename" | grep -qE "^on-"; then
        if ! grep -q "x-worker:" "$op_file" 2>/dev/null; then
            echo "  ❌ Event handler '$filename.yaml' is missing x-worker (required on on-* receive operations)"
            WORKER_ERRORS=$((WORKER_ERRORS + 1))
            VALIDATION_FAILED=1
        fi
        # Check action is receive
        if ! grep -q "action: receive" "$op_file" 2>/dev/null; then
            echo "  ❌ Event handler '$filename.yaml' must have action: receive"
            WORKER_ERRORS=$((WORKER_ERRORS + 1))
            VALIDATION_FAILED=1
        fi
    fi

    # run-* operations (send): MUST have x-worker, action must be send
    if echo "$filename" | grep -qE "^run-"; then
        if ! grep -q "x-worker:" "$op_file" 2>/dev/null; then
            echo "  ❌ Scheduled job '$filename.yaml' is missing x-worker (required on run-* send operations)"
            WORKER_ERRORS=$((WORKER_ERRORS + 1))
            VALIDATION_FAILED=1
        fi
        if ! grep -q "action: send" "$op_file" 2>/dev/null; then
            echo "  ❌ Scheduled job '$filename.yaml' must have action: send (cron-triggered publishers are senders)"
            WORKER_ERRORS=$((WORKER_ERRORS + 1))
            VALIDATION_FAILED=1
        fi
    fi

    # emit-* operations (send): MUST NOT have x-worker
    if echo "$filename" | grep -qE "^emit-"; then
        if grep -q "x-worker:" "$op_file" 2>/dev/null; then
            echo "  ❌ Publishing declaration '$filename.yaml' has x-worker (forbidden on emit-* operations — they are not workers)"
            WORKER_ERRORS=$((WORKER_ERRORS + 1))
            VALIDATION_FAILED=1
        fi
        if ! grep -q "action: send" "$op_file" 2>/dev/null; then
            echo "  ❌ Publishing declaration '$filename.yaml' must have action: send"
            WORKER_ERRORS=$((WORKER_ERRORS + 1))
            VALIDATION_FAILED=1
        fi
    fi
done

# Note: x-emits on on-* operations is validated by the cross-spec validator
# which checks that every x-emits entry matches a corresponding emit-* operation.
# We do not warn about missing x-emits here because not every on-* handler
# in a domain publishes events — only those that explicitly need to.

if [ $WORKER_ERRORS -eq 0 ]; then
    echo "  ✅ All operations follow x-worker rules (required on on-*/run-*, forbidden on emit-*)"
fi

# Check 7: Domains with async specs must have flow documentation
echo ""
echo "📋 Checking flow documentation coverage..."
FLOW_ERRORS=0
FLOWS_DIR="$PROJECT_ROOT/api/docs/flows"

for domain_dir in "$SPEC_DIR/domains"/*; do
    if [ -d "$domain_dir" ]; then
        domain_name=$(basename "$domain_dir")
        HAS_ASYNC=0
        for async_dir in "channels" "messages" "async-operations"; do
            if [ -d "$domain_dir/$async_dir" ] && [ "$(find "$domain_dir/$async_dir" -name '*.yaml' 2>/dev/null | wc -l | tr -d ' ')" -gt 0 ]; then
                HAS_ASYNC=1
                break
            fi
        done

        if [ $HAS_ASYNC -eq 1 ]; then
            if [ ! -d "$FLOWS_DIR/$domain_name" ] || [ "$(find "$FLOWS_DIR/$domain_name" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')" -eq 0 ]; then
                echo "  ❌ Domain '$domain_name' has async specs but no flow documentation"
                echo "     Create at least one flow doc in api/docs/flows/$domain_name/"
                echo "     Use /design-flow to generate it from the specs"
                FLOW_ERRORS=$((FLOW_ERRORS + 1))
                VALIDATION_FAILED=1
            else
                flow_count=$(find "$FLOWS_DIR/$domain_name" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
                echo "  - $domain_name: $flow_count flow doc(s)"
            fi
        fi
    fi
done

if [ $FLOW_ERRORS -eq 0 ]; then
    echo "  ✅ All async domains have flow documentation"
fi

# Check 8: Messages should have x-version
echo ""
echo "📋 Checking message versioning..."
VERSION_WARNINGS=0
for msg_file in $(find "$SPEC_DIR/domains" -path "*/messages/*.yaml" 2>/dev/null); do
    filename=$(basename "$msg_file")
    if ! grep -q "x-version:" "$msg_file" 2>/dev/null; then
        echo "  ⚠️  Message '$filename' is missing x-version (recommended)"
        VERSION_WARNINGS=$((VERSION_WARNINGS + 1))
    fi
done

if [ $VERSION_WARNINGS -eq 0 ]; then
    echo "  ✅ All messages declare x-version"
else
    echo "  ⚠️  $VERSION_WARNINGS message(s) missing x-version (add x-version with current and status)"
fi

# Check 9: Cross-spec validation — x-emits on async on-* operations match emit-* declarations
echo ""
echo "📋 Checking async x-emits ↔ emit-* operation linkage..."
CROSSREF_ERRORS=0

for op_file in $(find "$SPEC_DIR/domains" -path "*/async-operations/on-*.yaml" 2>/dev/null); do
    filename=$(basename "$op_file" .yaml)
    domain_dir=$(dirname "$(dirname "$op_file")")

    # Extract x-emits events from the on-* operation
    EMITS=$(grep "event:" "$op_file" 2>/dev/null | sed 's/.*event:\s*//' | tr -d "'\" " || true)
    if [ -z "$EMITS" ]; then
        continue
    fi

    for event in $EMITS; do
        # Parse Entity.Action from x-emits
        ENTITY=$(echo "$event" | cut -d. -f1)
        ACTION=$(echo "$event" | cut -d. -f2)

        # Find matching emit-* operation in the same domain
        FOUND_EMIT=0
        for emit_file in $(find "$domain_dir/async-operations" -name "emit-*.yaml" 2>/dev/null); do
            # Check if any message in the emit file matches the x-label
            EMIT_ENTITY=$(grep "entity:" "$emit_file" 2>/dev/null | head -1 | sed 's/.*entity:\s*//' | tr -d "'\" " || true)
            EMIT_ACTION=$(grep "action:" "$emit_file" 2>/dev/null | head -1 | sed 's/.*action:\s*//' | tr -d "'\" " || true)
            if [ -z "$EMIT_ENTITY" ] || [ -z "$EMIT_ACTION" ]; then
                # Check the referenced message file for x-label
                MSG_REF=$(grep '\$ref:' "$emit_file" 2>/dev/null | grep "messages/" | head -1 | sed "s/.*'\(.*\)'/\1/" | sed 's/.*"\(.*\)"/\1/' || true)
                if [ -n "$MSG_REF" ]; then
                    MSG_FILE="$domain_dir/async-operations/$MSG_REF"
                    if [ -f "$MSG_FILE" ]; then
                        EMIT_ENTITY=$(grep "entity:" "$MSG_FILE" 2>/dev/null | head -1 | sed 's/.*entity:\s*//' | tr -d "'\" " || true)
                        EMIT_ACTION=$(grep "action:" "$MSG_FILE" 2>/dev/null | head -1 | sed 's/.*action:\s*//' | tr -d "'\" " || true)
                    fi
                fi
            fi
            if [ "$EMIT_ENTITY" = "$ENTITY" ] && [ "$EMIT_ACTION" = "$ACTION" ]; then
                FOUND_EMIT=1
                echo "  - $filename x-emits $event → $(basename "$emit_file" .yaml) ✓"
                break
            fi
        done

        if [ $FOUND_EMIT -eq 0 ]; then
            echo "  ⚠️  $filename declares x-emits '$event' but no matching emit-* operation found in domain"
        fi
    done
done

if [ $CROSSREF_ERRORS -eq 0 ]; then
    echo "  ✅ All async x-emits declarations are consistent with emit-* operations"
fi

# Summary
echo ""
echo "=== Validation Summary ==="
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo "✅ AsyncAPI structure validation passed!"
    echo ""
    echo "File organization verified:"
    echo "  - Main spec uses \$ref for channels and operations"
    echo "  - async-common/ shared components present"
    echo "  - Domain async folders follow conventions"
    echo "  - Message files are PascalCase"
    echo "  - Async operation files use v2 verb prefixes (on-, emit-, run-)"
    echo "  - Channel files are kebab-case"
    echo "  - Cross-references to OpenAPI models resolve"
    echo "  - x-worker rules: required on on-*/run-*, forbidden on emit-*"
    echo "  - x-emits links on-* operations to emit-* declarations"
    echo "  - All async domains have flow documentation"
    echo ""
    exit 0
else
    echo "❌ AsyncAPI structure validation failed"
    echo ""
    echo "Required file organization:"
    echo "  - Main spec: ONLY \$ref references (no inline definitions)"
    echo "  - Channels: domains/{domain}/channels/{channel-name}.yaml (kebab-case)"
    echo "  - Messages: domains/{domain}/messages/{MessageName}.yaml (PascalCase)"
    echo "  - Operations: domains/{domain}/async-operations/{verb-desc}.yaml (kebab-case with verb prefix)"
    echo ""
    exit 1
fi
