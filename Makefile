NAME := tap_dbf
EXECUTABLE := tap-dbf
POETRY := $(shell command -v poetry 2> /dev/null)

.PHONY: lint
lint:
	$(POETRY) run ruff check --fix --show-fixes $(NAME)

.PHONY: format
format:
	$(POETRY) run ruff format $(NAME)

.PHONY: about
.SILENT: about
about:
	$(POETRY) run $(EXECUTABLE) --about --format json
