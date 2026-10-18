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

# nixpkgs' qmk package is missing the "appdirs" python dependency; resolve it
# separately and hand it to that interpreter via PYTHONPATH.
appdirs_out="$(nix build --no-link --print-out-paths nixpkgs#python3Packages.appdirs)"
appdirs_site="$(find "$appdirs_out" -maxdepth 4 -type d -name site-packages | head -n1)"

cd "$QMK_FIRMWARE"
PYTHONPATH="$appdirs_site" nix shell nixpkgs#qmk -c qmk compile -kb "$KEYBOARD" -km "$KEYMAP"

bin_name="${KEYBOARD//\//_}_${KEYMAP}.bin"
mkdir -p "$REPO_DIR/build"
cp "$QMK_FIRMWARE/$bin_name" "$REPO_DIR/build/$bin_name"

if [ -d "$DOWNLOADS_DIR" ]; then
  downloads_name="zsa_${BOARD}_${KEYMAP}.bin"
  cp "$QMK_FIRMWARE/$bin_name" "$DOWNLOADS_DIR/$downloads_name"
  echo "ready to flash: $DOWNLOADS_DIR/$downloads_name (open Keymapp and flash this file)"
fi

echo "built: $REPO_DIR/build/$bin_name"
