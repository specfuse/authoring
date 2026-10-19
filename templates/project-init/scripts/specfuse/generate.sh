#!/bin/bash
# SpecFuse Code Generation (Mac/Linux)
#
# Single entrypoint for generating the artifact groups declared in the project
# file (<name>-project.json). The generator's `--group` takes ONE name, so this
# bundles the specs once, then runs one generator invocation per group.
#
# Usage:
#   ./scripts/specfuse/generate.sh --list                 # groups, by language, with destinations
#   ./scripts/specfuse/generate.sh <group> [<group>...]   # one or more groups (case-insensitive)
#   ./scripts/specfuse/generate.sh --lang <language>      # every group of a language (repeatable)
#   ./scripts/specfuse/generate.sh all                    # every group (explicit opt-in)
#   ./scripts/specfuse/generate.sh <targets...> --dry-run # print what would run, generate nothing
#
# Other options:
#   --skip-validation   passed to the generator (it validates before generating by default)
#   --allow-dirty       generate into destination repos that have uncommitted changes
#   --spec-version vN   spec directory under api/specs/ (default: the newest)
#
# DESTRUCTIVE: a group whose `destination` is outside this repo (e.g.
# `../Backend/`) writes into another repo, and `cleanGenerated: true` deletes
# the group's generated tree before rewriting it. Before generating, this script
# refuses to touch a destination repo with uncommitted changes (override with
# --allow-dirty). Prefer naming groups over `all`.
#
# Post-generation hook: if the project has an executable `scripts/post-generate.sh`
# (project-owned, outside scripts/specfuse/), it runs once per generated group as
#   scripts/post-generate.sh <group> <language> <destination> <basePackage>
# from the project root. Use it for language steps the generator does not run,
# e.g. Dart's `dart run build_runner build`. A non-zero exit stops the run.
#
# Markdown groups generate like any other here. `generate-scenario-docs.sh` also
# adds cross-links and the scenario index on top, so prefer it for docs.
#
# The generator is the version `specfuse authoring generate` resolves: the
# project's `.specfuse/generator.lock` when present, otherwise the kit's pin.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -n "${SPECFUSE_AUTHORING:-}" ]; then
    SPECFUSE_CLI=("${SPECFUSE_AUTHORING}")
elif command -v specfuse &> /dev/null; then
    SPECFUSE_CLI=(specfuse authoring)
else
    SPECFUSE_CLI=(specfuse-authoring)
fi
# `specfuse authoring generate` runs the pinned generator with whatever follows
# it, so the generator's own verb is passed explicitly. Dropping it runs the
# generator with no command.
RUN_GENERATOR=("${SPECFUSE_CLI[@]}" generate)

die() { echo "❌ $1" >&2; exit 1; }

