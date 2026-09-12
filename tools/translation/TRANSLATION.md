# Estonian translation tooling

Helpers for translating pokeemerald's text into Estonian, adapted from the
`pokecrystal-et` / `pocketrgb-en` workflow. All Python, run from a project
virtualenv. pokeemerald keeps text in two places and both are handled:

* **ASM** — `.string "..."` blocks in `data/{text,maps,scripts}/**.inc`.
* **C** — `_("...")` literals in selected `src/` and `include/` prose files.

Proper-noun NAME tables (species/move/item/ability/type/trainer names) stay
English by convention and are excluded from extraction.

## Setup (once)

```bash
make -C tools/translation venv
```

Homebrew's Python is PEP 668 "externally managed", so the deps (`pyphen`,
`phunspell`, `termcolor`, `pillow`) live in `tools/translation/.venv`
(git-ignored).

## The loop: extract → translate → writeback → validate → build

### 1. extract — English into a worksheet

```bash
make -C tools/translation extract
# -> et_untranslated.json : [{file,label,box,kind,en,et:""}]
```

A label's `.string` fragments concatenate into one stream ending in `$`; `\p`
splits it into boxes (message windows), `\n`/`\l` are soft line breaks reflowed
into one paragraph per box. C strings split the same way. Game tokens
(`{PLAYER}`, `{STR_VAR_1}`, `{PKMN}`, …) are kept verbatim.

### 2. translate — machine-draft via TartuNLP + memory

```bash
make -C tools/translation translate                 # whole worksheet
make -C tools/translation translate ARGS="--limit 50"   # small trial
```

`translate.py` fills each `et`: exact matches from the human-reviewed pokered
memory (`pocketred_et_memory.json`) win; the rest is drafted by the TartuNLP NMT
API (https://api.tartunlp.ai). Each `{...}` token and POKéMON/POKé is masked
before the call and restored after, so the model can't break them; rows whose
token set still changed are flagged `check`. The **glossary** (`glossary.json`)
forces element-type roots, fixes word-sense misses, and keeps all-caps
names/places English. Unique strings are translated once and fanned out; the run
is resumable. Set `TARTUNLP_API_KEY` for higher rate limits.

The NMT output is a **draft** — review `et` rows before trusting them. To
re-translate only machine rows after editing the glossary:

```bash
make -C tools/translation translate ARGS="et_draft.json --out et_draft.json --redo-mt"
```

### 3. fonts — draw the õ/Õ glyphs (once)

```bash
make -C tools/translation fonts
```

pokeemerald's charmap has ä/ö/ü but not õ; `fix_fonts.py` draws õ/Õ into the
five Latin font sheets by splicing a tilde onto o/O (reusing the unused ô/Ô
slots — see `charmap.txt`). Idempotent. š/ž have no caron glyph and fall back to
s/z via the charmap.

### 4. writeback — bake translations into the sources

```bash
make -C tools/translation writeback                 # every safe block
make -C tools/translation writeback ARGS="--dry-run"
make -C tools/translation writeback ARGS="data/text" # limit to path substrings
```

`writeback.py` re-wraps each box to the 208px box width (Estonian hyphenation
via `syllabify`/pyphen), emits `.string` lines (`\n` first break, `\l` after,
`\p` between boxes, `$` at end), and splices them in — leaving surrounding code
untouched. Non-charmap punctuation is sanitized (straight quotes → curly, `...`
→ `…`). Conservative: a block is rewritten only when it is a clean `.string`
run whose box count matches the translation and every box is non-empty; C arrays
with a byte cap that would overflow are skipped. Reruns are safe.

### 5. validate + build

```bash
make -C tools/translation check      # .string lines over 208px
make -C tools/translation spell      # et_EE spelling of et fields
gmake modern -j8                     # build the ROM (from repo root)
```

## Files

| file | purpose |
|---|---|
| `extract.py` | English ASM/C text → worksheet |
| `translate.py` | NMT + memory + glossary draft |
| `writeback.py` | re-wrap & splice translations into sources |
| `fix_fonts.py` | draw õ/Õ into the Latin fonts |
| `textwidth.py` | proportional on-screen pixel width (charmap + fonts.c) |
| `syllabify.py` | Estonian hyphenation (pyphen) |
| `check_lines.py` | flag over-wide `.string` lines |
| `spellcheck.py` | et_EE spell-check of `et` fields |
| `glossary.json` | termbase (types, term fixes, caps overrides) |
| `pocketred_et_memory.json` | human-reviewed pokered Estonian memory |
