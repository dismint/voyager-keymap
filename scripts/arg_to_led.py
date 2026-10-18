#!/usr/bin/env python3
"""
Print the argument-position -> LED-index table for a board (default: the
ZSA Voyager).

The `ledmap[][RGB_MATRIX_LED_COUNT][3]` array in keymap.c is indexed in LED
WIRING order, which is NOT the same order keys appear in a LAYOUT_xxx(...)
macro call. Before writing a color into ledmap, map the key's position in
the LAYOUT_xxx(...) argument list (counting left-to-right, top-to-bottom,
thumbs last) through this table to find which ledmap slot actually controls
it.

Usage:
  arg_to_led.py [board]            print the full table (board: voyager [default] or moonlander)
  arg_to_led.py [board] <argpos>   print just the LED index for one argument position
"""
import json
import sys

QMK_FIRMWARE = "/home/dismint/qmk_firmware"

BOARD_JSON = {
    "voyager": f"{QMK_FIRMWARE}/keyboards/zsa/voyager/keyboard.json",
    "moonlander": f"{QMK_FIRMWARE}/keyboards/zsa/moonlander/reva/keyboard.json",
}
BOARD_KEY_COUNT = {"voyager": 52, "moonlander": 72}


def compute(board="voyager"):
    with open(BOARD_JSON[board]) as f:
        d = json.load(f)
    arg_to_matrix = [tuple(e["matrix"]) for e in d["layouts"]["LAYOUT"]["layout"]]
    matrix_to_led = {tuple(e["matrix"]): i for i, e in enumerate(d["rgb_matrix"]["layout"])}
    arg_to_led = [matrix_to_led[m] for m in arg_to_matrix]
    key_count = BOARD_KEY_COUNT[board]
    assert sorted(arg_to_led) == list(range(key_count)), "mapping is not a clean bijection"
    return arg_to_led


def main():
    args = sys.argv[1:]
    board = "voyager"
    if args and args[0] in BOARD_JSON:
        board = args.pop(0)
    arg_to_led = compute(board)
    if args:
        print(arg_to_led[int(args[0])])
    else:
        for argpos, led in enumerate(arg_to_led):
            print(f"{argpos}\t{led}")


if __name__ == "__main__":
    main()
