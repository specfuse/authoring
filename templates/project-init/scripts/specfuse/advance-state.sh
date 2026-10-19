#!/bin/bash
# Advance the regen-over-regen baseline (<stateDir>/<group>.json) to what the
# destination repos have actually merged.
#
# Why: each group's state file is what the next regen's CHANGELOG.md is diffed
# against, so it must describe the code that SHIPPED in the destination repo, not
# the working copy a local regen just produced. A baseline committed ahead of
# the destination's default branch adds phantom "Breaking" entries to every later
# changelog; a stale one makes the next changelog repeat old changes. Run this
# AFTER a regen PR merges in a destination repo, then open a spec-repo PR with
# only the changed state files.
#
# How: wraps the generator's `baseline` command, which re-captures the surface
# from the generated code already on disk and regenerates nothing. `baseline`
# rewrites every group's state file, so this script keeps a group's new
# baseline only when its destination repo is clean, on its default branch, and
# level with origin; every other group's state file is restored afterwards.
#
# Limit: `baseline` rewrites <group>.json only. If <group>.paths.json has
# drifted too, regenerate the group into the destination's default branch and
# confirm the output is byte-identical.
#
# Usage:
#   ./scripts/specfuse/advance-state.sh                   # every destination repo that passes
#   ./scripts/specfuse/advance-state.sh --repo Backend    # only these repos (repeatable; dir name)
#   ./scripts/specfuse/advance-state.sh --dry-run         # report what would be captured, keep nothing
#   ./scripts/specfuse/advance-state.sh --no-fetch        # compare to the local origin ref, no fetch
#   ./scripts/specfuse/advance-state.sh --branch main     # default branch (default: origin/HEAD, else main)

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
command -v java &> /dev/null || die "Java not found. Install Java 21+."
command -v "${SPECFUSE_CLI[0]}" &> /dev/null || die "${SPECFUSE_CLI[*]} not found on PATH. Install the suite: pipx install specfuse"

DRY_RUN=false
FETCH=true
BRANCH=""
SELECTED=()
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run|-n) DRY_RUN=true ;;
        --no-fetch) FETCH=false ;;
        --repo) shift; [ $# -gt 0 ] || die "--repo needs a value"; SELECTED+=("$1") ;;
        --branch) shift; [ $# -gt 0 ] || die "--branch needs a value"; BRANCH="$1" ;;
        -h|--help) sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) die "Unknown argument: $1 (see --help)" ;;
    esac
    shift
done

cd "$ROOT_DIR"

# stateDir resolves against the working directory, which is ROOT_DIR here.
STATE_DIR="$(python3 - "$CONFIG" <<'PY'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8")).get("stateDir") or ".specfuse/state")
PY
)"
STATE_DIR="${STATE_DIR%/}"; STATE_DIR="${STATE_DIR#./}"
SELF_TOP="$(git rev-parse --show-toplevel 2>/dev/null)" || die "$ROOT_DIR is not a git repo."

# Restoring groups uses `git checkout`, which would also discard a hand edit to
# a state file, so refuse to start on a dirty state dir (dry runs included).
if [ -d "$STATE_DIR" ] && [ -n "$(git status --porcelain -- "$STATE_DIR")" ]; then
    die "$STATE_DIR has uncommitted changes. Commit or discard them first (git checkout -- $STATE_DIR && git clean -fd -- $STATE_DIR)."
fi

# Plain parallel arrays, not `declare -A`: macOS /bin/bash is 3.2.
# GROUP_NAMES[i] is generated into the repo at GROUP_REPOS[i] ("" = this repo
# or no repo, which never advances).
GROUP_NAMES=(); GROUP_REPOS=()
while IFS=$'\t' read -r name dest; do
    top=""
    if [ -n "$dest" ] && [ -d "$dest" ]; then
        top="$(git -C "$dest" rev-parse --show-toplevel 2>/dev/null || true)"
        [ "$top" = "$SELF_TOP" ] && top=""
    fi
    if [ -z "$top" ]; then
        echo "⏭️  $name: destination ${dest:-.} is not in a separate git repo — not advanced"
    fi
    GROUP_NAMES+=("$name"); GROUP_REPOS+=("$top")
