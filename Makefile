PACKAGE         := laserbeamsize

# -------- venv config --------
PY_VERSION      ?= 3.11
VENV            ?= .venv
PY              := /opt/homebrew/opt/python@$(PY_VERSION)/bin/python$(PY_VERSION)
PYTHON          := $(VENV)/bin/python
SERVE_PY        := $(abspath $(PYTHON))
PIP             := $(VENV)/bin/pip
REQUIREMENTS    := requirements-dev.txt

PROJECT         := laserbeamsize
REPO            := scottprahl/$(PROJECT)
BUILD_APPS      := lab
DOCS_DIR        := docs
HTML_DIR        := $(DOCS_DIR)/_build/html

ROOT            := $(abspath .)
OUT_ROOT        := $(ROOT)/_site
OUT_DIR         := $(OUT_ROOT)/$(PROJECT)
STAGE_DIR       := $(ROOT)/.lite_src
DOIT_DB         := $(ROOT)/.jupyterlite.doit.db

# --- GitHub Pages deploy config ---
PAGES_BRANCH    := gh-pages
WORKTREE        := .gh-pages
REMOTE          := origin

# --- server config (override on CLI if needed) ---
HOST            ?= 127.0.0.1
PORT            ?= 8000

PYTEST          := $(VENV)/bin/pytest
PYLINT          := $(VENV)/bin/pylint
SPHINX          := $(VENV)/bin/sphinx-build
RUFF            := $(VENV)/bin/ruff
BLACK           := $(VENV)/bin/black
PYROMA          := $(PYTHON) -m pyroma
RSTCHECK        := $(PYTHON) -m rstcheck
YAMLLINT        := $(PYTHON) -m yamllint

PYTEST_OPTS     := -q
SPHINX_OPTS     := -T -E -b html -d $(DOCS_DIR)/_build/doctrees -D language=en
NOTEBOOK_RUN    := $(PYTEST) --verbose tests/all_test_notebooks.py

