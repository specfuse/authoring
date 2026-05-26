#!/usr/bin/env bash
#
# init.sh — Bootstrap a new Specfuse project from this kit's template.
#
# Usage:
#   ./init.sh <target-directory>                Initialize a new project
#   ./init.sh --refresh-assets <target-dir>     Re-copy kit's claude-assets into an existing project
#
# See README.md in this directory for what gets created.

set -euo pipefail

# --- Parse args ---------------------------------------------------------------

REFRESH_ASSETS=false
TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --refresh-assets)
      REFRESH_ASSETS=true
      shift
      ;;
    -h|--help)
      grep -E '^# ' "$0" | head -10
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
    *)
      if [[ -z "$TARGET" ]]; then
        TARGET="$1"
      else
        echo "Multiple target directories specified." >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 <target-directory>" >&2
  echo "       $0 --refresh-assets <existing-project-directory>" >&2
  exit 1
fi

# Resolve kit root (assume this script lives at <kit>/templates/project-init/init.sh)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ ! -d "$KIT_ROOT/claude-assets/agents" ]] || [[ ! -d "$KIT_ROOT/claude-assets/commands" ]]; then
  echo "Error: cannot find kit's claude-assets at $KIT_ROOT/claude-assets/" >&2
  echo "       Is this script being run from the correct location inside the kit?" >&2
  exit 1
fi

# --- Refresh-assets mode ------------------------------------------------------

copy_claude_assets() {
  local target="$1"
  mkdir -p "$target/.claude/agents" "$target/.claude/commands"
  cp "$KIT_ROOT/claude-assets/agents/"*.md "$target/.claude/agents/"
  cp "$KIT_ROOT/claude-assets/commands/"*.md "$target/.claude/commands/"
}

if [[ "$REFRESH_ASSETS" == "true" ]]; then
  if [[ ! -d "$TARGET" ]]; then
    echo "Error: target directory does not exist: $TARGET" >&2
    exit 1
  fi
  echo "Refreshing claude-assets in: $TARGET"
  copy_claude_assets "$TARGET"
  echo "✓ Refreshed .claude/agents/ and .claude/commands/ from $KIT_ROOT/claude-assets/"
  exit 0
fi

# --- New-project mode ---------------------------------------------------------

if [[ -e "$TARGET" && ! -d "$TARGET" ]]; then
  echo "Error: $TARGET exists and is not a directory." >&2
  exit 1
fi

if [[ -d "$TARGET" ]] && [[ -n "$(ls -A "$TARGET" 2>/dev/null || true)" ]]; then
  read -rp "Target directory $TARGET is not empty. Continue and overwrite? [y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

echo ""
echo "Bootstrapping Specfuse project."
echo "  Kit:    $KIT_ROOT"
echo "  Target: $TARGET"
echo ""

# Prompt for project metadata
read -rp "Project name (kebab-case, e.g. my-app): " PROJECT_NAME
if [[ ! "$PROJECT_NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "Error: project name must be kebab-case (lowercase letters, digits, hyphens; must start with a letter)." >&2
  exit 1
fi

read -rp "Project token for channel addresses (lowercase, no dots, e.g. myapp): " PROJECT_TOKEN
if [[ ! "$PROJECT_TOKEN" =~ ^[a-z][a-z0-9]*$ ]]; then
  echo "Error: project token must be lowercase letters and digits only (no hyphens, no dots)." >&2
  exit 1
fi

read -rp "Initial domain name (kebab-case, e.g. order): " INITIAL_DOMAIN
if [[ ! "$INITIAL_DOMAIN" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "Error: domain name must be kebab-case." >&2
  exit 1
fi

mkdir -p "$TARGET"
TARGET_ABS="$(cd "$TARGET" && pwd)"

# Copy the template tree (everything except this script itself and the README)
cd "$SCRIPT_DIR"
find . -type f \
  ! -name 'init.sh' \
  ! -name 'README.md' \
  | while read -r src; do
    dest="$TARGET_ABS/${src#./}"
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
  done

# Rename the initial domain folder
if [[ -d "$TARGET_ABS/api/specs/v1/domains/{initial-domain}" ]]; then
  mv "$TARGET_ABS/api/specs/v1/domains/{initial-domain}" \
     "$TARGET_ABS/api/specs/v1/domains/$INITIAL_DOMAIN"
fi

# Process .template files: strip suffix and substitute placeholders
find "$TARGET_ABS" -type f -name '*.template' | while read -r template_file; do
  output_file="${template_file%.template}"
  sed -e "s/{ProjectName}/$PROJECT_NAME/g" \
      -e "s/{project}/$PROJECT_TOKEN/g" \
      -e "s/{initial-domain}/$INITIAL_DOMAIN/g" \
      "$template_file" > "$output_file"
  rm "$template_file"
done

# Rename the project config file to use the actual project name
if [[ -f "$TARGET_ABS/{project-name}-project.json" ]]; then
  mv "$TARGET_ABS/{project-name}-project.json" \
     "$TARGET_ABS/${PROJECT_NAME}-project.json"
fi

# Copy claude-assets
echo ""
echo "Copying claude-assets..."
copy_claude_assets "$TARGET_ABS"

echo ""
echo "✓ Project bootstrapped at $TARGET_ABS"
echo ""
echo "  Next steps:"
echo "    cd $TARGET_ABS"
echo "    git init && git add . && git commit -m 'Initial bootstrap from spec-authoring-kit'"
echo ""
echo "  Then read CLAUDE.md and start designing with /design-scenario or /design-async."
echo "  When the kit ships updates, refresh agents/commands with:"
echo "    $SCRIPT_DIR/init.sh --refresh-assets $TARGET_ABS"
