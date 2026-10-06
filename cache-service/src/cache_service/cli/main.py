from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cache_service import models  # noqa: F401 ensures models are registered on Base.metadata
from cache_service.cli.settings import cli_settings
from cache_service.db.base import Base
from cache_service.models.payload import Payload
from cache_service.schemas.payload import PayloadRequest
from cache_service.services.payload_service import PayloadService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cache-service",
        description="Generate (or reuse) a cached payload from two equal-length lists of strings.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to a JSON file with 'list_1'/'list_2' keys (defaults to stdin)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write the result (defaults to stdout)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full JSON object (id, request_hash, output) instead of a plain output list",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Submit the same request N times (demonstrates payload deduplication)",
    )
    return parser


def read_input(input_path: Path | None) -> dict:
    raw = input_path.read_text(encoding="utf-8") if input_path else sys.stdin.read()
    return json.loads(raw)


def format_output(payload: Payload, as_json: bool) -> str:
    if as_json:
        return json.dumps(
            {"id": payload.id, "request_hash": payload.request_hash, "output": payload.output},
            indent=2,
        )
    return "\n".join(payload.output)


def write_output(output_path: Path | None, text: str) -> None:
    if output_path:
        output_path.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.repeat < 1:
        parser.error("--repeat must be >= 1")

    try:
        raw_data = read_input(args.input)
        request = PayloadRequest.model_validate(raw_data)
    except (json.JSONDecodeError, ValidationError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 1

    connect_args = {"check_same_thread": False} if cli_settings.database_url.startswith("sqlite") else {}
    engine = create_engine(cli_settings.database_url, connect_args=connect_args, future=True)
    Base.metadata.create_all(bind=engine)
    # expire_on_commit=False so payload attributes stay readable after the
    # session (and its "with" block) closes below.
    session_factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    payload: Payload | None = None
    for _ in range(args.repeat):
        with session_factory() as db:
            payload = PayloadService(db).get_or_create_payload(request.list_1, request.list_2)

    assert payload is not None
    write_output(args.output, format_output(payload, args.json))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
