# Graphics with baked-in English text — localization checklist

These are UI strings drawn as **tile art / pixel glyphs** (not `_()` font strings), so
the text-translation pipeline never touched them. Each must be redrawn by hand in the
image's own indexed palette. Estonian below is proposed to match `menus.json` style
(ALL-CAPS, established terms); adjust freely.

**Guiding rule — match the in-game text.** The text pass kept most short ALL-CAPS labels
**English** (`keep_caps`) and localized only a curated set (see `menus.json`). To keep the
game internally consistent, a graphic should be localized the same way its text twin was:

- **Tier 1 — localize now.** The matching text is already Estonian (or it's a pure-graphic
  prompt with no text twin). Redrawing these makes the graphic agree with the game.
- **Tier 2 — English today; localize only if you also flip the text.** The matching
  in-game text (`gText_*`) is still English by deliberate glossary choice (type names,
  contest conditions, POWER, RIBBONS, PARTY, OK/BACK, facility names…). If you want these
  in Estonian, say so and I'll change the `_()` strings too, so text + graphic agree.
- **Tier 3 — brand / logo.** You asked to localize these; they're stylized lettering.

Legend: `[ ]` = to do · `EN → ET` · `(keep)` = leave English · widths are the tile cell,
watch for overflow on the long ones.

---

## ✅ Done
- [x] `title_screen/press_start.png` — PRESS START → **VAJUTA START** (copyright rows + palette preserved)

---

## Tier 1 — localize now (text twin already Estonian, or pure prompt)

- [ ] `battle_frontier/tourney_buttons.png` — CANCEL → **TÜHISTA** · EXIT → **VÄLJU**
- [ ] `pokenav/options/cancel.png` — CANCEL → **TÜHISTA**
- [ ] `slot_machine/menu.png` — CANCEL → **TÜHISTA** · QUIT → **LÕPETA** · INFO → **INFO** (unchanged)
      · CREDIT / PAYOUT / BIG BONUS / REG / REPLAY / POWER → see Tier 2 · `B` `SELECT` = hardware buttons (keep)
- [ ] `pokedex/menu.png` — CANCEL → **TÜHISTA** (rest of this sheet is Tier 2 below)
- [ ] `pokedex/search_menu.png` — CANCEL → **TÜHISTA** · OK → **OK** (unchanged) (rest Tier 2)
- [ ] `pokemon_storage/menu.png` — CANCEL → **TÜHISTA** (rest Tier 2)
- [ ] `union_room_chat/r_button_labels.png` — REGISTER → **REGISTREERI** · `A` `A+B` combos = hardware (keep)

