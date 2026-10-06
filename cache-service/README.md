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
`[t(list_1[0]), t(list_2[0]), t(list_1[1]), t(list_2[1]), ...]`, stored as a
list and returned by `GET /payload/{id}` joined with `", "`. The transformer
(`services/transformer.py`) upper-cases its input and stands in for an external service.

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

The CLI is an HTTP client for the API (start the server first). Options are
parsed by Pydantic Settings' CLI support:

| Option                  | Meaning                                                              |
|-------------------------|----------------------------------------------------------------------|
| `-H`, `--host URL`      | API server URL (default `http://localhost:8000`)                     |
| `-r`, `--repeat N`      | Iterations, N >= 1 (default 1)                                       |
| `-i`, `--input FILE\|-` | JSON input file, or `-` for stdin                                    |
| `-j`, `--json JSON`     | JSON input given directly as an argument                             |
| `-o`, `--output FILE\|-`| Output file, or `-` for stdout (default `-`)                         |
| `-h`, `--help`          | Usage                                                                |

The assignment assigns `-h` to both `--host` and `--help`; argparse cannot
register both, so `-h` stays `--help` and the host short option is `-H`.

Exactly one of `--input` / `--json` is required; passing both is an error.
Each iteration POSTs the request and GETs the payload back, and writes one
JSON object (`{"id": ..., "output": ...}`) per line, so repeated runs show the
same `id` being reused. Only results go to stdout; errors go to stderr.
Exit codes: `0` success, `1` server unreachable/rejected, `2` bad arguments or input.
Generic environment variables (e.g. `HOST`) are intentionally ignored.

```bash
python -m cache_service.cli.main -j '{"list_1": ["a"], "list_2": ["b"]}'
python -m cache_service.cli.main -H http://localhost:8000 -i request.json -r 3 -o results.jsonl
echo '{"list_1": ["a"], "list_2": ["b"]}' | python -m cache_service.cli.main -i -
```

After `pip install -e .` the same command is available as `cache-cli`.

## Tests

```bash
pytest
```

Tests use an isolated in-memory SQLite database per test (no PostgreSQL in the
automated suite) and cover:
- model constraints: unique `input_text` / `request_hash`, rollback and recovery after a conflict
- repositories: cache hit/miss, empty-string results, batch lookup
- the service: transformer called only for uncached strings (also across payloads and
  duplicates within one request), payload id reuse, order-sensitive hashing, recovery
  from a simulated concurrent insert
- the API: the sample POST/GET, 404, and 422 for invalid bodies
- the CLI: every option, stdin/stdout, files, invalid input, conflicting arguments,
  unreachable server and server errors (via an in-process transport, no real network)

Lint and format: `ruff check src tests` and `ruff format --check src tests`.

## Docker

```bash
docker compose up --build
# if port 8000 is taken on your machine:
APP_PORT=8765 docker compose up --build
```

This starts PostgreSQL and the API (default `http://localhost:8000`).

- The app reaches the database at hostname `db` (the Compose service name), and
  starts only after the database healthcheck passes (`depends_on: service_healthy`).
- Data lives in the named volume `db_data`; `docker compose down` keeps it,
  `docker compose down -v` deletes it.
- The database port is not published to the host; only the API is.
- The container runs as a non-root user and has a `/health` healthcheck.
- The credentials in `docker-compose.yml` are development placeholders; change
  them for any real deployment.
- Dependencies are installed from `pyproject.toml` version ranges, not a lock file.

Verified manually against this stack on PostgreSQL 16: the CLI sample returns the
expected output, 30 concurrent identical POSTs returned one id, 30 concurrent POSTs
with overlapping strings left no duplicate `input_text` rows, and a payload was
still readable after restarting the app container. The automated test suite itself
runs on SQLite only.

## Configuration

All deployment settings are read from the environment (see `.env.example`):

| Variable       | Default                          | Description                     |
|----------------|-----------------------------------|----------------------------------|
| `DATABASE_URL` | `sqlite:///./cache_service.db`    | SQLAlchemy database URL          |
| `ECHO_SQL`     | `false`                           | Log SQL statements when `true`   |
