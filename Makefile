FOLDERS := collect collectable
INSTALL_STAMP := .install.stamp
POETRY := $(shell command -v poetry 2> /dev/null)

.PHONY: help clean lint format tests

help:
	@echo "Please use 'make <target>' where <target> is one of the following commands.\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo "\nCheck the Makefile to know exactly what each target is doing."

install: $(INSTALL_STAMP)  ## Install dependencies
$(INSTALL_STAMP): pyproject.toml poetry.lock
	@if [ -z $(POETRY) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(POETRY) --version
	$(POETRY) install --no-ansi --no-interaction --verbose
	touch $(INSTALL_STAMP)

clean:  ## Delete cache files
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -rf .install.stamp .coverage .mypy_cache $(VERSION_FILE)

lint: $(INSTALL_STAMP)  ## Analyze code base
	$(POETRY) run ruff check $(FOLDERS)
	$(POETRY) run ruff format --check $(FOLDERS)
	$(POETRY) run mypy $(FOLDERS) --ignore-missing-imports
	$(POETRY) run djlint $(FOLDERS) --lint

format: $(INSTALL_STAMP)  ## Format code base
	$(POETRY) run ruff check --fix $(FOLDERS)
	$(POETRY) run ruff format $(FOLDERS)
	$(POETRY) run djlint $(FOLDERS) --reformat

test: tests  ## Run unit tests
tests: $(INSTALL_STAMP) $(VERSION_FILE)
	$(POETRY) run pytest tests --cov-report term-missing --cov-fail-under 100 --cov $(FOLDERS)

start: $(INSTALL_STAMP) ## Start the app
	$(POETRY) run python manage.py runserver

