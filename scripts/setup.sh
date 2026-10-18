#!/usr/bin/env bash
# idempotent environment setup: clones ZSA's qmk_firmware fork if missing,
# makes sure it's on the firmware25 branch, applies the python3.14 compat
# patch it needs, and symlinks this repo's keymap/ into it. safe to re-run.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QMK_FIRMWARE="$HOME/qmk_firmware"
KEYMAP_DEST="$QMK_FIRMWARE/keyboards/zsa/voyager/keymaps/yayaya-alttab"

if [ ! -d "$QMK_FIRMWARE" ]; then
  echo "cloning zsa/qmk_firmware..."
  nix shell nixpkgs#qmk -c qmk setup zsa/qmk_firmware -b firmware25 --yes
fi

cd "$QMK_FIRMWARE"
if [ "$(git branch --show-current)" != "firmware25" ]; then
  # firmware25 (origin/HEAD) is required: it's the branch that has the
  # modules/zsa/oryx community module. firmware24 lacks it, which makes
  # locally-built firmware diverge from what Oryx's own cloud builder
  # produces (RGB/live-control behavior especially).
  echo "checking out firmware25..."
  git fetch origin firmware25 --depth=1
  git checkout firmware25
  git submodule update --init --recursive
fi

# python 3.14 removed ast.Num (deprecated since 3.8); this qmk_firmware
# checkout's math.py still uses it. patch to the ast.Constant equivalent.
MATH_PY="lib/python/qmk/math.py"
if grep -q "ast\.Num" "$MATH_PY"; then
  echo "patching $MATH_PY for python3.14 compat..."
  sed -i \
    -e 's/isinstance(node, ast\.Num)/isinstance(node, ast.Constant)/' \
    -e 's/return node\.n$/return node.value/' \
    "$MATH_PY"
fi

if [ ! -L "$KEYMAP_DEST" ]; then
  echo "linking keymap into qmk_firmware..."
  rm -rf "$KEYMAP_DEST"
  ln -s "$REPO_DIR/keymap" "$KEYMAP_DEST"
fi

echo "setup complete. run scripts/build.sh to compile."
