# ElohimOS Documentation

**Copyright (c) 2025 MagnetarAI, LLC**

Welcome to the **ElohimOS** documentation. This directory contains comprehensive technical documentation, implementation guides, and mission information for the ElohimOS platform.

---

## 📚 Documentation Index

### Getting Started
- **[Main README](../README.md)** — Project overview and quickstart guide
- **[Contributing Guide](CONTRIBUTING.md)** — How to contribute to ElohimOS
- **[Quickstart](#quickstart)** — Get up and running quickly

### Mission & Vision
- **[Founder Statement](FOUNDER_STATEMENT.md)** — Josh's vision and calling
- **[About the Founder](ABOUT_FOUNDER.md)** — Background and mission
- **[Mission & Values](MISSION.md)** — MagnetarAI's core mission and values
- **[Brand Identity](BRAND_IDENTITY.md)** — Complete brand identity guide
- **[Naming Significance](NAMING_SIGNIFICANCE.md)** — The deep meaning behind MagnetarAI and ElohimOS

### Funding & Investment
- **[Pitch Deck](PITCH_DECK.md)** — Complete investor pitch deck summary
- **[Funding Opportunities](FUNDING_OPPORTUNITIES.md)** — Faith-based investors and accelerators
- **[Brand Assets & Trademarks](BRAND_ASSETS_TRADEMARK.md)** — Trademark filing guide and brand protection

### Technical Documentation

#### Core Features
- **[Chat API](markdowns/CHAT_API.md)** — AI chat integration and endpoints
- **[Chat UI Implementation](markdowns/CHAT_UI_COMPLETE.md)** — Frontend chat interface
- **[Insights Lab](markdowns/INSIGHTS_LAB_COMPLETE.md)** — AI-powered data insights

#### Performance & Acceleration
- **[Metal 4 Implementation](markdowns/METAL4_COMPLETE_STATUS.md)** — ANE/Metal acceleration status
- **[Metal 4 Optimization Plan](markdowns/METAL4_OPTIMIZATION_PLAN.md)** — Performance optimization strategies
- **[Metal 4 Validation](markdowns/METAL4_VALIDATION_REPORT.md)** — Testing and validation results
- **[ANE/Metal Integration](markdowns/ANE_METAL_INTEGRATION.md)** — Apple Neural Engine integration

#### Architecture & Implementation
- **[Backend Complete](markdowns/BACKEND_COMPLETE.md)** — Backend architecture overview
- **[Phase 1 Complete](markdowns/PHASE1_COMPLETE.md)** — Initial implementation milestone
- **[Progress Report](markdowns/ELOHIMOS_PROGRESS_REPORT.md)** — Current development status
- **[Vision Assessment](markdowns/ELOHIMOS_VISION_ASSESSMENT.md)** — Long-term roadmap

#### Operations
- **[Archive & Restore](markdowns/ARCHIVE_RESTORE.md)** — Data backup and recovery
- **[Whisper Installation](markdowns/WHISPER_INSTALLATION.md)** — Audio transcription setup

---

## 🚀 Quickstart

### Installation

```bash
# Clone the repository
git clone https://github.com/magnetar-ai/ElohimOS.git
cd ElohimOS

# Run the application
./elohim
```

This will:
1. Create a Python virtual environment
2. Install web dependencies
3. Start backend (http://localhost:8000)
4. Launch frontend (http://localhost:5173)

### Basic Usage

1. **Load Data** — Upload an Excel file from the GUI
2. **Write Queries** — Use SQL or natural language
3. **Get Insights** — AI-powered analysis and recommendations
4. **Export Results** — Download as Excel, CSV, or Parquet

---

## 💻 Development

### Prerequisites

- macOS 14.0+ (for Metal/ANE support)
- Python 3.11+
- Node.js 18+
- Git LFS

### Setup

```bash
# Backend setup
python3 -m venv venv
source venv/bin/activate
pip install -r web_requirements.txt

# Frontend setup
cd apps/frontend
npm install
npm run dev
```

### Development Tasks

```bash
# Code formatting
make format

# Linting
make lint

# Strict linting (audit mode)
make lint-strict
```

---

## 🛠️ Technical Details

### Architecture

ElohimOS uses:
- **DuckDB** for SQL query engine
- **Pandas** for data processing
- **FastAPI** for REST API backend
- **React + TypeScript** for frontend
- **Metal/ANE** for AI acceleration

### SQL Compatibility

ElohimOS includes Redshift-compatible features:
- LIKE/ILIKE auto-casting
- Recursive CTE support
- Null type handling
- Identifier cleaning

Column headers with spaces/punctuation are cleaned to SQL-safe identifiers. The Columns panel shows cleaned names; use double quotes for original names (e.g., `"Column With Spaces"`).

### Data Processing

**Supported Formats:**
- Excel (.xlsx, .xls)
- CSV (.csv)
- Parquet (.parquet)

**Default Table Names:**
- GUI: `excel_file`
- Processor: `catalog_data`

---

## 🔧 Troubleshooting

### Excel Extension Errors
**Issue:** DuckDB extension loading warnings

**Solution:** These are harmless. ElohimOS automatically falls back to pandas-based Excel loading.

### LIKE/ILIKE Type Errors
**Issue:** Type mismatches in LIKE queries

**Solution:** The engine auto-casts between text and numeric/binary types. See COMPATIBILITY.md for details.

### Query Timeouts
**Issue:** Long-running queries timing out

**Solution:** Timeouts are configurable in Preferences. Query cancellation is best-effort.

### Parquet Export Issues
**Issue:** Parquet export fails

**Solution:** Ensure `pyarrow` is installed:
```bash
pip install pyarrow
```

---

## 📖 Additional Resources

### Configuration
- Config files: `utils/config.py`
- YAML configs: Repository root
- Web requirements: `web_requirements.txt`

### Linting Behavior
- **Primary linter:** Ruff (configured in `pyproject.toml`)
- **Secondary linter:** Flake8 (reads `.flake8`)
- **Strict mode:** Use `make lint-strict` for audits (expect warnings)

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of conduct
- Development setup
- Coding standards
- Pull request process

---

## 📄 License

Copyright (c) 2025 MagnetarAI, LLC

Licensed under the MIT License — see [LICENSE](../LICENSE) for details.

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/magnetar-ai/ElohimOS/issues)
- **Discussions:** [GitHub Discussions](https://github.com/magnetar-ai/ElohimOS/discussions)
- **Email:** [Contact Information]

---

**Built with conviction. Deployed with compassion. Powered by faith.**

*Local, offline-first AI platform — Excel → SQL → Insights with AI assistance*
