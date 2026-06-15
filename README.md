# AI University

AI University is a personalized AI-powered UPSC coaching backend. The first MVP focuses on one complete study loop: route a student request, teach Polity using memory and trusted sources, generate MCQs, store progress, and schedule revision.

## Local Setup

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Copy environment defaults:

```bash
cp .env.example .env
```

Start local infrastructure:

```bash
docker compose up -d
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Health check:

```text
GET /api/v1/health
```

## Development

Run tests:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

See project planning and architecture in `docs/`.
