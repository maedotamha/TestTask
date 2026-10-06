import json
import sys
from pathlib import Path

import httpx
from pydantic import ValidationError
from pydantic_settings import SettingsError

from cache_service.cli.settings import CLISettings
from cache_service.schemas.payload import PayloadRequest

EXIT_OK = 0
EXIT_FAILURE = 1  # the service was unreachable or rejected the request
EXIT_USAGE = 2  # bad arguments or bad input; nothing was sent

REQUEST_TIMEOUT_SECONDS = 10.0


class CLIError(Exception):
    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def load_request(settings: CLISettings) -> PayloadRequest:
    """Read and validate the request body so invalid input never reaches the server."""
    if settings.json_data is not None:
        raw = settings.json_data
    elif settings.input == "-":
        raw = sys.stdin.read()
    else:
        try:
            raw = Path(settings.input).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CLIError(f"cannot read input file {settings.input!r}: {exc}", EXIT_USAGE) from exc

    try:
        return PayloadRequest.model_validate_json(raw)
    except ValidationError as exc:
        raise CLIError(f"invalid input: {exc}", EXIT_USAGE) from exc


def check_output_does_not_clobber_input(settings: CLISettings) -> None:
    if settings.output == "-" or settings.input in (None, "-"):
        return
    if Path(settings.output).resolve() == Path(settings.input).resolve():
        raise CLIError("--output must not be the same file as --input", EXIT_USAGE)


def submit_and_fetch(client: httpx.Client, request: PayloadRequest) -> dict[str, str]:
    """POST the request, then GET the generated payload; returns {"id", "output"}."""
    try:
        created = client.post("/payload", json=request.model_dump())
        created.raise_for_status()
        payload_id = created.json()["id"]
        fetched = client.get(f"/payload/{payload_id}")
        fetched.raise_for_status()
        return {"id": payload_id, "output": fetched.json()["output"]}
    except httpx.HTTPStatusError as exc:
        raise CLIError(f"server returned {exc.response.status_code}: {exc.response.text}", EXIT_FAILURE) from exc
    except httpx.HTTPError as exc:
        raise CLIError(f"cannot reach the server: {exc}", EXIT_FAILURE) from exc
    except (ValueError, KeyError) as exc:
        raise CLIError(f"unexpected response from the server: {exc}", EXIT_FAILURE) from exc


def write_results(output: str, results: list[dict[str, str]]) -> None:
    text = "".join(json.dumps(result) + "\n" for result in results)
    if output == "-":
        sys.stdout.write(text)
        return
    try:
        Path(output).write_text(text, encoding="utf-8")
    except OSError as exc:
        raise CLIError(f"cannot write output file {output!r}: {exc}", EXIT_FAILURE) from exc


def run(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None) -> int:
    """Run the CLI; ``transport`` lets tests route requests without a network."""
    try:
        settings = CLISettings(_cli_parse_args=sys.argv[1:] if argv is None else argv)
        request = load_request(settings)
        check_output_does_not_clobber_input(settings)

        # All output goes to stderr on failure so stdout stays machine-readable JSON.
        with httpx.Client(base_url=settings.host, timeout=REQUEST_TIMEOUT_SECONDS, transport=transport) as client:
            results = [submit_and_fetch(client, request) for _ in range(settings.repeat)]
        write_results(settings.output, results)
    except CLIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except (SettingsError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    return EXIT_OK


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
