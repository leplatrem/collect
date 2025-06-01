INSTALL_STAMP := .install.stamp
ENV_FILE := .env
UV := $(shell command -v uv 2> /dev/null)

.PHONY: help clean lint format migrate demo tests

help:
	@echo "Please use 'make <target>' where <target> is one of the following commands.\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo "\nCheck the Makefile to know exactly what each target is doing."

install: $(INSTALL_STAMP)  ## Install dependencies
$(INSTALL_STAMP): pyproject.toml uv.lock
	@if [ -z $(UV) ]; then echo "uv could not be found. See https://docs.astral.sh/uv/"; exit 2; fi
	$(UV) --version
	$(UV) sync --locked
	$(UV) run playwright install firefox
	touch $(INSTALL_STAMP)

clean:  ## Delete cache files
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -rf .install.stamp .coverage .mypy_cache

lint: $(INSTALL_STAMP)  ## Analyze code base
	$(UV) run ruff check src/
	$(UV) run ruff format --check src/
	$(UV) run djlint src/ --lint
	$(UV) run mypy src/ --ignore-missing-imports

format: $(INSTALL_STAMP)  ## Format code base
	$(UV) run ruff check --fix src/
	$(UV) run ruff format src/
	$(UV) run djlint src/ --reformat

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

createadminuser: migrate   ## Create admin user if necessary
	@echo "Ensuring admin user exists with default password..."
	$(UV) run manage.py smart_create_user --admin admin s3cr3t

demo: $(INSTALL_STAMP) $(ENV_FILE) createadminuser   ## Load demo data
	$(UV) run manage.py loadfolder admin demo
	@echo "You can now run 'make start'"

test: tests  ## Run unit tests
tests: $(INSTALL_STAMP)
	$(UV) run pytest --cov-report term-missing --cov-fail-under 90 --cov src src/

browser-test: $(INSTALL_STAMP)  ## Run browser end-to-end tests
	$(UV) run pytest --base-url http://localhost:8000 tests/

$(ENV_FILE):
	cp -n env.local .env

start: $(INSTALL_STAMP) $(ENV_FILE) migrate  ## Start the app
	$(UV) run manage.py runserver
