from __future__ import annotations

from pathlib import Path

import pytest

from excalidraw_svg_to_lib.library import append_to_existing, make_library_file


class TestMakeLibraryFile:
    def test_creates_basic_library(self) -> None:
        result = make_library_file([[]])
        assert result["type"] == "excalidrawlib"
        assert result["version"] == 1
        assert result["library"] == [[]]

    def test_includes_files_when_provided(self) -> None:
        files = {"file-1": {"mimeType": "image/png"}}
        result = make_library_file([[]], files)
        assert result["files"] == files

    def test_omits_files_key_when_none(self) -> None:
        result = make_library_file([[]])
        assert "files" not in result

    def test_includes_multiple_library_items(self) -> None:
        items = [
            [{"type": "rectangle"}],
            [{"type": "ellipse"}],
        ]
        result = make_library_file(items)
        assert len(result["library"]) == 2


class TestAppendToExisting:
    def test_appends_new_items_to_existing_library(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.excalidrawlib"
        existing.write_text(
            '{"type":"excalidrawlib","version":1,"library":[[{"type":"rectangle"}]]}',
        )
        new_file = make_library_file([[{"type": "ellipse"}]])
        result = append_to_existing(new_file, existing)

        assert len(result["library"]) == 2
        assert result["library"][0][0]["type"] == "rectangle"
        assert result["library"][1][0]["type"] == "ellipse"

    def test_merges_files_from_both_libraries(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.excalidrawlib"
        existing.write_text(
            '{"type":"excalidrawlib","version":1,"library":[[]],"files":{"old-id":{"mimeType":"image/png"}}}',
        )
        new_file = make_library_file(
            [[]],
            {"new-id": {"mimeType": "image/jpeg"}},
        )
        result = append_to_existing(new_file, existing)

        assert "old-id" in result["files"]
        assert "new-id" in result["files"]

    def test_handles_existing_library_without_files(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.excalidrawlib"
        existing.write_text(
            '{"type":"excalidrawlib","version":1,"library":[[{"type":"line"}]]}',
        )
        new_file = make_library_file(
            [[]],
            {"img-1": {"mimeType": "image/png"}},
        )
        result = append_to_existing(new_file, existing)
        assert "img-1" in result["files"]

    def test_preserves_existing_metadata(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.excalidrawlib"
        existing.write_text(
            '{"type":"excalidrawlib","version":2,"library":[[]],"customKey":"value"}',
        )
        new_file = make_library_file([[{"type": "rect"}]])
        result = append_to_existing(new_file, existing)

        assert result["version"] == 2
        assert result["customKey"] == "value"

    def test_raises_for_invalid_existing_file_type(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.excalidrawlib"
        bad.write_text('{"type":"excalidraw","version":1}')
        new_file = make_library_file([[]])

        with pytest.raises(ValueError, match="Invalid library file"):
            append_to_existing(new_file, bad)

    def test_raises_for_missing_library_key(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.excalidrawlib"
        bad.write_text('{"type":"excalidrawlib"}')
        new_file = make_library_file([[]])

        with pytest.raises(ValueError, match="Invalid library file"):
            append_to_existing(new_file, bad)

    def test_raises_for_non_list_library(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.excalidrawlib"
        bad.write_text('{"type":"excalidrawlib","library":"not-a-list"}')
        new_file = make_library_file([[]])

        with pytest.raises(ValueError, match="Invalid library file"):
            append_to_existing(new_file, bad)
