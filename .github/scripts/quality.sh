#!/usr/bin/env bash
set -euo pipefail
unformatted=$(go tool -modfile=.github/tools/go.mod gofumpt -l .)
if [[ -n "$unformatted" ]]; then
  printf '%s\n' "$unformatted"
  exit 1
fi
go mod verify
go mod verify -modfile=.github/tools/go.mod
python3 -m compileall -q scripts
python3 -m unittest discover -s .github/tests -v
python3 .github/scripts/lint.py
python3 .github/scripts/vulnerabilities.py