Pure-graphic prompts (no text twin) — keep as-is unless you want them changed:
- [ ] `link/321start.png` — “3 2 1 START” → START **(keep**, matches `START→START` in menus.json)
- [ ] `berry_blender/start.png` — START! → **(keep)**
- [ ] `bag/select_button.png`, `easy_chat/start_select_buttons.png` — **SELECT / START = hardware button names (keep)**
- [ ] `naming_screen/ok_button.png` — OK → **OK** (unchanged) · `back_button.png` — BACK → **TAGASI** (Tier 2 word, but it's a pure button)

---

## Tier 2 — English today; localize only if we also flip the matching `_()` text

Proposed Estonian is given so you can decide per-item. Say “localize Tier 2” (all or a
subset) and I'll update the corresponding `gText_*` strings in the same pass.

**Pokédex info menu — `pokedex/menu.png`** (tight cells; abbreviations noted)
- [ ] AREA → **ALA** · CRY → **HÄÄL** · SIZE → **SUURUS**
- [ ] BACK TO LIST → **TAGASI LOENDISSE** (long — may need **LOENDISSE**)
- [ ] LIST TOP → **LOENDI ALGUS** · LIST BOTTOM → **LOENDI LÕPP**
- [ ] BACK TO POKéDEX → **TAGASI POKéDEXi** · CLOSE POKéDEX → **SULGE POKéDEX**

**Pokédex search — `pokedex/search_menu.png`**
- [ ] NAME → **NIMI** · ORDER → **JÄRJEKORD** · MODE → **REŽIIM** · COLOR → **VÄRV**
- [ ] TYPE → **TÜÜP** · SHIFT → **VAHETUS** · SEARCH → **OTSI**

**Move/type info — `interface/menu_info.png`**
- [ ] TYPE → **TÜÜP** · POWER → **JÕUD** · ACCURACY → **TÄPSUS** · PP → **PP** (keep) · EFFECT → **EFEKT**
- [ ] the 18 type names (NORMAL, FIRE, WATER…DRAGON, ???) — **recommend KEEP ENGLISH**
      (they're English everywhere in-game: `battle_main.c gTypeNames`, easy-chat, etc.)

**PokéNav — `pokenav/options/*.png` + `pokenav/left_headers/*.png`** (two copies each)
- [ ] PARTY → **SALK** · SEARCH → **OTSI** · RIBBONS → **LINDID** · CONDITION → **SEISUND**
- [ ] MATCH CALL → **KÕNED** (or keep — feature name) · HOENN MAP → **HOENN KAART** (HOENN = name)
- [ ] MAIN MENU → **PEAMENÜÜ** · SWITCH OFF → **LÜLITA VÄLJA**
- [ ] COOL / BEAUTY / CUTE / SMART / TOUGH → **LAHE / ILUS / NUNNU / TARK / KARM**
      — but these are English in text (`gText_Cool=_("COOL")`, contests, etc.); flip both or neither.

**PC storage — `pokemon_storage/menu.png`**
- [ ] PKMN DATA → **POKéMONi ANDMED** · PARTY POKéMON → **SALGA POKéMON**
- [ ] CLOSE BOX → **SULGE KAST** · BOX → **KAST**

**Slot machine — `slot_machine/menu.png`**
- [ ] CREDIT → **KREDIIT** · PAYOUT → **VÄLJAMAKSE** · BIG BONUS → **SUUR BOONUS**
- [ ] REPLAY → **KORDUS** · REG (regular) → **TAVA** · POWER → **JÕUD**
- [ ] `roulette/credit.png` — CREDIT → **KREDIIT**

**Pokéblock — `pokeblock/menu.png`**
- [ ] FEEL → **TUNNE** (+ any flavor labels SPICY/DRY/SWEET/BITTER/SOUR if present on the sheet → ÄGE/KUIV/MAGUS/MÕRU/HAPU)

**Region-map facility captions — `pokenav/region_map/city_zoom_text.png`**
- [ ] POKéMON CENTER / MART / GYM → **POKéMONi KESKUS / POOD / SAAL**
- [ ] BATTLE TENT → **LAHINGUTELK** · POKéMON CONTEST → **POKéMONi VÕISTLUS**
- [ ] note: these are English in text today (`gText_PokemonCenter=_("POKéMON CENTER")`), so
      flipping them means updating map/facility text too — biggest consistency footprint.

**Naming keyboard mode — `naming_screen/page_swap_{upper,lower,others}.png`**
- [ ] UPPER → **SUURED** · lower → **väiksed** · others → **muud**  (keyboard case toggle)
- [ ] `naming_screen/back_button.png` — BACK → **TAGASI**

---

## Tier 3 — brand / logo (you asked to localize)

- [ ] `title_screen/emerald_version.png` — EMERALD (name, keep) + VERSION → **VERSIOON**
      → renders as **EMERALD / VERSIOON**
- [ ] `berry_fix/logo.png` + `berry_fix/window.png` — Berry Program Update utility screen
      (boot tool). Text is dark-on-dark; I'll extract exact wording if you want to do this one.
- [ ] `battle_transitions/frontier_logo*.png` — “BATTLE FRONTIER” — **recommend keep**
      (facility proper name, English throughout the game)
- [ ] `intro/copyright.png`, `credits/the_end_copyright.png` — © Nintendo / Creatures /
      GAME FREAK legal boilerplate — **recommend keep** (legal text, matches the title copyright line we preserved)

---

## Not text (checked, nothing to do)
`summary_screen/a_button.png` `b_button.png` (hardware A/B) · `party_menu/bg.png` (HP bars) ·
`shop/menu.png` `bag/menu.png` `naming_screen/menu.png` `trade/menu.png` (window chrome / digits) ·
all `pokemon/*`, `object_events/*`, `trainers/*`, wallpapers, `text_window/*`, weather, battle-anim sprites.