CONFIG=""
for candidate in "$ROOT_DIR"/*-project.json; do
    if [ -f "$candidate" ]; then
        CONFIG="$candidate"
        break
    fi
done
[ -n "$CONFIG" ] || die "Project file not found: expected <name>-project.json in $ROOT_DIR"
command -v python3 &> /dev/null || die "python3 not found (needed to read the project file)."

# groups_tsv — one line per group: name<TAB>language<TAB>destination<TAB>basePackage.
# python3 rather than jq: no extra dependency, and no CRLF output on Windows.
groups_tsv() {
    python3 - "$CONFIG" <<'PY'
import json, sys
for g in json.load(open(sys.argv[1], encoding="utf-8")).get("groups", []):
    print("\t".join(str(g.get(k) or "") for k in ("name", "language", "destination", "basePackage")))
PY
}
config_value() {
    python3 - "$CONFIG" "$1" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8")).get(sys.argv[2]) or "")
PY
}

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }

# Language aliases, matched case-insensitively against each group's `language`.
canon_lang() {
    case "$(lower "$1")" in
        c#|cs|csharp|dotnet) echo "c#" ;;
        py|python)           echo "python" ;;
        dart|flutter)        echo "dart" ;;
        ts|typescript)       echo "typescript" ;;
        md|markdown|docs)    echo "markdown" ;;
        *)                   lower "$1" ;;
    esac
}

usage() { sed -n '4,15p' "$0" | sed 's/^# \{0,1\}//'; }

TARGETS=()
GEN_ALL=false
DRY_RUN=false
ALLOW_DIRTY=false
SPEC_VERSION="latest"
PASSTHROUGH=()

add_target() {
    local t
    for t in ${TARGETS[@]+"${TARGETS[@]}"}; do
        [ "$t" = "$1" ] && return 0
    done
    TARGETS+=("$1")
}

[ $# -ge 1 ] || { usage; exit 1; }

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --list)
            echo "Groups in $(basename "$CONFIG"):"
            groups_tsv | sort -t$'\t' -k2,2 -s | while IFS=$'\t' read -r name lang dest _; do
                printf '  [%s] %s -> %s\n' "$lang" "$name" "${dest:-.}"
            done
            exit 0 ;;
        all) GEN_ALL=true ;;
        --lang|-l)
            shift; [ $# -ge 1 ] || die "--lang needs a value"
            want="$(canon_lang "$1")"
            found=0
            while IFS=$'\t' read -r name lang _ _; do
                if [ "$(canon_lang "$lang")" = "$want" ]; then
                    add_target "$name"; found=$((found + 1))
                fi
            done < <(groups_tsv)
            [ "$found" -gt 0 ] || die "No groups for language '$1'. See --list."
            ;;
        --skip-validation) PASSTHROUGH+=("$1") ;;
        --allow-dirty) ALLOW_DIRTY=true ;;
        --dry-run|-n) DRY_RUN=true ;;
        --spec-version) shift; [ $# -ge 1 ] || die "--spec-version needs a value"; SPEC_VERSION="$1" ;;
        -*) die "Unknown option: '$1' (see --help)" ;;
        *)
            match=""
            while IFS=$'\t' read -r name _ _ _; do
                if [ "$(lower "$name")" = "$(lower "$1")" ]; then match="$name"; break; fi
            done < <(groups_tsv)
            [ -n "$match" ] || die "Unknown group: '$1'. See --list."
            add_target "$match" ;;
    esac
    shift
done

if [ "$GEN_ALL" = true ]; then
    TARGETS=()
    while IFS=$'\t' read -r name _ _ _; do add_target "$name"; done < <(groups_tsv)
fi
[ ${#TARGETS[@]} -gt 0 ] || die "No groups selected. See --list."

# group_field <name> <column> — 2 language, 3 destination, 4 basePackage.
group_field() {
    groups_tsv | awk -F'\t' -v n="$1" -v c="$2" '$1 == n { print $c; exit }'
}

# Destinations that land in another git repo, checked before anything is written.
cd "$ROOT_DIR"
SELF_TOP="$(git rev-parse --show-toplevel 2>/dev/null || echo "$ROOT_DIR")"
DIRTY=()
echo "Selected ${#TARGETS[@]} group(s) from $(basename "$CONFIG"):"
for g in "${TARGETS[@]}"; do
    dest="$(group_field "$g" 3)"
    note=""
    if [ -n "$dest" ] && [ -d "$dest" ]; then
        top="$(git -C "$dest" rev-parse --show-toplevel 2>/dev/null || true)"
        if [ -n "$top" ] && [ "$top" != "$SELF_TOP" ]; then
            note="  ⚠️  writes into $(basename "$top") ($(git -C "$top" branch --show-current 2>/dev/null || echo detached))"
            if [ -n "$(git -C "$top" status --porcelain 2>/dev/null)" ]; then
                note="$note — HAS UNCOMMITTED CHANGES"
                DIRTY+=("$(basename "$top")")
            fi
        fi
    elif [ -n "$dest" ]; then
        note="  (destination $dest does not exist yet)"
    fi
    echo "  - $g [$(group_field "$g" 2)] -> ${dest:-.}$note"
done

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "Dry run: nothing generated."
    exit 0
fi

if [ ${#DIRTY[@]} -gt 0 ] && [ "$ALLOW_DIRTY" = false ]; then
    die "Destination repo(s) have uncommitted changes: $(printf '%s\n' "${DIRTY[@]}" | sort -u | tr '\n' ' ')
   A regen with cleanGenerated deletes and rewrites files there. Commit or stash first,
   or pass --allow-dirty."
fi

command -v java &> /dev/null || die "Java not found. Install Java 21+."
command -v "${SPECFUSE_CLI[0]}" &> /dev/null || die "${SPECFUSE_CLI[*]} not found on PATH. Install the suite: pipx install specfuse"

if [ "$SPEC_VERSION" = "latest" ]; then
    SPEC_VERSION=$(ls -d "$ROOT_DIR/api/specs/v"* 2>/dev/null | sort -V | tail -n 1 | xargs basename 2>/dev/null || true)
fi
SOURCE_ROOT="$ROOT_DIR/api/specs/$SPEC_VERSION"
[ -n "$SPEC_VERSION" ] && [ -d "$SOURCE_ROOT" ] || die "Spec directory not found: $SOURCE_ROOT"

echo ""
echo "📦 Bundling specs ($SPEC_VERSION)..."
OPENAPI_BUNDLE="$(config_value openApiSpecifications)"
"$SCRIPT_DIR/bundle-spec.sh" "$SOURCE_ROOT/openapi.yaml" "${OPENAPI_BUNDLE:-output/openapi-bundled.yaml}" > /dev/null
ASYNC_BUNDLE="$(config_value asyncSpecifications)"
if [ -n "$ASYNC_BUNDLE" ] && [ -f "$SOURCE_ROOT/asyncapi.yaml" ]; then
    "$SCRIPT_DIR/bundle-async-spec.sh" "$SOURCE_ROOT/asyncapi.yaml" "$ASYNC_BUNDLE" > /dev/null
fi
echo "  ✅ Bundled"

HOOK="$ROOT_DIR/scripts/post-generate.sh"
n=0
for g in "${TARGETS[@]}"; do
    n=$((n + 1))
    echo ""
    echo "── [$n/${#TARGETS[@]}] $g ──────────────────────────────"
    "${RUN_GENERATOR[@]}" generate --progress --group "$g" ${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"} "$CONFIG"
    if [ -x "$HOOK" ]; then
        echo "▶ post-generate: $g"
        "$HOOK" "$g" "$(group_field "$g" 2)" "$(group_field "$g" 3)" "$(group_field "$g" 4)"
    fi
done

echo ""
echo "✅ Generated ${#TARGETS[@]} group(s)."
others=()
for g in "${TARGETS[@]}"; do
    dest="$(group_field "$g" 3)"
    top="$(git -C "${dest:-.}" rev-parse --show-toplevel 2>/dev/null || true)"
    if [ -n "$top" ] && [ "$top" != "$SELF_TOP" ]; then others+=("$(basename "$top")"); fi
done
if [ ${#others[@]} -gt 0 ]; then
    echo "Next: review and PR the regen in $(printf '%s\n' "${others[@]}" | sort -u | tr '\n' ' ')"
    echo "      After those PRs merge, run ./scripts/specfuse/advance-state.sh."
fi
echo "Don't commit the stateDir changes this regen made (default .specfuse/state/):"
echo "only advance-state.sh, run against merged destination repos, moves the baseline."
