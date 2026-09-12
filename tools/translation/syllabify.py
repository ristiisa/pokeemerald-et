#!/usr/bin/env python3
"""syllabify.py -- Estonian syllable splitting for on-screen line breaking.

The actual hyphenation is **pyphen with lang="et"** (Filosoft `hyph_et_EE`
patterns), which gives correct Estonian syllable breaks, e.g.:

    putukapüügivõistlus -> pu-tu-ka-püü-gi-võist-lus
    salvestusfailidest  -> sal-ves-tus-fai-li-dest

This module adds what the raw hyphenator can't do for the proportional GBA box:

  * **pixel-aware wrapping** -- a break point is chosen by on-screen pixel width
    (see textwidth.pixels), not Python string length, since glyph widths vary
    and `{PLAYER}`-style tokens have their own estimated width.
  * **game-token words** -- pyphen must not split inside a `{...}` token. A word
    carrying one is split into [token/plain-head..] so the token stays intact.
"""
import re

import pyphen

from textwidth import pixels

_dic = pyphen.Pyphen(lang="et")

# a leading game token like '{PLAYER}' kept atomic; plain letters after it split.
_HEAD_TOKEN = re.compile(r"^(\{[^}]*\})")


def syllables(word):
    """Estonian syllables of `word` (Filosoft/et_EE via pyphen).

    A word carrying a `{...}` game token is split into [token, *syllables] so
    the token is never broken.
    """
    m = _HEAD_TOKEN.match(word)
    if m:
        head, rest = m.group(0), word[m.end():]
        return [head] + (syllables(rest) if rest else [])
    if "{" in word or "}" in word:
        return [word]  # can't safely syllabify around an interior token
    return _dic.inserted(word).split("-")


# Minimum letters a split may leave before the break (head) and after it
# (tail). 2/2 means we never hyphenate just after a single letter, and never
# strand a single letter at the start of the next line -- while still filling
# lines with the longer breaks pyphen offers.
MIN_PREFIX = 2
MIN_SUFFIX = 2


def _syllable_points(word):
    """Offsets after which pyphen allows a (new) hyphen to be inserted."""
    syl = syllables(word)
    pts, pos = [], 0
    for s in syl[:-1]:
        pos += len(s)
        pts.append(pos)
    return pts


def _letters(s):
    """Letters in `s`, ignoring `{TOKEN}`s and any '-' characters."""
    return len(re.sub(r"\{[^}]*\}", "", s).replace("-", ""))


# An uppercase letter after the first position marks a name or an ALL-CAPS
# game term (POKéMON, POKéRUS, LILYCOVE, SAALI) -- possibly with an Estonian
# case ending (POKéMONidele). We never insert a *new* hyphen inside such a
# word, so names are never split; an existing '-' is still a legal break.
_EMBEDDED_CAP = re.compile(r".[A-ZÄÖÜÕŠŽ]")


def _break_points(word):
    """Legal break offsets as (pos, needs_hyphen), left-to-right.

    * An existing '-' in the word is a natural break: the head ends with it,
      so no new hyphen is added (needs_hyphen=False) and it is preferred.
    * pyphen syllable breaks add a '-' (needs_hyphen=True), but never right
      beside an existing '-', and never inside a name/ALL-CAPS term.
    * Every break must leave >=MIN_PREFIX letters before and >=MIN_SUFFIX
      after it, so a word is never split just after one letter.
    """
    cands = {}
    for i, ch in enumerate(word):          # existing hyphens (preferred)
        if ch == "-":
            cands[i + 1] = False
    if not _EMBEDDED_CAP.search(word):     # skip syllable breaks inside names
        for p in _syllable_points(word):   # pyphen syllable breaks
            if word[p - 1:p] == "-" or word[p:p + 1] == "-":
                continue
            cands.setdefault(p, True)
    out = []
    for pos in sorted(cands):
        if _letters(word[:pos]) >= MIN_PREFIX and _letters(word[pos:]) >= MIN_SUFFIX:
            out.append((pos, cands[pos]))
    return out


def wrap(word, room):
    """Split `word` so the head (+ '-' if needed) fits within `room` pixels.

    Returns (head, tail), choosing the break that fills `room` best; or None
    if no clean break fits (caller pushes the whole word to the next line,
    rather than making an ugly one-letter split).
    """
    if room <= 6:
        return None
    best = None
    for pos, needs_hyphen in _break_points(word):
        head = word[:pos] + ("-" if needs_hyphen else "")
        if pixels(head) <= room:
            best = (head, word[pos:])
        else:
            break  # break points are left-to-right; once too wide, stop
    return best


if __name__ == "__main__":
    import sys
    for w in sys.argv[1:] or ["putukapüügivõistlus", "salvestusfailidest",
                              "raadiotorn", "kaubamaja"]:
        print(f"{w:22s} {'-'.join(syllables(w))}")
