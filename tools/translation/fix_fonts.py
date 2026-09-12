#!/usr/bin/env python3
"""fix_fonts.py -- draw Estonian 'õ'/'Õ' glyphs into the Latin font sheets.

pokeemerald's charmap has ä/ö/ü (Ä/Ö/Ü) but not õ/Õ, the one extra Estonian
vowel. We reuse two unused accent slots (ô=0x24 -> õ, Ô=0x0F -> Õ; see
charmap.txt) and draw the glyph by splicing a tilde onto the base letter:

    glyph cells are 16x16 in a 16-wide grid, index N at (N%16, N//16).
    The diacritic of 'õ' sits in exactly the rows where 'ö' differs from 'o'
    (the marks above the x-height); the body is identical to 'o'. So:
        õ = o, with those rows replaced by the tilde from 'ñ'
        Õ = O, with ö/O's diacritic rows replaced by the tilde from 'Ñ'
    which adapts to each font's own metrics automatically.

Idempotent: reads o/O/ñ/Ñ/ö/Ö (never the target slots) and overwrites
0x24/0x0F, so it is safe to re-run. Run from anywhere.
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS = ("latin_normal", "latin_short", "latin_small",
         "latin_narrow", "latin_small_narrow")

O, O_UP = 0xE3, 0xC9          # base letters
OE, OE_UP = 0xF5, 0xF2        # ö / Ö  (to locate the diacritic rows)
NT, NT_UP = 0x29, 0x14        # ñ / Ñ  (tilde source)
OTILDE, OTILDE_UP = 0x24, 0x0F  # targets (reused ô / Ô slots)


def cell(idx):
    return (idx % 16) * 16, (idx // 16) * 16


def rows(px, idx):
    x0, y0 = cell(idx)
    return [[px[x0 + x, y0 + y] for x in range(16)] for y in range(16)]


def write_rows(px, idx, grid):
    x0, y0 = cell(idx)
    for y in range(16):
        for x in range(16):
            px[x0 + x, y0 + y] = grid[y][x]


def make(base, accent, diac_ref):
    """base/accent/diac_ref are 16-row glyphs; return base with the accent's
    tilde spliced into the rows where diac_ref marks a diacritic over base."""
    out = [row[:] for row in base]
    for y in range(16):
        if diac_ref[y] != base[y]:        # a diacritic row
            out[y] = accent[y][:]
    return out


def process(name):
    path = os.path.join(ROOT, "graphics", "fonts", name + ".png")
    im = Image.open(path)
    px = im.load()
    o, oup = rows(px, O), rows(px, O_UP)
    oe, oeup = rows(px, OE), rows(px, OE_UP)
    nt, ntup = rows(px, NT), rows(px, NT_UP)
    write_rows(px, OTILDE, make(o, nt, oe))
    write_rows(px, OTILDE_UP, make(oup, ntup, oeup))
    im.save(path)
    return path


def main():
    for name in FONTS:
        p = process(name)
        print(f"  õ/Õ drawn -> {os.path.relpath(p, ROOT)}")


if __name__ == "__main__":
    main()
