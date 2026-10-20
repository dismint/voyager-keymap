#!/usr/bin/env bash
# idempotent environment setup: clones ZSA's qmk_firmware fork if missing,
# makes sure it's on the firmware25 branch, applies the python compat patch
# it needs, and symlinks this repo's keymap/ (and keymap-moonlander/) into
# it. safe to re-run. the toolchain/qmk CLI themselves come from this
# repo's flake.nix (nix develop), not a floating nixpkgs channel -- nothing
# here depends on anything already installed on the machine besides Nix.
#
# usage: scripts/setup.sh [voyager|moonlander]  (default: both)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QMK_FIRMWARE="$HOME/qmk_firmware"
BOARD="${1:-all}"

if [ ! -d "$QMK_FIRMWARE" ]; then
  echo "cloning zsa/qmk_firmware..."
  nix develop "path:$REPO_DIR" --command qmk setup zsa/qmk_firmware -b firmware25 --yes
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

# python 3.12+ removed ast.Num (deprecated since 3.8); this qmk_firmware
# checkout's math.py still uses it. patch to the ast.Constant equivalent.
MATH_PY="lib/python/qmk/math.py"
if grep -q "ast\.Num" "$MATH_PY"; then
  echo "patching $MATH_PY for python3.14 compat..."
  sed -i \
    -e 's/isinstance(node, ast\.Num)/isinstance(node, ast.Constant)/' \
    -e 's/return node\.n$/return node.value/' \
    "$MATH_PY"
fi

link_keymap() {
  local repo_subdir="$1" qmk_keyboard="$2" qmk_keymap_name="$3"
  local dest="$QMK_FIRMWARE/keyboards/$qmk_keyboard/keymaps/$qmk_keymap_name"
  if [ ! -L "$dest" ]; then
    echo "linking $repo_subdir into qmk_firmware ($qmk_keyboard)..."
    rm -rf "$dest"
    ln -s "$REPO_DIR/$repo_subdir" "$dest"
  fi
}

if [ "$BOARD" = "voyager" ] || [ "$BOARD" = "all" ]; then
  link_keymap keymap zsa/voyager yayaya-alttab
fi
if [ "$BOARD" = "moonlander" ] || [ "$BOARD" = "all" ]; then
  link_keymap keymap-moonlander zsa/moonlander yayaya-alttab
fi

echo "setup complete. run scripts/build.sh [voyager|moonlander] to compile."
