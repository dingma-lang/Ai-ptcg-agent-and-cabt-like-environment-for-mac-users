#!/bin/zsh
set -e

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --disable-pip-version-check -e .
.venv/bin/python start_app.py
