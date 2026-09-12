# Estonian translation tooling for pokeemerald.
#
# Set up once:   make -C tools/translation venv
# Pipeline:      make -C tools/translation extract      # English -> worksheet
#                make -C tools/translation translate     # NMT + memory draft
#                make -C tools/translation fonts          # draw õ/Õ into fonts
#                make -C tools/translation writeback      # draft -> sources
# Validate:      make -C tools/translation check          # line widths
#                make -C tools/translation spell          # et_EE spelling
#
# Then build the ROM from the repo root:  gmake modern -j8
.PHONY: venv extract translate writeback fonts check spell clean-venv

PY := .venv/bin/python

venv: .venv/pyvenv.cfg
.venv/pyvenv.cfg: requirements.txt
	python3 -m venv .venv
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -r requirements.txt
	@touch .venv/pyvenv.cfg

extract: venv
	$(PY) extract.py $(ARGS)

translate: venv
	$(PY) translate.py $(ARGS)

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