PY_SRC := \
	$(PACKAGE)/*.py \
	tests/*.py

YAML_FILES := \
	.github/workflows/citation.yaml \
	.github/workflows/pypi.yaml \
	.github/workflows/test.yaml

RST_FILES := \
	README.rst \
	CHANGELOG.rst \
	$(DOCS_DIR)/index.rst \
	$(DOCS_DIR)/changelog.rst \
	$(DOCS_DIR)/analysis.rst \
	$(DOCS_DIR)/background.rst \
	$(DOCS_DIR)/display.rst \
	$(DOCS_DIR)/image_tools.rst \
	$(DOCS_DIR)/m2_display.rst \
	$(DOCS_DIR)/m2_fit.rst \
	$(DOCS_DIR)/masks.rst

.PHONY: help
help:
	@echo "Build Targets:"
	@echo "  dist           - Build sdist+wheel locally"
	@echo "  venv           - Create/provision the virtual environment ($(VENV))"
	@echo "  freeze         - Snapshot venv packages to requirements.lock.txt"
	@echo "  html           - Build Sphinx HTML documentation"
	@echo "  test           - Run pytest"
	@echo "Packaging Targets:"
	@echo "  lint           - Run pylint and yamllint"
	@echo "  rcheck         - Release checks (ruff, tests, docs, manifest, pyroma, notebooks)"
	@echo "  manifest-check - Validate MANIFEST"
	@echo "  note-check     - Validate jupyter notebooks"
	@echo "  rst-check      - Validate all RST files"
	@echo "  ruff-check     - Lint all .py and .ipynb files"
	@echo "  pyroma-check   - Validate overall packaging"
	@echo "JupyterLite Targets:"
	@echo "  run            - Clean lite, build, and serve locally"
	@echo "  lite           - Build JupyterLite site into $(OUT_DIR)"
	@echo "  lite-serve     - Serve $(OUT_DIR) at http://$(HOST):$(PORT)"
	@echo "Clean Targets:"
	@echo "  clean          - Remove build caches and docs output"
	@echo "  lite-clean     - Remove JupyterLite outputs"
	@echo "  realclean      - clean + remove $(VENV)"

# venv bootstrap (runs once, or when requirements change)
$(VENV)/.ready: Makefile $(REQUIREMENTS)
	@echo ">> Ensuring venv at $(VENV) using $(PY)"
	@if [ ! -x "$(PY)" ]; then \
		echo "❌ Homebrew Python $(PY_VERSION) not found at $(PY)"; \
		echo "   Try: brew install python@$(PY_VERSION)"; \
		exit 1; \
	fi
	@if [ ! -d "$(VENV)" ]; then \
		"$(PY)" -m venv "$(VENV)"; \
	fi
	@$(PIP) -q install --upgrade pip wheel
	@echo ">> Installing dev requirements from $(REQUIREMENTS)"
	@$(PIP) -q install -r "$(REQUIREMENTS)"
	@touch "$(VENV)/.ready"
	@echo "✅ venv ready"

.PHONY: venv
venv: $(VENV)/.ready
	@:

# Snapshot exact packages (useful for CI/repro)
.PHONY: freeze
freeze: $(VENV)/.ready
	@$(PIP) freeze > requirements.lock.txt
	@echo "📌 Wrote requirements.lock.txt"

.PHONY: dist
dist: $(VENV)/.ready ## [release] Build sdist and wheel (PEP 517)
	$(PYTHON) -m build
	
.PHONY: test
test: $(VENV)/.ready
	$(PYTEST) $(PYTEST_OPTS) tests

.PHONY: html
html: $(VENV)/.ready       ## Build HTML documentation using Sphinx
	@mkdir -p "$(HTML_DIR)"
	$(SPHINX) $(SPHINX_OPTS) "$(DOCS_DIR)" "$(HTML_DIR)"
	@command -v open >/dev/null 2>&1 && open "$(HTML_DIR)/index.html" || true

.PHONY: lint
lint: $(VENV)/.ready      ## Run pylint and yamllint
	-@$(PYLINT) $(PY_SRC)
	-@$(YAMLLINT) $(YAML_FILES)

.PHONY: rst-check
rst-check: $(VENV)/.ready    ## Validate all RST files
	-@$(RSTCHECK) README.rst
	-@$(RSTCHECK) CHANGELOG.rst
	-@$(RSTCHECK) $(DOCS_DIR)/index.rst
	-@$(RSTCHECK) $(DOCS_DIR)/changelog.rst
	-@$(RSTCHECK) --ignore-directives automodapi $(DOCS_DIR)/analysis.rst
	-@$(RSTCHECK) --ignore-directives automodapi $(DOCS_DIR)/background.rst
	-@$(RSTCHECK) --ignore-directives automodapi $(DOCS_DIR)/display.rst
	-@$(RSTCHECK) --ignore-directives automodapi $(DOCS_DIR)/image_tools.rst
	-@$(RSTCHECK) --ignore-directives automodapi $(DOCS_DIR)/m2_display.rst
	-@$(RSTCHECK) --ignore-directives automodapi $(DOCS_DIR)/m2_fit.rst

.PHONY: note-check
note-check: $(VENV)/.ready    ## Validate notebooks
	$(PYTEST) --verbose tests/all_test_notebooks.py
	@echo "✅ Notebook check complete"

.PHONY: ruff-check
ruff-check: $(VENV)/.ready
	$(RUFF) check

.PHONY: manifest-check
manifest-check: $(VENV)/.ready
	check-manifest

.PHONY: pyroma-check
pyroma-check: $(VENV)/.ready
	$(PYROMA) -d .

.PHONY: rcheck
rcheck: realclean ruff-check test lint rst-check html manifest-check pyroma-check note-check lite dist
	@echo "✅ Release checks complete"

.PHONY: lite
lite: $(VENV)/.ready
	@echo ">> Ensuring root jupyter-lite.json exists"; \
	[ -f $(ROOT)/jupyter-lite.json ] || { echo "❌ Missing jupyter-lite.json"; exit 1; }

	@echo ">> Clearing doit cache (if present)"
	@/bin/rm -f "$(DOIT_DB)"

	@echo ">> Staging notebooks from docs/ (excluding readme_images.ipynb) -> $(STAGE_DIR)"
	@/bin/rm -rf "$(STAGE_DIR)"; mkdir -p "$(STAGE_DIR)"
	@/bin/cp docs/*.ipynb "$(STAGE_DIR)"

	@echo ">> Building JupyterLite into $(OUT_DIR)"
	@/bin/rm -rf "$(OUT_DIR)"; mkdir -p "$(OUT_DIR)"
	"$(PYTHON)" -m jupyter lite build \
	  --apps lab \
	  --contents "$(STAGE_DIR)" \
	  --LiteBuildApp.lite_dir="$(ROOT)" \
	  --LiteBuildApp.output_dir="$(OUT_DIR)"

	@touch "$(OUT_DIR)/.nojekyll"
	@echo "✅ Build complete -> $(OUT_DIR)"

.PHONY: lite-serve
lite-serve:
	[ -d $(OUT_ROOT) ] || { echo "❌ run 'make lite' first"; exit 1; }
	@echo ">> Serving _site at http://127.0.0.1:8000/laserbeamsize/?disableCache=1"
	python3 -m http.server -d "$(OUT_ROOT)" --bind 127.0.0.1 8000

.PHONY: run
run: lite-clean lite lite-serve

.PHONY: lite-clean
lite-clean:
	@echo ">> Cleaning site, stage, caches, and isolated lite_dir"
	@/bin/rm -rf "$(STAGE_DIR)"
	@/bin/rm -rf "$(OUT_ROOT)"
	@/bin/rm -rf ".lite_root"
	@/bin/rm -rf "$(DOIT_DB)"
	@/bin/rm -rf "_output"
	@/bin/rm -rf "__pycache__"
	@/bin/rm -rf  ".pytest_cache"

.PHONY: lite-deploy
lite-deploy: lite
	@echo ">> Sanity checks before deploy"
	@test -d "$(OUT_DIR)" || { echo "❌ Missing $(OUT_DIR)"; exit 1; }
	@test -f "$(OUT_DIR)/index.html" || { echo "❌ Missing $(OUT_DIR)/index.html"; exit 1; }
	@test -f "$(OUT_DIR)/jupyter-lite.json" || { echo "❌ Missing $(OUT_DIR)/jupyter-lite.json"; exit 1; }
	@grep -q '"baseUrl": *"/laserbeamsize/"' "$(OUT_DIR)/jupyter-lite.json" || { \
	  echo "❌ jupyter-lite.json baseUrl is not /laserbeamsize/"; exit 1; }

	@echo ">> Ensure $(PAGES_BRANCH) branch exists"
	@if ! git show-ref --verify --quiet refs/heads/$(PAGES_BRANCH); then \
	  CURRENT=$$(git branch --show-current); \
	  git switch --orphan $(PAGES_BRANCH); \
	  git commit --allow-empty -m "Initialize $(PAGES_BRANCH)"; \
	  git switch $$CURRENT; \
	fi

	@echo ">> Ensure worktree at $(WORKTREE)"
	@if [ ! -d "$(WORKTREE)/.git" ]; then \
	  rm -rf "$(WORKTREE)"; \
	  git worktree add --checkout "$(WORKTREE)" "$(PAGES_BRANCH)"; \
	else \
	  git -C "$(WORKTREE)" fetch "$(REMOTE)" "$(PAGES_BRANCH)"; \
	  git -C "$(WORKTREE)" reset --hard "$(REMOTE)/$(PAGES_BRANCH)" || true; \
	fi

	@echo ">> Sync $(OUT_DIR) -> $(WORKTREE) (root of Pages)"
	# Keep CNAME if you use a custom domain; otherwise it's fine to delete it.
	@rsync -a --delete \
	  --exclude ".git/" \
	  --exclude ".gitignore" \
	  "$(OUT_DIR)/" "$(WORKTREE)/"

	@echo ">> Ensure .nojekyll at Pages root"
	@touch "$(WORKTREE)/.nojekyll"

	@echo ">> Commit & push if there are changes"
	@cd "$(WORKTREE)" && \
	  git add -A && \
	  if git diff --quiet --cached; then \
	    echo "✅ No changes to deploy"; \
	  else \
	    git commit -m "Deploy $$(date -u +'%Y-%m-%d %H:%M:%S UTC')" && \
	    git push "$(REMOTE)" "$(PAGES_BRANCH)"; \
	    echo "✅ Deployed to https://scottprahl.github.io/laserbeamsize/"; \
	  fi

.PHONY: clean
clean: ## Remove cache, build artifacts, docs output, and JupyterLite build (but keep config)
	@echo "==> Cleaning build artifacts"	
	@find . -name '__pycache__' -type d -exec rm -rf {} +
	@find . -name '.DS_Store' -type f -delete
	@find . -name '.ipynb_checkpoints' -type d -prune -exec rm -rf {} +
	@rm -rf \
		.DS_store \
		.cache \
		.eggs \
		.pytest_cache \
		.ruff_cache \
		.virtual_documents \
		dist \
		build \
		$(PACKAGE).egg-info \
		$(DOCS_DIR)/_build \
		$(DOCS_DIR)/api \

.PHONY: realclean
realclean: lite-clean clean
	@/bin/rm -rf "$(VENV)"

