# Ambiverse Studio — common tasks. A visitor only needs `make demo`.

PY   ?= $(shell for p in python3.14 python3.13 python3.12 python3; do command -v $$p >/dev/null && { echo $$p; break; }; done)
VENV := server/venv
BIN  := $(VENV)/bin

.PHONY: setup demo dev web test demo-reset

setup: $(BIN)/.installed web/node_modules/.installed

$(BIN)/.installed: server/requirements.txt server/requirements-dev.txt
	@$(PY) -c 'import sys; sys.exit(sys.version_info < (3, 12))' || \
		{ echo "Python 3.12+ is required (found $$($(PY) --version))"; exit 1; }
	test -d $(VENV) || $(PY) -m venv $(VENV)
	$(BIN)/pip install -q -r server/requirements-dev.txt
	touch $@

web/node_modules/.installed: web/package-lock.json
	npm --prefix web ci
	touch $@

# One process on http://127.0.0.1:4700: the built UI plus generated demo data — no keys needed.
demo: setup
	npm --prefix web run build
	STUDIO_DEMO=1 $(BIN)/uvicorn app:app --app-dir server --host 127.0.0.1 --port 4700

# API with autoreload on :4700 — run `make web` in a second terminal for the UI on :5175.
dev: setup
	$(BIN)/uvicorn app:app --app-dir server --host 127.0.0.1 --port 4700 --reload --reload-dir server

web:
	npm --prefix web run dev

# API tests (demo mode, throwaway data dir) + web lint, typecheck and build.
test: setup
	$(BIN)/python -m pytest -q server/tests
	npm --prefix web run lint
	npm --prefix web run build

# Forget the generated demo data; it is rebuilt on the next start.
demo-reset:
	rm -rf data/demo
