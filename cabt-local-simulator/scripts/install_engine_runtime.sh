#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="2.2.0"
ARCHIVE="lima-${VERSION}-Darwin-arm64.tar.gz"
URL="https://github.com/lima-vm/lima/releases/download/v${VERSION}/${ARCHIVE}"
EXPECTED_SHA="bbdef91774885a0d05f7b048c4eb89ae2bcf3a0c252ae7ca7934e63df76d93c3"
RUNTIME="$ROOT/.runtime/lima"
DOWNLOADS="$ROOT/.runtime/downloads"
LIMA_HOME="$HOME/.cabt-lima"
export LIMA_HOME

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  print -u2 "This installer is for Apple Silicon macOS."
  exit 2
fi

if ! pkgutil --pkg-info=com.apple.pkg.RosettaUpdateAuto >/dev/null 2>&1; then
  print -u2 "Rosetta is required. Install it from macOS Software Update, then run this installer again."
  exit 2
fi

mkdir -p "$RUNTIME" "$DOWNLOADS" "$LIMA_HOME"
if [[ ! -x "$RUNTIME/bin/limactl" ]]; then
  curl --fail --location --retry 3 "$URL" --output "$DOWNLOADS/$ARCHIVE"
  ACTUAL_SHA="$(shasum -a 256 "$DOWNLOADS/$ARCHIVE" | awk '{print $1}')"
  if [[ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]]; then
    print -u2 "Lima archive checksum mismatch."
    exit 3
  fi
  tar -xzf "$DOWNLOADS/$ARCHIVE" -C "$RUNTIME"
fi

if ! "$RUNTIME/bin/limactl" list ce --quiet | grep -qx ce; then
  "$RUNTIME/bin/limactl" start \
    --name=ce \
    --cpus=4 \
    --memory=6 \
    --disk=24 \
    --vm-type=vz \
    --rosetta \
    --containerd=user \
    --mount-writable \
    --port-forward=8780:8780 \
    --progress \
    --timeout=20m \
    template:default \
    -y
else
  "$RUNTIME/bin/limactl" start ce -y
fi

PYTHONPATH="$ROOT/src" python3 "$ROOT/manage_engine.py" start
