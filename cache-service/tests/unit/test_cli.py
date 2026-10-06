import io
import json
import sys

import pytest

from cache_service.cli import main as cli_main


@pytest.fixture(autouse=True)
def _use_temp_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / "cli_test.db"
    monkeypatch.setattr(cli_main.cli_settings, "database_url", f"sqlite:///{db_path}")
    yield


def test_cli_reads_input_file_and_writes_output_file(tmp_path):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.txt"
    input_path.write_text(json.dumps({"list_1": ["hello", "world"], "list_2": ["one", "two"]}))

    exit_code = cli_main.run(["--input", str(input_path), "--output", str(output_path)])

    assert exit_code == 0
    lines = output_path.read_text().strip().splitlines()
    assert len(lines) == 4


def test_cli_reads_from_stdin_and_writes_to_stdout(monkeypatch, capsys):
    data = json.dumps({"list_1": ["hello"], "list_2": ["one"]})
    monkeypatch.setattr(sys, "stdin", io.StringIO(data))

    exit_code = cli_main.run([])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() != ""


def test_cli_json_flag_outputs_structured_result(tmp_path):
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(json.dumps({"list_1": ["hello"], "list_2": ["one"]}))

    cli_main.run(["--input", str(input_path), "--output", str(output_path), "--json"])

    result = json.loads(output_path.read_text())
    assert set(result.keys()) == {"id", "request_hash", "output"}


def test_cli_repeat_returns_same_payload_id(tmp_path):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"list_1": ["hello"], "list_2": ["one"]}))
    output_path_1 = tmp_path / "out1.json"
    output_path_2 = tmp_path / "out2.json"

    cli_main.run(["--input", str(input_path), "--output", str(output_path_1), "--json", "--repeat", "3"])
    cli_main.run(["--input", str(input_path), "--output", str(output_path_2), "--json"])

    first = json.loads(output_path_1.read_text())
    second = json.loads(output_path_2.read_text())
    assert first["id"] == second["id"]


def test_cli_rejects_mismatched_list_lengths(tmp_path):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps({"list_1": ["a"], "list_2": ["a", "b"]}))

    exit_code = cli_main.run(["--input", str(input_path)])

    assert exit_code == 1
