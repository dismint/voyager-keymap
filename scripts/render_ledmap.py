#!/usr/bin/env python3
"""
Reorder 52 argument-order HSV colors into LED-wiring order for one row of
ledmap[][RGB_MATRIX_LED_COUNT][3].

Colors must be given in the exact order keys appear in that layer's
LAYOUT_voyager(...) call (left-to-right, top-to-bottom, thumbs last — 52
total). This script reorders them into the LED-wiring order the array
actually needs (see arg_to_led.py for why those two orders differ) and
prints the finished C array literal.

Usage:
  render_ledmap.py <<'EOF'
  150,170,255
  0,0,255
  0,0,255
  ...   (52 lines total, one "h,s,v" triple per argument position)
  EOF
"""
import sys

from arg_to_led import compute


def main():
    arg_to_led = compute()
    lines = [l.strip() for l in sys.stdin if l.strip()]
    assert len(lines) == 52, f"expected 52 colors, got {len(lines)}"

    slots = [None] * 52
    for argpos, triple in enumerate(lines):
        slots[arg_to_led[argpos]] = triple

    print("{ " + ", ".join(f"{{{t}}}" for t in slots) + " }")


if __name__ == "__main__":
    main()
