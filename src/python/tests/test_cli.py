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
    assert library["version"] == 2
    assert len(library["libraryItems"]) >= 2
    assert all(
        any(element["type"] == "text" for element in item["elements"])
        for item in library["libraryItems"]
    )


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
    assert all(
        "text" not in {element["type"] for element in item["elements"]}
        for item in library["libraryItems"]
    )


def test_cli_prints_help(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["excalidraw-svg-to-lib", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert "excalidraw-svg-to-lib" in capsys.readouterr().out


def test_cli_warns_and_skips_unsupported_files_in_directory(tmp_path: Path, monkeypatch, capsys) -> None:
    """Non-supported files in a directory are skipped with warnings; valid files still convert."""
    output_path = tmp_path / "icons.excalidrawlib"

    # Create valid and invalid files alongside fixtures
    (tmp_path / "valid.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
    )
    (tmp_path / "readme.txt").write_text("not an icon")
    (tmp_path / "data.json").write_text('{"key": "value"}')

    monkeypatch.setattr(
        "sys.argv",
        ["excalidraw-svg-to-lib", str(tmp_path), "-o", str(output_path)],
    )

    main()

    captured = capsys.readouterr()
    # Should warn about the unsupported files
    assert "readme.txt" in captured.err
    assert "data.json" in captured.err
    assert "WARN:" in captured.err

    # Should still convert valid SVGs
    assert output_path.exists()
    library = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(library["libraryItems"]) == 1
    assert library["libraryItems"][0]["name"] == "valid"


def test_cli_warns_and_skips_unsupported_single_file(tmp_path: Path, monkeypatch, capsys) -> None:
    """A single unsupported file is skipped with a warning; exits with error."""
    output_path = tmp_path / "icons.excalidrawlib"
    bad_file = tmp_path / "icon.txt"
    bad_file.write_text("not an icon")

    monkeypatch.setattr(
        "sys.argv",
        ["excalidraw-svg-to-lib", str(bad_file), "-o", str(output_path)],
    )

    with pytest.raises(SystemExit):
        main()

    captured = capsys.readouterr()
    assert "icon.txt" in captured.err
    assert "WARN:" in captured.err

    # No output file since all inputs were skipped
    assert not output_path.exists()


def test_cli_mixed_valid_and_invalid_files(tmp_path: Path, monkeypatch, capsys) -> None:
    """Valid files are converted, invalid files are warned and skipped."""
    output_path = tmp_path / "icons.excalidrawlib"
    good = tmp_path / "good.svg"
    good.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>')
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        "sys.argv",
        ["excalidraw-svg-to-lib", str(good), str(bad), "-o", str(output_path)],
    )

    main()

    captured = capsys.readouterr()
    # Warning about bad file
    assert "bad.pdf" in captured.err
    # Success for good file
    assert "Wrote" in captured.err

    assert output_path.exists()
    library = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(library["libraryItems"]) == 1
    assert library["libraryItems"][0]["name"] == "good"
