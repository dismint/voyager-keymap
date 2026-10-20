#!/usr/bin/env bash
# compiles the voyager (default) or moonlander keymap and drops a flashable
# .bin into build/ here and into Windows Downloads, ready to flash with
# Keymapp.
#
# usage: scripts/build.sh [voyager|moonlander]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QMK_FIRMWARE="$HOME/qmk_firmware"
BOARD="${1:-voyager}"
KEYMAP="yayaya-alttab"
DOWNLOADS_DIR="/mnt/c/Users/justi/Downloads"

case "$BOARD" in
  voyager)    KEYBOARD="zsa/voyager" ;;
  moonlander) KEYBOARD="zsa/moonlander/reva" ;;
  *) echo "unknown board: $BOARD (expected voyager or moonlander)" >&2; exit 1 ;;
esac

# keymap/keymap.c (voyager) is the single source of truth; the moonlander
# keymap.c is always regenerated from it before building, so it can't drift.
if [ "$BOARD" = "moonlander" ]; then
  "$REPO_DIR/scripts/generate_moonlander.py"
fi

# the toolchain and qmk CLI come from this repo's pinned flake.nix/flake.lock
# (not a floating nixpkgs channel), so builds are reproducible on any machine
# and can't silently break from an upstream nixpkgs update.
cd "$QMK_FIRMWARE"
nix develop "path:$REPO_DIR" --command qmk compile -kb "$KEYBOARD" -km "$KEYMAP"

bin_name="${KEYBOARD//\//_}_${KEYMAP}.bin"
mkdir -p "$REPO_DIR/build"
cp "$QMK_FIRMWARE/$bin_name" "$REPO_DIR/build/$bin_name"

if [ -d "$DOWNLOADS_DIR" ]; then
  downloads_name="zsa_${BOARD}_${KEYMAP}.bin"
  cp "$QMK_FIRMWARE/$bin_name" "$DOWNLOADS_DIR/$downloads_name"
  echo "ready to flash: $DOWNLOADS_DIR/$downloads_name (open Keymapp and flash this file)"
fi

echo "built: $REPO_DIR/build/$bin_name"
