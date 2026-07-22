from __future__ import annotations

import json
from pathlib import Path

import pytest

from svg_to_excalidrawlib.cli import main
from tests.conftest import FIXTURES_DIR


def test_cli_converts_directory(tmp_path: Path, monkeypatch, capsys) -> None:
    output_path = tmp_path / "icons.excalidrawlib"

    monkeypatch.setattr(
        "sys.argv",
        [
            "svg-to-excalidrawlib",
            str(FIXTURES_DIR),
            "-o",
            str(output_path),
        ],
    )

    main()

    captured = capsys.readouterr()
    assert "Wrote" in captured.err
    assert output_path.exists()

    library = json.loads(output_path.read_text(encoding="utf-8"))
    assert library["type"] == "excalidrawlib"
    assert len(library["library"]) == 2


def test_cli_prints_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["svg-to-excalidrawlib", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert "svg-to-excalidrawlib" in capsys.readouterr().out
