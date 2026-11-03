#!/usr/bin/env bash
# Run this repo's generated-code contract (gen-contract.yml) through the shared
# engine, the same way from a shell, from .specfuse/verification.yml and from CI.
#
#   ./scripts/check-gen-contract.sh                 # every rule
#   ./scripts/check-gen-contract.sh --list          # what is enforced
#   ./scripts/check-gen-contract.sh --explain GEN-004
#   ./scripts/check-gen-contract.sh --only GEN-001 GEN-004
#   ./scripts/check-gen-contract.sh --json findings.json
#
# Exit 0 clean, 1 violations, 2 the checker could not run.
#
# The engine is `specfuse.loop.gen_contract`, shipped in specfuse-loop 0.30+
# (`pipx install specfuse` or `uv tool install specfuse` brings it). Until the
# umbrella CLI dispatches `specfuse gen-contract`, the module is run directly,
# by the first of: SPECFUSE_PYTHON, the interpreter installed beside the
# `specfuse` command when it has the engine, `python3`.

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

# The Python beside the `specfuse` on PATH, following the link pipx and uv put
# there. Not the script's shebang: a long install path makes it `#!/bin/sh`.
python_beside_specfuse() {
  local bin target
  bin="$(command -v specfuse 2>/dev/null)" || return 0
  while [ -L "$bin" ]; do
    target="$(readlink "$bin")"
    case "$target" in
      /*) bin="$target" ;;
      *) bin="$(dirname "$bin")/$target" ;;
    esac
  done
  if [ -x "$(dirname "$bin")/python" ]; then
    printf '%s\n' "$(dirname "$bin")/python"
  fi
}

PY="${SPECFUSE_PYTHON:-}"
if [ -z "$PY" ]; then
  PY=python3
  BESIDE="$(python_beside_specfuse)"
  if [ -n "$BESIDE" ] && "$BESIDE" -c "import specfuse.loop.gen_contract" >/dev/null 2>&1; then
    PY="$BESIDE"
  fi
fi

if command -v specfuse >/dev/null 2>&1 && specfuse gen-contract --help >/dev/null 2>&1; then
  exec specfuse gen-contract "$@"
fi

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "check-gen-contract: $PY not found" >&2
  exit 2
fi

if ! "$PY" -c "import specfuse.loop.gen_contract" >/dev/null 2>&1; then
  cat >&2 <<EOF
check-gen-contract: the engine is not importable by $PY.
  Install it:  pipx install specfuse   (or: uv tool install specfuse)
  Or point SPECFUSE_PYTHON at an interpreter that has it.
EOF
  exit 2
fi

exec "$PY" -m specfuse.loop.gen_contract "$@"
