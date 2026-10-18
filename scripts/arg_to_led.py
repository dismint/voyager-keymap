#!/usr/bin/env python3
"""
Print the argument-position -> LED-index table for the ZSA Voyager.

The `ledmap[][RGB_MATRIX_LED_COUNT][3]` array in keymap.c is indexed in LED
WIRING order, which is NOT the same order keys appear in a LAYOUT_voyager(...)
macro call. Before writing a color into ledmap, map the key's position in the
LAYOUT_voyager(...) argument list (0-51, counting left-to-right, top-to-bottom,
thumbs last) through this table to find which ledmap slot actually controls it.

Usage:
  arg_to_led.py            print the full 52-row table
  arg_to_led.py <argpos>   print just the LED index for one argument position
"""
import json
import sys

QMK_FIRMWARE = "/home/dismint/qmk_firmware"


def compute():
    with open(f"{QMK_FIRMWARE}/keyboards/zsa/voyager/keyboard.json") as f:
        d = json.load(f)
    arg_to_matrix = [tuple(e["matrix"]) for e in d["layouts"]["LAYOUT"]["layout"]]
    matrix_to_led = {tuple(e["matrix"]): i for i, e in enumerate(d["rgb_matrix"]["layout"])}
    arg_to_led = [matrix_to_led[m] for m in arg_to_matrix]
    assert sorted(arg_to_led) == list(range(52)), "mapping is not a clean bijection"
    return arg_to_led


def main():
    arg_to_led = compute()
    if len(sys.argv) > 1:
        print(arg_to_led[int(sys.argv[1])])
    else:
        for argpos, led in enumerate(arg_to_led):
            print(f"{argpos}\t{led}")


if __name__ == "__main__":
    main()
