import io
import json
import sys

import httpx
import pytest

from cache_service.cli import main as cli_main

REQUEST = {"list_1": ["first string", "second string"], "list_2": ["other string", "another string"]}
EXPECTED_OUTPUT = "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING"


def _run(argv, transport):
    return cli_main.run(argv, transport=transport)


def test_json_argument_prints_one_result_to_stdout(cli_transport, capsys):
    assert _run(["--json", json.dumps(REQUEST)], cli_transport) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["output"] == EXPECTED_OUTPUT


def test_short_options_work(cli_transport, capsys):
    assert _run(["-j", json.dumps(REQUEST), "-r", "2", "-o", "-"], cli_transport) == 0
    assert len(capsys.readouterr().out.splitlines()) == 2


def test_input_file_and_output_file(tmp_path, cli_transport, capsys):
    source, target = tmp_path / "in.json", tmp_path / "out.jsonl"
    source.write_text(json.dumps(REQUEST))

    assert _run(["--input", str(source), "--output", str(target)], cli_transport) == 0

    assert json.loads(target.read_text())["output"] == EXPECTED_OUTPUT
    assert capsys.readouterr().out == ""


def test_input_from_stdin(monkeypatch, cli_transport, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(REQUEST)))

    assert _run(["--input", "-"], cli_transport) == 0

    assert json.loads(capsys.readouterr().out)["output"] == EXPECTED_OUTPUT


def test_repeat_emits_one_result_per_iteration_with_same_id(cli_transport, capsys):
    assert _run(["--json", json.dumps(REQUEST), "--repeat", "3"], cli_transport) == 0

    results = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(results) == 3
    assert len({r["id"] for r in results}) == 1


def test_host_is_used_as_base_url(capsys):
    seen: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        if request.method == "POST":
            return httpx.Response(201, json={"id": "abc", "message": "ok"})
        return httpx.Response(200, json={"output": "X"})

    transport = httpx.MockTransport(handler)
    assert _run(["--host", "http://service.example:9000", "--json", json.dumps(REQUEST)], transport) == 0

    assert [(u.host, u.port, u.path) for u in seen] == [
        ("service.example", 9000, "/payload"),
        ("service.example", 9000, "/payload/abc"),
    ]


def test_help_exits_zero_and_lists_options(capsys):
    with pytest.raises(SystemExit) as exc:
        cli_main.run(["--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    for option in ("--host", "--repeat", "--input", "--json", "--output", "-h", "-H"):
        assert option in out


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "{not json"],
        ["--json", json.dumps({"list_1": ["a"], "list_2": ["a", "b"]})],
        ["--json", json.dumps({"list_1": ["a"]})],
        ["--json", json.dumps(REQUEST), "--repeat", "0"],
        ["--json", json.dumps(REQUEST), "--repeat", "many"],
        ["--json", json.dumps(REQUEST), "--bogus"],
        [],
    ],
)
def test_invalid_arguments_or_input_exit_2_without_calling_server(argv, capsys):
    def fail(request):
        raise AssertionError("server must not be called")

    assert _run(argv, httpx.MockTransport(fail)) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error:")


def test_input_and_json_together_are_rejected(tmp_path, capsys):
    source = tmp_path / "in.json"
    source.write_text(json.dumps(REQUEST))

    code = cli_main.run(["--input", str(source), "--json", json.dumps(REQUEST)])

    assert code == 2
    assert "mutually exclusive" in capsys.readouterr().err


def test_missing_input_file_exits_2(tmp_path, capsys):
    assert cli_main.run(["--input", str(tmp_path / "nope.json")]) == 2
    assert "cannot read input file" in capsys.readouterr().err


def test_output_is_not_allowed_to_overwrite_input(tmp_path, capsys):
    source = tmp_path / "in.json"
    source.write_text(json.dumps(REQUEST))

    assert cli_main.run(["--input", str(source), "--output", str(source)]) == 2
    assert json.loads(source.read_text()) == REQUEST


def test_unreachable_server_exits_1_with_message_on_stderr(capsys):
    def refuse(request):
        raise httpx.ConnectError("connection refused")

    assert _run(["--json", json.dumps(REQUEST)], httpx.MockTransport(refuse)) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cannot reach the server" in captured.err


def test_server_error_status_exits_1(capsys):
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text="boom"))

    assert _run(["--json", json.dumps(REQUEST)], transport) == 1
    assert "500" in capsys.readouterr().err


def test_host_environment_variable_does_not_leak_into_settings(monkeypatch):
    monkeypatch.setenv("host", "http://evil.example")
    monkeypatch.setenv("HOST", "http://evil.example")

    from cache_service.cli.settings import CLISettings

    settings = CLISettings(_cli_parse_args=["--json", "{}"])
    assert settings.host == "http://localhost:8000"
