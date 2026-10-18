#!/usr/bin/env python3
"""
Generate keymap-moonlander/keymap.c from keymap/keymap.c.

keymap/keymap.c (the Voyager) is the single source of truth for this
keymap's logic -- layers, combos, Alt-Tab/gaming mechanics, lighting. The
Moonlander file is a derived artifact: this script re-maps the Voyager's
52 argument-position keycodes/colors onto their equivalent Moonlander
argument positions (see MOONLANDER_TO_VOYAGER below), copies every other
line of keymap.c verbatim (enums, combos, process_record_user, lighting
functions -- none of that is keyboard-specific), and writes the result.

Never hand-edit keymap-moonlander/keymap.c -- edit keymap/keymap.c and
re-run this script. scripts/build.sh moonlander does this automatically.

Usage:
    scripts/generate_moonlander.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_layouts import parse_layers, extract_balanced
from arg_to_led import compute as arg_to_led_for

REPO_DIR = Path(__file__).resolve().parent.parent
QMK_FIRMWARE = Path.home() / "qmk_firmware"
VOYAGER_KEYMAP_C = REPO_DIR / "keymap" / "keymap.c"
MOONLANDER_KEYMAP_C = REPO_DIR / "keymap-moonlander" / "keymap.c"
MOONLANDER_JSON = QMK_FIRMWARE / "keyboards/zsa/moonlander/reva/keyboard.json"

# Moonlander argument position -> Voyager argument position, or None if
# that Moonlander key is intentionally left unused. The Moonlander has 72
# argument positions to the Voyager's 52 (an extra pinky column, an extra
# bottom row, and a 4-key thumb cluster vs. 2 per half); the 20 extras are
# left idle per Justin's request when porting: the 3-key inner-edge column
# per half (rows 0-2), the whole bottom row per half (incl. the big wide
# key), and the outermost of each half's 3 regular thumb keys. See
# CLAUDE.md's "Porting to a new board" section for the full table and the
# physical reasoning -- this is a hardware/layout-design fact, not
# something that changes with keymap edits, hence hardcoded here.
MOONLANDER_TO_VOYAGER = [None] * 72


def _setrange(moon_start, voy_start, count):
    for i in range(count):
        MOONLANDER_TO_VOYAGER[moon_start + i] = voy_start + i


_setrange(0, 0, 6)      # row0 left: Esc,1,2,3,4,5
_setrange(8, 6, 6)      # row0 right: 6,7,8,9,0,Bksp
_setrange(14, 12, 6)    # row1 left: Tab,Q,W,E,R,T
_setrange(22, 18, 6)    # row1 right: Y,U,I,O,P,\
_setrange(28, 24, 6)    # row2 left: Meta,A,S,D,F,G
_setrange(36, 30, 6)    # row2 right: H,J,K,L,;,'
_setrange(42, 36, 6)    # row3 left: Shift,Z,X,C,V,B
_setrange(48, 42, 6)    # row3 right: N,M,,,.,/,Shift
# row4 (54-65): unused. thumb cluster: each half has 3 keys (outer, middle,
# inner-toward-center); the innermost of each is left unused, keeping the
# outer two -- these are the two keys Justin's real Moonlander layout
# already uses for Ctrl/Meta (left) and Enter/Space (right), so the port
# reuses the same physical slots his muscle memory already expects.
MOONLANDER_TO_VOYAGER[66] = 48  # left thumb outer: Ctrl
MOONLANDER_TO_VOYAGER[67] = 49  # left thumb middle: LR 1
MOONLANDER_TO_VOYAGER[70] = 50  # right thumb middle: Enter
MOONLANDER_TO_VOYAGER[71] = 51  # right thumb outer: Space
# thumb positions 68 and 69 (innermost of each half) are left unused

assert sorted(v for v in MOONLANDER_TO_VOYAGER if v is not None) == list(range(52))

# (left_count, right_count) per logical keymap row, in Moonlander argument order
ROW_SPLITS = [(7, 7), (7, 7), (7, 7), (6, 6), (6, 6), (3, 3)]


def build_moonlander_keymap(voyager_tokens):
    return [
        "KC_TRANSPARENT" if v is None else voyager_tokens[v]
        for v in MOONLANDER_TO_VOYAGER
    ]


def build_moonlander_colors(voyager_colors_arg_order):
    return [
        "{0,0,0}" if v is None else voyager_colors_arg_order[v]
        for v in MOONLANDER_TO_VOYAGER
    ]


def format_keymap_layer(tokens):
    lines = []
    pos = 0
    for lc, rc in ROW_SPLITS:
        left = tokens[pos:pos + lc]; pos += lc
        right = tokens[pos:pos + rc]; pos += rc
        left_str = " ".join(f"{t + ',':<17}" for t in left)
        right_str = " ".join(f"{t + ',':<17}" for t in right)
        lines.append(f"    {left_str}                                {right_str}")
    assert pos == 72
    return re.sub(r",(\s*)$", r"\1", "\n".join(lines).rstrip())


def format_ledmap_layer(colors_arg_order, arg_to_led):
    slots = [None] * 72
    for argpos, triple in enumerate(colors_arg_order):
        slots[arg_to_led[argpos]] = triple
    return "{ " + ", ".join(slots) + " }"


def replace_array(text, decl_prefix, new_block):
    decl_start = text.index(decl_prefix)
    eq_pos = text.index("=", decl_start)
    open_brace = text.index("{", eq_pos)
    extract_balanced(text, open_brace, "{", "}")  # validate balance
    depth, close_brace = 0, None
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                close_brace = i
                break
    end_of_stmt = text.index(";", close_brace) + 1
    return text[:decl_start] + new_block + text[end_of_stmt:]


def main():
    voyager_text = VOYAGER_KEYMAP_C.read_text()
    voyager_arg_to_led = arg_to_led_for("voyager")
    moonlander_arg_to_led = arg_to_led_for("moonlander")

    keymap_layers = parse_layers(voyager_text, "keymaps", "LAYOUT_voyager", 52)
    led_layers = parse_layers(voyager_text, "ledmap", "LAYOUT_voyager", 52)

    keymaps_block = "const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {\n"
    ledmap_block = "const uint8_t PROGMEM ledmap[][RGB_MATRIX_LED_COUNT][3] = {\n"
    for layer_idx in sorted(keymap_layers):
        moon_tokens = build_moonlander_keymap(keymap_layers[layer_idx])
        keymaps_block += f"  [{layer_idx}] = LAYOUT_moonlander(\n{format_keymap_layer(moon_tokens)}\n  ),\n"

        # led_layers[idx] is parsed in LED-wiring order (how ledmap[] is
        # literally written); convert to Voyager argument order first.
        led_order_colors = led_layers[layer_idx]
        voyager_colors_arg_order = [led_order_colors[voyager_arg_to_led[a]] for a in range(52)]
        moon_colors = build_moonlander_colors(voyager_colors_arg_order)
        ledmap_block += f"    [{layer_idx}] = {format_ledmap_layer(moon_colors, moonlander_arg_to_led)},\n\n"
    keymaps_block += "};"
    ledmap_block += "};"

    text = voyager_text
    text = replace_array(text, "const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS]", keymaps_block)
    text = replace_array(text, "const uint8_t PROGMEM ledmap[][RGB_MATRIX_LED_COUNT][3]", ledmap_block)

    header = (
        "// GENERATED FILE -- do not hand-edit.\n"
        "// Derived from keymap/keymap.c (the Voyager, the single source of\n"
        "// truth for this keymap) by scripts/generate_moonlander.py. Edit that\n"
        "// file and re-run the script (or scripts/build.sh moonlander, which\n"
        "// does so automatically) instead of editing this one.\n\n"
    )
    MOONLANDER_KEYMAP_C.write_text(header + text)
    print(f"wrote {MOONLANDER_KEYMAP_C}")


if __name__ == "__main__":
    main()
