# ElohimOS — AI-Powered Data Platform

**Copyright (c) 2025 MagnetarAI, LLC**

Local, offline‑first Excel → SQL → Results with AI assistance. DuckDB + Pandas under the hood, React web UI on top. Redshift‑compat shims make real‑world SQL less painful (LIKE/ILIKE autocast, recursive CTE fix, null::type handling, identifier cleaning).

## Quickstart

Web UI
- Run `./elohim` to start the application
- This creates a venv, installs web-only deps, and starts backend + frontend
- Frontend: http://localhost:5173 (proxied to backend at http://localhost:8000)

Notes:
- Web path uses `web_requirements.txt` and does not install PySide6.
- DuckDB may attempt to install/load optional extensions for direct Excel access. If unavailable, the app falls back to pandas‑based reading automatically.
- No external services required; enrichment is local‑only.
- Parquet exports require `pyarrow` (included). If Parquet export fails in your environment, install `pyarrow` and retry.

## Using It

1. Load an Excel file from the GUI.
2. Write SQL against the in‑memory table (default names: `excel_file` in the GUI, `catalog_data` in the processor helpers).
3. Run query; preview results; export to Excel/CSV/Parquet.

Helpful details:
- Column headers with spaces/punctuation are cleaned to SQL‑safe identifiers. The Columns panel shows the cleaned names; double‑quote the original name if you prefer it literally (e.g., `"Column With Spaces"`).
- Compatibility behavior is described in `docs/COMPATIBILITY.md`.

## Troubleshooting

- Excel extension errors: harmless. The app will log a warning and use pandas to load Excel.
- LIKE/ILIKE type errors: the engine auto‑casts text vs numeric/binary in most cases. See `docs/COMPATIBILITY.md`.
- Timeouts: configurable in Preferences. Cancels are best‑effort.

## Dev Tasks

- Formatting: `make format` (Black) and `make lint` (Ruff/Flake8). No code behavior changes.
- Config: See `utils/config.py` and YAMLs in the repo root.
- Web-only install for local backend work: `pip install -r web_requirements.txt`

## Known Linting Behavior

- Ruff is configured via `pyproject.toml` and is the primary linter; `make lint` runs Ruff first.
- Flake8 now reads `.flake8` here to mirror the same ignores (line length, wildcard/unused imports, etc.).
- If you want a noisier pass ignoring project config, run `make lint-strict` (uses `--isolated`). Expect warnings — it’s for audits only.
