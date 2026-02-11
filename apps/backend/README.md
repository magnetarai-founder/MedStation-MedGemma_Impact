# MedStation Backend

FastAPI backend for MedStation medical AI triage assistant.

## Quick Start

```bash
cd apps/backend
source ../../venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `POST /api/v1/chat/ollama` | Chat via Ollama (MedGemma) |
| `GET /api/v1/chat/ollama/models` | List available models |
| `POST /api/v1/image-analysis/analyze` | Image analysis |

## Environment Variables

```bash
MEDSTATION_ENV=development    # or production
PYTHONUNBUFFERED=1
```

## Architecture

```
api/
├── main.py              # FastAPI app entry point
├── router_registry.py   # Route registration
├── routes/
│   ├── chat/            # Chat + Ollama proxy
│   ├── system/          # Health + metrics
│   └── schemas/         # Pydantic models
├── services/
│   ├── chat_ollama.py   # Ollama streaming client
│   ├── ollama_client.py # Ollama HTTP client
│   └── visual/          # Image analysis
└── config/              # App configuration
```

## License

CC BY 4.0
