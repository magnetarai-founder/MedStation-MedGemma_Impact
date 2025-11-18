.PHONY: check-imports help

help:
	@echo "ElohimOS Development Tasks"
	@echo ""
	@echo "Available targets:"
	@echo "  check-imports    - Validate Python import structure in apps/backend/api/"
	@echo "  help            - Show this help message"

check-imports:
	@echo "Validating Python imports..."
	@python3 scripts/check_imports.py
