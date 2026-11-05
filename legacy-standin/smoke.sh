#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
base=${1:-http://localhost:8082}
report=$(mktemp)
trap 'rm -f "$report"' EXIT
python3 tools/parity/compare.py "$base" "$base" --verbose --output "$report"
