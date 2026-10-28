#!/usr/bin/env bash
#
# Re-apply this repo's temporary patches to generated code, or prove they are
# all in place.
#
# A patch in gen-patches/ is a stop-gap for a generator defect that cannot be
# worked around from src/: a `git diff` of gen-src/ files, headed by the
# generator issue that will make it unnecessary. A regen with cleanGenerated
# wipes gen-src/, so every patch has to go back on after every regen until the
# fix ships in the generator and the pin reaches it. The spec repo's
# scripts/post-generate.sh calls this once per regenerated group; CI runs it
# with --check.
#
#   ./scripts/apply-gen-patches.sh                  # apply every patch
#   ./scripts/apply-gen-patches.sh HelloOrders.Api  # only patches touching these project folders
#   ./scripts/apply-gen-patches.sh --check          # every patch is applied and tracked (the gate)
#
# Per patch, applying reports one of:
#   applied          it went on cleanly
#   already present  the tree already has it. Right after a regen, that means the
#                    generator now emits the fix: retire the patch (exit 0, warns)
#   FAILED           neither: the generator changed the code around it. Re-derive
#                    the patch from the new output, or retire it if the defect is gone
#
# Every patch must carry a `Generator-Issue:` line before its first `diff --git`,
# be listed by file name in gen-patches/README.md, and only modify existing files
# under a gen-src/ folder: a patch never creates or deletes a generated file.
#
# Exit: 0 all good, 1 a patch failed or is untracked, 2 cannot run.
#
# Seeded from the Specfuse authoring kit (templates/component-contract/csharp/)
# and owned by this repo from then on.

set -uo pipefail
cd "$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)" || exit 2

DIR=gen-patches
INDEX="$DIR/README.md"
CHECK=false
FOLDERS=()
for a in "$@"; do
  case "$a" in
    --check) CHECK=true ;;
    -h|--help) sed -n '2,31p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "apply-gen-patches: unknown option $a" >&2; exit 2 ;;
    *) FOLDERS+=("${a%/}") ;;
  esac
done

shopt -s nullglob
PATCHES=("$DIR"/*.patch)
if [ ${#PATCHES[@]} -eq 0 ]; then
  echo "apply-gen-patches: no patches in $DIR/"
  exit 0
fi

# Does every file the patch touches sit under one of the named folders?
in_scope() {
  [ ${#FOLDERS[@]} -eq 0 ] && return 0
  local f ok
  while IFS= read -r f; do
    ok=false
    for d in "${FOLDERS[@]}"; do
      case "$f" in "$d"/*) ok=true ;; esac
    done
    $ok || return 1
  done < <(git apply --numstat "$1" | cut -f3)
  return 0
}

# Header, index and shape problems, one line each, empty when the patch is well formed.
problems() {
  local p="$1" name f
  name="$(basename "$p")"
  sed '/^diff --git /,$d' "$p" | grep -q '^Generator-Issue: *[^ ]' \
    || echo "no 'Generator-Issue:' line before the first diff"
  [ -f "$INDEX" ] && grep -qF "$name" "$INDEX" \
    || echo "not listed in $INDEX"
  git apply --summary "$p" | grep -Eq '^ *(create|delete) mode' \
    && echo "creates or deletes a file; a patch only modifies existing generated files"
  while IFS= read -r f; do
    case "$f" in */gen-src/*) ;; *) echo "touches $f, which is not under a gen-src/ folder" ;; esac
  done < <(git apply --numstat "$p" | cut -f3)
}

status=0
retire=()
for p in "${PATCHES[@]}"; do
  in_scope "$p" || continue
  issue="$(sed '/^diff --git /,$d' "$p" | sed -n 's/^Generator-Issue: *//p' | head -1)"
  bad="$(problems "$p")"
  if [ -n "$bad" ]; then
    echo "  FAILED           $p"
    while IFS= read -r line; do echo "                   $line"; done <<<"$bad"
    status=1
    continue
  fi
  if $CHECK; then
    if git apply --reverse --check "$p" 2>/dev/null; then
      echo "  ok               $p  ($issue)"
    elif git apply --check "$p" 2>/dev/null; then
      echo "  NOT APPLIED      $p  ($issue): run ./scripts/apply-gen-patches.sh"
      status=1
    else
      echo "  STALE            $p  ($issue): the generated code changed under it; re-derive or retire it"
      status=1
    fi
  else
    if git apply --check "$p" 2>/dev/null; then
      git apply "$p" && echo "  applied          $p  ($issue)"
    elif git apply --reverse --check "$p" 2>/dev/null; then
      echo "  already present  $p  ($issue)"
      retire+=("$p")
    else
      echo "  FAILED           $p  ($issue): does not apply to the regenerated code"
      git apply --check "$p" 2>&1 | sed 's/^/                   /' | head -5
      status=1
    fi
  fi
done

if [ ${#retire[@]} -gt 0 ]; then
  echo ""
  echo "If this run follows a fresh regen, the generator now emits these changes itself."
  echo "Confirm the issue is fixed, then retire each patch (gen-patches/README.md, 'Retiring a patch'):"
  printf '  %s\n' "${retire[@]}"
fi
exit "$status"
