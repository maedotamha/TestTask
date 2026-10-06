# Cache Service

A small FastAPI service that transforms strings from two input lists, caches
each unique transformation, and deduplicates the resulting generated payloads.

## How it works

Two database tables back the service, with intentionally different identities:

| Table           | Identity               | Purpose                                             |
|-----------------|-------------------------|------------------------------------------------------|
| `cache_entries` | unique `input_text`      | One cached transformation per unique input string.    |
| `payloads`      | unique `request_hash`    | One record per unique generated payload (stable `id`).|

Given `list_1` and `list_2` (equal length), the service transforms each string
(reusing cached results whenever possible) and interleaves the results as
`[t(list_1[0]), t(list_2[0]), t(list_1[1]), t(list_2[1]), ...]`.

The `request_hash` is a SHA-256 fingerprint of `{"list_1": [...], "list_2": [...]}`,
which preserves list order and distinguishes `list_1` from `list_2`. Submitting
the same two lists again returns the existing payload `id` instead of creating
a duplicate.

Both `cache_entries.input_text` and `payloads.request_hash` are enforced unique
at the database level. Writes are wrapped in commit/rollback and fall back to
re-reading the existing row on `IntegrityError`, so concurrent duplicate
requests can't create duplicate rows.

## Project layout

```
cache-service/
├── src/cache_service/
│   ├── main.py              FastAPI app + startup (creates tables)
│   ├── api/routes/          HTTP endpoints
│   ├── schemas/              Pydantic request/response models
│   ├── models/                SQLAlchemy ORM models
│   ├── services/              PayloadService + transformer
│   ├── repositories/           DB access for cache_entries / payloads
│   ├── db/                      Declarative base + session management
│   ├── cli/                      Command-line entry point
│   └── config.py                 Environment-based settings (DATABASE_URL, ...)
├── tests/
│   ├── unit/
│   └── integration/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Setup

```bash
cd cache-service
python -m venv .venv
.venv\Scripts\activate        # on Windows
pip install -e ".[dev]"
copy .env.example .env         # or: cp .env.example .env
```

By default `.env` points at a local SQLite file, so no extra setup is required
to run the API or the tests.

## Running the API

```bash
uvicorn cache_service.main:app --reload
```

Create a payload:

```bash
curl -X POST http://localhost:8000/payload \
  -H "Content-Type: application/json" \
  -d '{"list_1": ["hello", "world"], "list_2": ["one", "two"]}'
```

Sending the same request again returns the same `id`. Sending `list_1`/`list_2`
with different lengths returns `422 Unprocessable Entity`.

Fetch a previously generated payload:

```bash
curl http://localhost:8000/payload/<id>
```

## Running the CLI

The CLI validates input the same way the API does and shares the `PayloadService`.

```bash
# Read from a file, write to stdout
python -m cache_service.cli.main --input request.json

# Read from stdin, write to a file
echo '{"list_1": ["hello"], "list_2": ["one"]}' | python -m cache_service.cli.main --output result.txt

# Full JSON output (id, request_hash, output) instead of a plain list
python -m cache_service.cli.main --input request.json --json

# Submit the same request multiple times to demonstrate deduplication
python -m cache_service.cli.main --input request.json --repeat 5 --json
```

If `pip install -e .` was used, the `cache-service-cli` console script is also
available as a shortcut for `python -m cache_service.cli.main`.

## Tests

```bash
pytest
```

Tests use an isolated in-memory SQLite database per test and cover:
- cache hits/misses (the transformer is only called for uncached strings)
- payload deduplication (identical requests return the same id)
- the `422` response for mismatched list lengths
- the CLI's `--input`, `--output`, `--json`, and `--repeat` flags, including
  stdin/stdout behavior

## Docker

```bash
docker compose up --build
```

This starts a PostgreSQL database and the API (on `http://localhost:8000`),
configured entirely through the `DATABASE_URL` environment variable — no code
changes needed to switch between SQLite (local dev) and PostgreSQL (Docker).

## Configuration

All deployment settings are read from the environment (see `.env.example`):

| Variable       | Default                          | Description                     |
|----------------|-----------------------------------|----------------------------------|
| `DATABASE_URL` | `sqlite:///./cache_service.db`    | SQLAlchemy database URL          |
| `ECHO_SQL`     | `false`                           | Log SQL statements when `true`   |
