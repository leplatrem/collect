INSTALL_STAMP_PYTHON := .install.python.stamp
INSTALL_STAMP_NODE := .install.node.stamp
ENV_FILE := .env
UV := $(shell command -v uv 2> /dev/null)

.PHONY: help clean lint format migrate demo tests browser-tests

help:
	@echo "Please use 'make <target>' where <target> is one of the following commands.\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo "\nCheck the Makefile to know exactly what each target is doing."

install: $(INSTALL_STAMP_PYTHON)  ## Install Python dependencies
$(INSTALL_STAMP_PYTHON): pyproject.toml uv.lock
	@if [ -z $(UV) ]; then echo "uv could not be found. See https://docs.astral.sh/uv/"; exit 2; fi
	$(UV) --version
	$(UV) sync --locked
	touch $(INSTALL_STAMP_PYTHON)

install-node: $(INSTALL_STAMP_NODE)  ## Install Node dependencies
$(INSTALL_STAMP_NODE): package.json package-lock.json
	npm ci
	npx playwright install firefox
	touch $(INSTALL_STAMP_NODE)

clean:  ## Delete cache files
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -rf $(INSTALL_STAMP_PYTHON) $(INSTALL_STAMP_NODE) ./node_modules/ .coverage .*_cache .venv

lint: $(INSTALL_STAMP_PYTHON) $(INSTALL_STAMP_NODE)  ## Analyze code base
	$(UV) run ruff check src/
	$(UV) run ruff format --check src/
	$(UV) run djlint src/ --lint
	$(UV) run mypy src/ --ignore-missing-imports
	npx prettier --check tests/

format: $(INSTALL_STAMP_PYTHON) $(INSTALL_STAMP_NODE)  ## Format code base
	$(UV) run ruff check --fix src/
	$(UV) run ruff format src/
	$(UV) run djlint src/ --reformat
	npx prettier --write tests/

migrate:  ## Run pending migrations if needed
	@echo "Checking for unapplied migrations..."
	@$(UV) run sh -c '\
		if python manage.py showmigrations --plan | grep "\[ \]" > /dev/null; then \
			echo "Running migrations..."; \
			python manage.py migrate; \
		else \
			echo "No migrations to apply."; \
		fi \
	'

demo: $(INSTALL_STAMP_PYTHON) $(ENV_FILE) migrate   ## Create demo data
	$(UV) run manage.py smart_create_user --admin admin s3cr3t
	$(UV) run manage.py smart_create_user testuser testpass
	$(UV) run manage.py loadfolder admin demo
	@echo "You can now run 'make start'"

test: tests  ## Run unit tests
tests: $(INSTALL_STAMP_PYTHON) $(ENV_FILE)
	$(UV) run pytest --cov-report term-missing --cov-fail-under 90 --cov src src/

$(ENV_FILE):
	cp --update=none env.local .env

start: $(INSTALL_STAMP_PYTHON) $(ENV_FILE) migrate  ## Start the app
	$(UV) run manage.py runserver

browser-tests: $(INSTALL_STAMP_NODE)  ## Run browser end-to-end tests
	npx playwright test
