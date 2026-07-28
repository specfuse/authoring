#!/usr/bin/env bash
#
# Copyright 2026 Specfuse Contributors
# Licensed under the Apache License, Version 2.0. See LICENSE.
#
# spectral-lint.sh — run Spectral so that a crash cannot be mistaken for a pass.
#
# WHY THIS EXISTS
#
# The failure mode of a validation tool is silence. When Spectral crashes — a
# null the ruleset engine cannot handle, an unresolvable $ref, a bad ruleset
# path, an OOM, a timeout — it emits no findings and produces an empty report.
# Any wrapper that asks "did Spectral report errors?" gets "no" and concludes
# the spec is clean. There is no partial output and no non-zero finding count to
# notice. A project can sit in that state for months believing it is gated.
#
# So this wrapper does not ask whether findings were reported. It asks whether
# Spectral actually ran:
#
#   exit 0        findings below the fail severity        -> pass
#   exit 1        findings at or above the fail severity  -> fail (real findings)
#   exit >= 2     Spectral itself failed                  -> fail (crash)
#   no output     Spectral produced nothing at all        -> fail (crash)
#
# The last two are the point. Adopt this pattern in any wrapper you write,
# including ones that never touch this kit's rulesets — it is not specific to
# any rule or any bug, it is specific to the fact that silence is the default
# shape of a broken lint run.
#
# Usage:
#   scripts/spectral-lint.sh <label> <ruleset> <target> [extra spectral args...]
#
# Example:
#   scripts/spectral-lint.sh "OpenAPI bundle" \
#     schemas/spectral/specfuse-openapi.yaml "$RUNNER_TEMP/hello-orders.bundle.yaml"

set -uo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: $0 <label> <ruleset> <target> [extra spectral args...]" >&2
  exit 64
fi

LABEL="$1"; RULESET="$2"; TARGET="$3"; shift 3

if ! REPORT="$(mktemp "${TMPDIR:-/tmp}/spectral-report.XXXXXX")" || [[ -z "$REPORT" ]]; then
  echo "::error::could not create a temp file for the Spectral report." >&2
  exit 70
fi
trap 'rm -f "$REPORT"' EXIT

echo "==> Spectral: ${LABEL}"

spectral lint \
  --ruleset "$RULESET" \
  --fail-severity error \
  "$@" \
  "$TARGET" >"$REPORT" 2>&1
STATUS=$?

cat "$REPORT"

# A crash. Spectral exits 0 for "clean", 1 for "findings at/above fail-severity",
# and 2+ for "I could not run". Only the first two are verdicts about the spec.
if [[ $STATUS -ge 2 ]]; then
  echo "::error::Spectral exited ${STATUS} on ${LABEL} — it FAILED TO RUN." >&2
  echo "This is not a clean spec. No findings were produced because no linting" >&2
  echo "happened. Do not treat this as a pass." >&2
  exit "$STATUS"
fi

# Belt and braces: even at exit 0, a report with no content means Spectral did
# not get far enough to say anything, including "No results ... found!".
if [[ ! -s "$REPORT" ]]; then
  echo "::error::Spectral produced no output on ${LABEL} — treat as failure, not a clean run." >&2
  exit 1
fi

if [[ $STATUS -eq 1 ]]; then
  echo "::error::Spectral found error-severity problems in ${LABEL}." >&2
  exit 1
fi

echo "==> ${LABEL}: clean (Spectral ran and reported no error-severity findings)."
