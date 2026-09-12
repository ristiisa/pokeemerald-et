"""Measure a pokeemerald source text string in on-screen pixels.

Unlike Gen-2's fixed 18-tile box, pokeemerald uses a proportional font: every
glyph has its own pixel width in `gFont<Face>LatinGlyphWidths[]` (src/fonts.c),
indexed by the charmap byte value. This module reproduces that: it parses
charmap.txt (char -> bytes, and {SYMBOL} -> bytes) and the width table, then
sums the width of each glyph in a source line.

Runtime placeholders (bytes 0xFD xx: {PLAYER}, {STR_VAR_1}, ...) expand to text
whose length isn't known until runtime, so they are charged a fixed estimate
(PLACEHOLDER_EST). Extended control codes (0xFC xx: colour, pause, ...) render
nothing and are charged 0.

LINE_WIDTH is the usable dialogue-box width in pixels, calibrated so the shipped
English text fits (see calibrate() / `make check`). The normal dialogue font is
the default; pass face= for menus that use a different one.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHARMAP = os.path.join(ROOT, "charmap.txt")
FONTS_C = os.path.join(ROOT, "src", "fonts.c")

# Usable width of the standard field message box, in pixels. The window content
# is 26 tiles but the text printer starts a couple px in and needs right margin;
# this value is calibrated to the shipped English corpus (every normal-font
# dialogue line fits) -- see calibrate().
LINE_WIDTH = 208

# Runtime-placeholder pixel estimates (0xFD <id>). Names are the player's/rival's
# chosen string (<=7 chars); STR_VARs are items/moves/numbers/places. We charge a
# moderate width so wrapping leaves room without being needlessly tight.
PLACEHOLDER_EST = {
    0x01: 42,   # PLAYER  (~7 chars)
    0x06: 42,   # RIVAL
    0x02: 36,   # STR_VAR_1
    0x03: 36,   # STR_VAR_2
    0x04: 36,   # STR_VAR_3
    0x05: 0,    # KUN (honorific; empty outside Japanese)
}
PLACEHOLDER_DEFAULT = 36

FACE_ARRAY = {
    "normal": "gFontNormalLatinGlyphWidths",
    "short": "gFontShortLatinGlyphWidths",
    "small": "gFontSmallLatinGlyphWidths",
    "narrow": "gFontNarrowLatinGlyphWidths",
    "small_narrow": "gFontSmallNarrowLatinGlyphWidths",
}

LINEBREAKS = ("\\n", "\\l", "\\p")
# a token is any {...} (possibly with an operand: {PAUSE 15}), a break code, EOS,
# or a single character.
_TOKEN = re.compile(r"\{([^}]*)\}|\\[nlp]|\$|(.)", re.S)


def _parse_charmap():
    """Return (chars, symbols): char->[bytes], NAME->[bytes]."""
    chars, symbols = {}, {}
    for line in open(CHARMAP, encoding="utf-8"):
        line = line.split("@", 1)[0].rstrip("\n")
        if "=" not in line:
            continue
        lhs, rhs = line.split("=", 1)
        vals = rhs.split()
        if not vals or not all(re.fullmatch(r"[0-9A-Fa-f]{2}", v) for v in vals):
            continue
        bs = [int(v, 16) for v in vals]
        lhs = lhs.strip()
        m = re.fullmatch(r"'(.+)'", lhs)
        if m:
            ch = m.group(1).replace("\\\\", "\\").replace("\\'", "'")
            chars[ch] = bs
        elif re.fullmatch(r"[A-Za-z0-9_]+", lhs):
            symbols[lhs] = bs
    return chars, symbols


def _parse_widths():
    src = open(FONTS_C, encoding="utf-8").read()
    out = {}
    for face, arr in FACE_ARRAY.items():
        m = re.search(arr + r"\[\]\s*=\s*\{(.*?)\};", src, re.S)
        out[face] = [int(x) for x in re.findall(r"-?\d+", m.group(1))] if m else []
    return out


_CHARS, _SYMBOLS = _parse_charmap()
_WIDTHS = _parse_widths()


def _bytes_width(bs, widths):
    """Pixel width of a flat byte list (handles 0xFD/0xFC sequences)."""
    w, i = 0, 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFD and i + 1 < len(bs):            # runtime placeholder
            w += PLACEHOLDER_EST.get(bs[i + 1], PLACEHOLDER_DEFAULT)
            i += 2
        elif b == 0xFC and i + 1 < len(bs):          # ext control code: 0 width
            i += 2                                    # (+ operands, also 0 width)
        elif b in (0x00,) and False:
            i += 1
        else:
            w += widths[b] if b < len(widths) else 0
            i += 1
    return w


def pixels(s, face="normal"):
    """On-screen pixel width of one source line (no line breaks expected)."""
    widths = _WIDTHS[face]
    total = 0
    for m in _TOKEN.finditer(s):
        sym, ch = m.group(1), m.group(2)
        tok = m.group(0)
        if tok in LINEBREAKS or tok == "$":
            continue
        if sym is not None:
            bs = _SYMBOLS.get(sym) or _CHARS.get(sym)
            if bs is None and " " in sym:     # operand token ({PAUSE 15}, ...)
                bs = _SYMBOLS.get(sym.split()[0])   # control code: 0 visible width
                total += _bytes_width(bs, widths) if bs else 0
            elif bs is None:          # unknown {TOKEN}: assume a placeholder
                total += PLACEHOLDER_DEFAULT
            else:
                total += _bytes_width(bs, widths)
        elif ch is not None:
            bs = _CHARS.get(ch)
            if bs is not None:
                total += _bytes_width(bs, widths)
            # characters absent from the charmap (shouldn't happen) contribute 0
    return total


def fits(s, face="normal", limit=None):
    return pixels(s, face) <= (LINE_WIDTH if limit is None else limit)


if __name__ == "__main__":
    import sys
    for line in sys.argv[1:] or ["You may call me the BERRY MASTER.",
                                  "Tõeline putukapüügivõistlus ootab {PLAYER}!"]:
        print(f"{pixels(line):4d}px  {line}")
