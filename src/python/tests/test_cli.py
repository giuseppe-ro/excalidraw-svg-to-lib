from __future__ import annotations

import json
from pathlib import Path

import pytest

from excalidraw_svg_to_lib.cli import main
from tests.conftest import FIXTURES_DIR


def test_cli_converts_directory(tmp_path: Path, monkeypatch, capsys) -> None:
    output_path = tmp_path / "icons.excalidrawlib"

    monkeypatch.setattr(
        "sys.argv",
        [
            "excalidraw-svg-to-lib",
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
    assert all(any(element["type"] == "text" for element in item) for item in library["library"])


def test_cli_no_label_skips_text(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "icons.excalidrawlib"

    monkeypatch.setattr(
        "sys.argv",
        [
            "excalidraw-svg-to-lib",
            str(FIXTURES_DIR),
            "-o",
            str(output_path),
            "--no-label",
        ],
    )

    main()

    library = json.loads(output_path.read_text(encoding="utf-8"))
    assert all("text" not in {element["type"] for element in item} for item in library["library"])


def test_cli_prints_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["excalidraw-svg-to-lib", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert "excalidraw-svg-to-lib" in capsys.readouterr().out
