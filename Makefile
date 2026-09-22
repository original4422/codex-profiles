PYTHON ?= python3

.PHONY: check format smoke assets

check:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m unittest discover -s tests -v
	xcrun swift-format lint --strict src/*.swift
	@for source in src/*.swift; do xcrun swiftc -typecheck -framework AppKit "$$source" || exit 1; done

format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .
	xcrun swift-format format --in-place src/*.swift

smoke:
	$(PYTHON) tests/smoke_install.py

assets:
	$(PYTHON) scripts/render_overview.py
