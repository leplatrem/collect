FOLDERS := collect collectable
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
	$(UV) sync
	touch $(INSTALL_STAMP)

clean:  ## Delete cache files
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -rf .install.stamp .coverage .mypy_cache $(VERSION_FILE)

lint: $(INSTALL_STAMP)  ## Analyze code base
	$(UV) run ruff check $(FOLDERS)
	$(UV) run ruff format --check $(FOLDERS)
	$(UV) run mypy $(FOLDERS) --ignore-missing-imports
	$(UV) run djlint $(FOLDERS) --lint

format: $(INSTALL_STAMP)  ## Format code base
	$(UV) run ruff check --fix $(FOLDERS)
	$(UV) run ruff format $(FOLDERS)
	$(UV) run djlint $(FOLDERS) --reformat

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

createsuperuser: migrate   ## Create admin user if necessary
	@echo "Ensuring admin user exists with default password..."
	DJANGO_SETTINGS_MODULE=collect.settings $(UV) run bin/createsuperuser.py

demo: $(INSTALL_STAMP) $(ENV_FILE) createsuperuser   ## Load demo data
	$(UV) run manage.py loadfolder admin demo
	@echo "You can now run 'make start'"

test: tests  ## Run unit tests
tests: $(INSTALL_STAMP) $(VERSION_FILE)
	$(UV) run pytest tests --cov-report term-missing --cov-fail-under 100 --cov $(FOLDERS)

$(ENV_FILE):
	cp -n env.local .env

start: $(INSTALL_STAMP) $(ENV_FILE) migrate  ## Start the app
	$(UV) run manage.py runserver
