# Estonian translation tooling

The translation is **one file**: [`et.json`](et.json) — the single source of truth.
The game's `data/`/`src/` sources are **generated** from it at build time and are
**not** committed (they stay pristine English in git; `writeback` applies the
Estonian, then you build).

## et.json

A flat list of boxes, each:

```json
{ "file": "data/text/foo.inc", "label": "gText_Bar", "box": 0,
  "kind": "asm", "en": "English text", "et": "Eesti tekst", "et_src": "human" }
```

- keyed by **location** (`file` / `label` / `box`); `en` is the English, `et` the Estonian.
- `et_src`: `human` (hand/curated), `memory` (pokered reuse), `mt` (leftover machine
  translation — **suspect quality, to be replaced by hand**), `""` (untranslated → English).
- ASM boxes are one message window; a label's `\n`/`\l` line breaks are reflowed into
  one paragraph per box and re-wrapped by `writeback` to the 208px box width.
- C `_()` strings carry a byte **cap** (`maxlen`) for fixed-size arrays (names,
  categories); `writeback` skips a translation that would overflow its buffer.

**To translate/fix a box:** edit its `et` in `et.json` (set `et_src` to `human`).
There is no separate override file — everything lives here.

`literals.json` is the one exception: exact `"English" → "Estonian"` replacements for
hand-laid-out strings with absolute `{CLEAR_TO ...}` positioning that must **not** be
re-wrapped (e.g. the shard-trade board). Applied verbatim by `writeback`.

## Workflow

```bash
make -C tools/translation venv          # one-time: python venv + deps
make -C tools/translation extract       # merge NEW English boxes into et.json
                                        #   (preserves existing et; new boxes get et="")
make -C tools/translation fonts         # draw õ/Õ etc. into the Latin fonts (once)
make -C tools/translation writeback     # et.json -> data/ + src/   (add ARGS="--with-c" for C files)
make -C tools/translation check         # flag .string lines over 208px
make -C tools/translation spell         # et_EE spellcheck of et fields
gmake modern -j8                        # build the ROM (from repo root)
```

Typical build from a clean checkout:

```bash
git checkout -- data/ src/                                   # pristine English
make -C tools/translation writeback ARGS="--with-c"          # apply et.json
gmake modern -j8
```

`extract` only needs re-running when you add a **new** source file/target (see
`ASM_DIRS`/`ASM_FILES`/`C_FILES` in `extract.py`); it merges, never overwrites `et`.

## What's translated

Dialogue, descriptions, battle text, menus/UI, Pokédex categories, contest terms,
type names + Gen 1 move names (reused from `../pocketrgb-en`). **Kept English** by
convention: Pokémon / trainer / person / place **names**, Gen 2-3 move names, and the
`mt`-tagged boxes still awaiting hand translation.

## Files

| file | purpose |
|---|---|
| `et.json` | the translation (single source of truth) |
| `literals.json` | verbatim replacements for absolute-positioned strings |
| `extract.py` | English → `et.json` (merge, preserving `et`) |
| `writeback.py` | `et.json` → sources (re-wrap + splice) |
| `syllabify.py` / `textwidth.py` | Estonian hyphenation + proportional pixel width |
| `check_lines.py` / `spellcheck.py` | validation |
| `fix_fonts.py` | draw õ/Õ into the Latin font PNGs |
| `GRAPHICS_TODO.md` | remaining text-in-graphics to redraw |

Machine translation (TartuNLP) was tried and abandoned — poor quality; the `mt`-tagged
`et.json` rows are its leftovers, being replaced by hand. (History in git.)
