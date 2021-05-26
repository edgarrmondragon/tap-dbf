NAME := tap_dbf
EXECUTABLE := tap-dbf
POETRY := $(shell command -v poetry 2> /dev/null)

.PHONY: lint
lint:
	$(POETRY) run flake8 $(NAME)
	$(POETRY) run pydocstyle $(NAME)
	$(POETRY) run black --check $(NAME)

.PHONY: format
format:
	$(POETRY) run black $(NAME)
	$(POETRY) run isort $(NAME)

.PHONY: about
.SILENT: about
about:
	$(POETRY) run $(EXECUTABLE) --about --format json
