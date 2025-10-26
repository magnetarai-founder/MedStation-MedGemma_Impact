# ElohimOS

**A Faith-Driven AI Operating System**

Copyright (c) 2025 MagnetarAI, LLC

---

## Overview

**ElohimOS** is a local, offline-first AI operating system designed to empower missions, ministries, and communities with secure, powerful tools that work anywhere—even without internet connectivity.

Built on the conviction that technology should serve people, not dominate them, ElohimOS provides:
- **Local AI Processing** — All inference runs on your hardware using Apple Neural Engine (ANE) and Metal Performance Shaders
- **Offline-First Architecture** — Full functionality without internet dependency
- **Data Privacy & Security** — Your data never leaves your machine
- **Excel → SQL → Insights** — Analyze data with natural language queries powered by AI
- **Mission-Ready Tools** — Built for field work, crisis response, and resource-constrained environments

---

## Quickstart

### Web UI

Run the following command to start ElohimOS:

```bash
./elohim
```

This will:
1. Create a Python virtual environment
2. Install web-only dependencies
3. Start the backend (http://localhost:8000)
4. Launch the frontend (http://localhost:5173)

Access the application at **http://localhost:5173**

### Using ElohimOS

1. **Load Data** — Upload an Excel file through the GUI
2. **Write Queries** — Use SQL or natural language to query your data
3. **Get Insights** — AI-powered analysis and recommendations
4. **Export Results** — Download as Excel, CSV, or Parquet

---

## Features

### 🚀 AI-Powered Analytics
- Natural language to SQL translation
- Automated insights and pattern detection
- Local LLM inference using optimized Metal shaders

### 📊 Data Processing
- Excel, CSV, Parquet file support
- DuckDB query engine with Redshift compatibility
- Pandas integration for data manipulation

### 🔒 Privacy & Security
- 100% local processing
- No cloud dependencies
- No telemetry or tracking

### ⚡ Performance
- Apple Neural Engine (ANE) acceleration
- Metal Performance Shaders optimization
- Efficient on-device inference

### 🌐 Collaboration Tools
- Real-time collaborative documents
- Spreadsheet editor
- Workflow builder
- Network monitoring and management

---

## Architecture

ElohimOS is built as a monorepo with the following structure:

```
ElohimOS/
├── apps/
│   ├── frontend/          # React + TypeScript web UI
│   └── backend/           # Python FastAPI server
├── packages/
│   ├── metal-inference/   # ANE/Metal acceleration
│   └── shared/            # Shared utilities
├── tools/                 # Build and deployment tools
└── docs/                  # Documentation
```

### Technology Stack

**Frontend:**
- React 18 + TypeScript
- TanStack Query for state management
- Tailwind CSS for styling
- Recharts for data visualization

**Backend:**
- Python 3.11+
- FastAPI for REST API
- DuckDB for SQL queries
- Pandas for data processing
- Metal/ANE for AI inference

---

## Documentation

### Mission & Identity
- [Mission & Values](docs/MISSION.md) — MagnetarAI's core mission and commitment
- [Founder Statement](docs/FOUNDER_STATEMENT.md) — The vision and calling behind MagnetarAI
- [About the Founder](docs/ABOUT_FOUNDER.md) — Josh's story and background
- [Brand Identity](docs/BRAND_IDENTITY.md) — Complete brand identity guide
- [Naming Significance](docs/NAMING_SIGNIFICANCE.md) — The deep meaning behind MagnetarAI and ElohimOS
- [Pitch Deck](docs/PITCH_DECK.md) — Investor pitch deck summary
- [Funding Opportunities](docs/FUNDING_OPPORTUNITIES.md) — Faith-based funding sources
- [Brand Assets & Trademarks](docs/BRAND_ASSETS_TRADEMARK.md) — Trademark filing guide

### Development & Contributing
- [Code of Conduct](CODE_OF_CONDUCT.md) — Community standards and values
- [Contributing Guide](docs/CONTRIBUTING.md) — How to contribute to ElohimOS
- [Technical Documentation](docs/README.md) — System architecture and implementation details

### Technical Resources
- [Chat API](docs/markdowns/CHAT_API.md) — AI chat integration documentation
- [Metal Implementation](docs/markdowns/METAL4_COMPLETE_STATUS.md) — ANE/Metal acceleration details

---

## Development

### Prerequisites

- macOS 14.0+ (for Metal/ANE support)
- Python 3.11+
- Node.js 18+
- Git LFS (for large model files)

### Installation

```bash
# Clone the repository
git clone https://github.com/magnetar-ai/ElohimOS.git
cd ElohimOS

# Run the application (handles setup automatically)
./elohim
```

### Development Tasks

```bash
# Format code
make format

# Run linter
make lint

# Strict linting (audit mode)
make lint-strict
```

---

## Troubleshooting

### Excel Extension Errors
These warnings are harmless. ElohimOS will automatically fall back to pandas-based Excel loading.

### LIKE/ILIKE Type Errors
The query engine auto-casts between text and numeric/binary types. See [COMPATIBILITY.md](docs/COMPATIBILITY.md) for details.

### Query Timeouts
Timeouts are configurable in application Preferences. Query cancellation is best-effort.

---

## Mission & Values

ElohimOS is part of **MagnetarAI**, a faith-driven technology company dedicated to building tools that serve people and glorify God.

### Our Conviction

> "Where others see code, I see creation—order pulled from chaos, light pulled from darkness."
> — Josh, Founder

We believe:
- **Technology should serve, not dominate**
- **Privacy is a fundamental right**
- **Powerful tools should be accessible to all**
- **Innovation can heal, not divide**

### MagnetarMission

Through **MagnetarMission**, we serve:
- Faith communities and missionaries in the field
- Crisis response teams in remote areas
- Under-resourced communities without reliable internet
- Anyone who needs powerful AI tools that respect privacy

---

## License

Copyright (c) 2025 MagnetarAI, LLC

Licensed under the [MIT License](LICENSE) — see LICENSE file for details.

---

## Contact

**MagnetarAI, LLC**
- Website: [Coming Soon]
- Email: [Contact Information]
- GitHub: [@magnetar-ai](https://github.com/magnetar-ai)

---

**Built with conviction. Deployed with compassion. Powered by faith.**

*Pressed but not crushed. Built under pressure, made for purpose.*
