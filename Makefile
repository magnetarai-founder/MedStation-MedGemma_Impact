.PHONY: format lint lint-strict

format:
	black .

lint:
	ruff check . || true
	flake8 || true

# Run linting without project ignores (expect noise; use for deep audits)
lint-strict:
	ruff check . --isolated --line-length 120 --exclude artifacts,tmp,.venv,venv,ENV,env,build,dist || true
	flake8 --isolated --max-line-length 120 --extend-ignore E203,W503 --exclude artifacts,tmp,.venv,venv,ENV,env,build,dist || true
