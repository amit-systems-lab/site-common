#!/bin/sh
# Quarto post-render hook: run fix_pdfs.py, which declares its own
# dependencies (PEP 723). Locally that is uv; the GitHub runner ships pipx
# but not uv, and `pipx run` reads the same inline metadata.
set -e
script="$(dirname "$0")/fix_pdfs.py"
if command -v uv >/dev/null 2>&1; then
  exec uv run --quiet --no-project --script "$script"
fi
exec pipx run "$script"
