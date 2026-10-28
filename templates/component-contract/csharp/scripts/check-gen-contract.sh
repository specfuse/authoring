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
# (`pipx install specfuse` brings it). Until the umbrella CLI dispatches
# `specfuse gen-contract`, the module is run directly. Set SPECFUSE_PYTHON to
# the interpreter that has specfuse-loop installed when it is not `python3`.

set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

PY="${SPECFUSE_PYTHON:-python3}"

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
  Install it:  $PY -m pip install 'specfuse-loop>=0.30'
  Or point SPECFUSE_PYTHON at an interpreter that has it (pipx: ~/.local/pipx/venvs/specfuse/bin/python).
EOF
  exit 2
fi

exec "$PY" -m specfuse.loop.gen_contract "$@"
