#!/usr/bin/env python3
"""
Reorder argument-order HSV colors into LED-wiring order for one row of
ledmap[][RGB_MATRIX_LED_COUNT][3].

Colors must be given in the exact order keys appear in that layer's
LAYOUT_xxx(...) call (left-to-right, top-to-bottom, thumbs last -- 52 for
Voyager, 72 for Moonlander). This script reorders them into the LED-wiring
order the array actually needs (see arg_to_led.py for why those two orders
differ) and prints the finished C array literal.

Usage:
  render_ledmap.py [voyager|moonlander] <<'EOF'
  150,170,255
  0,0,255
  0,0,255
  ...   (one "h,s,v" triple per argument position -- 52 or 72 lines total)
  EOF
"""
import sys

from arg_to_led import compute, BOARD_KEY_COUNT


def main():
    board = sys.argv[1] if len(sys.argv) > 1 else "voyager"
    arg_to_led = compute(board)
    key_count = BOARD_KEY_COUNT[board]
    lines = [l.strip() for l in sys.stdin if l.strip()]
    assert len(lines) == key_count, f"expected {key_count} colors, got {len(lines)}"

    slots = [None] * key_count
    for argpos, triple in enumerate(lines):
        slots[arg_to_led[argpos]] = triple

    print("{ " + ", ".join(f"{{{t}}}" for t in slots) + " }")


if __name__ == "__main__":
    main()