done < <(python3 - "$CONFIG" <<'PY'
import json, sys
for g in json.load(open(sys.argv[1], encoding="utf-8")).get("groups", []):
    print(f"{g.get('name') or ''}\t{g.get('destination') or ''}")
PY
)

PASSING=""
is_passing() { [ -n "$1" ] && printf '%s\n' "$PASSING" | grep -qxF "$1"; }

ok_count=0
while IFS= read -r top; do
    [ -n "$top" ] || continue
    repo="$(basename "$top")"
    if [ ${#SELECTED[@]} -gt 0 ] && [[ ! " ${SELECTED[*]} " == *" $repo "* ]]; then
        echo "⏭️  $repo: not selected"; continue
    fi
    branch="$BRANCH"
    if [ -z "$branch" ]; then
        branch="$(git -C "$top" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || true)"
        branch="${branch#origin/}"
        branch="${branch:-main}"
    fi
    if [ "$FETCH" = true ] && ! git -C "$top" fetch -q origin "$branch" 2>/dev/null; then
        echo "⚠️  $repo: git fetch failed — comparing to the local origin/$branch, which may be stale"
    fi
    current="$(git -C "$top" branch --show-current)"
    if [ "$current" != "$branch" ]; then
        echo "⏭️  $repo: on '${current:-detached HEAD}', not $branch"
    elif [ -n "$(git -C "$top" status --porcelain)" ]; then
        echo "⏭️  $repo: has uncommitted changes (unmerged regen?)"
    elif [ "$(git -C "$top" rev-parse HEAD)" != "$(git -C "$top" rev-parse "origin/$branch" 2>/dev/null)" ]; then
        echo "⏭️  $repo: $branch is not level with origin/$branch"
    else
        echo "✅ $repo @ $(git -C "$top" rev-parse --short HEAD) ($branch)"
        PASSING="$PASSING$top"$'\n'
        ok_count=$((ok_count + 1))
    fi
done < <(printf '%s\n' ${GROUP_REPOS[@]+"${GROUP_REPOS[@]}"} | sort -u)

[ "$ok_count" -gt 0 ] || die "No destination repo is clean and level with origin — nothing to advance."

echo ""
args=(baseline)
[ "$DRY_RUN" = true ] && args+=(--dry-run)
"${RUN_GENERATOR[@]}" "${args[@]}" "$CONFIG"

restore() {
    local f="$1"
    if git ls-files --error-unmatch "$f" &> /dev/null; then
        git checkout -q -- "$f"
    else
        rm -f "$f"
    fi
}

if [ "$DRY_RUN" = true ]; then
    # `baseline --dry-run` writes nothing on current generators; restoring
    # anyway keeps an older project-pinned generator from leaving changes.
    git checkout -q -- "$STATE_DIR" 2>/dev/null || true
    git clean -q -f -- "$STATE_DIR" 2>/dev/null || true
    echo ""
    echo "Dry run: nothing kept. Only the ✅ repos' groups would advance."
    exit 0
fi

# Put back every group whose repo did not pass, was not selected, or is this repo.
for i in "${!GROUP_NAMES[@]}"; do
    is_passing "${GROUP_REPOS[$i]}" && continue
    restore "$STATE_DIR/${GROUP_NAMES[$i]}.json"
done

echo ""
if [ -z "$(git status --porcelain -- "$STATE_DIR")" ]; then
    echo "State already matches the destination repos — nothing to commit."
    exit 0
fi
git status --short -- "$STATE_DIR"
echo ""
echo "Next: on a branch, commit only these state files, citing the destination"
echo "repo SHA(s) above and the regen PR(s), and open a PR. No spec changes in it."
