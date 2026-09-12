# Estonian translation tooling for pokeemerald.
#
# Set up once:   make -C tools/translation venv
# Pipeline:      make -C tools/translation extract      # merge new English boxes into et.json
#                make -C tools/translation fonts          # draw õ/Õ into fonts
#                make -C tools/translation writeback      # et.json -> sources
# Validate:      make -C tools/translation check          # line widths
#                make -C tools/translation spell          # et_EE spelling
#
# Translations live in et.json (single source of truth, hand-edited).
# Then build the ROM from the repo root:  gmake modern -j8
.PHONY: venv extract writeback fonts check spell clean-venv

PY := .venv/bin/python

venv: .venv/pyvenv.cfg
.venv/pyvenv.cfg: requirements.txt
	python3 -m venv .venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -r requirements.txt
	@touch .venv/pyvenv.cfg

extract: venv
	$(PY) extract.py $(ARGS)

writeback: venv
	$(PY) writeback.py $(ARGS)

fonts: venv
	$(PY) fix_fonts.py

check: venv
	$(PY) check_lines.py $(ARGS)

spell: venv
	$(PY) spellcheck.py $(ARGS)

clean-venv:
	$(RM) -r .venv
