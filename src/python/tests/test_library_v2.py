"""Tests for v2 library format (searchable icons via ``name`` field).

The v2 ``libraryItems`` format adds per-item metadata (``id``, ``name``,
``status``, ``created``) that makes icons searchable in Excalidraw.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from excalidraw_svg_to_lib.library import (
    append_to_existing,
    make_library_file,
    make_v2_item,
)


class TestMakeV2Item:
    """``make_v2_item`` produces a single libraryItem dict."""

    def test_creates_required_fields(self) -> None:
        item = make_v2_item(elements=[], name="TestIcon")

        assert "id" in item
        assert item["name"] == "TestIcon"
        assert item["status"] == "published"
        assert item["elements"] == []
        assert "created" in item
        assert isinstance(item["created"], int)

    def test_includes_elements(self) -> None:
        elements = [{"type": "rectangle"}, {"type": "text"}]
        item = make_v2_item(elements=elements, name="MyIcon")

        assert item["elements"] is elements
        assert len(item["elements"]) == 2

    def test_id_is_non_empty_string(self) -> None:
        item = make_v2_item(elements=[], name="X")
        assert isinstance(item["id"], str)
        assert len(item["id"]) > 0

    def test_created_is_recent_timestamp(self) -> None:
        now = int(time.time() * 1000)
        item = make_v2_item(elements=[], name="X")
        # Within 10 seconds of now
        assert abs(item["created"] - now) < 10_000


class TestMakeLibraryFileV2:
    """``make_library_file`` with ``format_version=2`` produces v2 output."""

    def test_v2_has_library_items_key(self) -> None:
        result = make_library_file(items=[([], "icon")], format_version=2)

        assert "libraryItems" in result
        assert result["version"] == 2
        assert result["type"] == "excalidrawlib"
        assert len(result["libraryItems"]) == 1

    def test_v2_item_has_name(self) -> None:
        result = make_library_file(items=[([], "MyIcon")], format_version=2)

        item = result["libraryItems"][0]
        assert item["name"] == "MyIcon"

    def test_v2_has_source(self) -> None:
        result = make_library_file(items=[([], "icon")], format_version=2)

        assert result["source"] == "https://excalidraw.com"

    def test_v2_omits_library_key(self) -> None:
        result = make_library_file(items=[([], "icon")], format_version=2)

        assert "library" not in result

    def test_v2_with_multiple_items(self) -> None:
        items = [
            ([{"type": "rectangle"}], "IconA"),
            ([{"type": "ellipse"}], "IconB"),
        ]
        result = make_library_file(items=items, format_version=2)

        assert len(result["libraryItems"]) == 2
        assert result["libraryItems"][0]["name"] == "IconA"
        assert result["libraryItems"][1]["name"] == "IconB"

    def test_v2_includes_files_when_provided(self) -> None:
        files = {"file-1": {"mimeType": "image/png"}}
        result = make_library_file(items=[([], "icon")], files=files, format_version=2)

        assert result["files"] == files

    def test_v2_omits_files_key_when_none(self) -> None:
        result = make_library_file(items=[([], "icon")], format_version=2)

        assert "files" not in result

    def test_v2_all_items_have_unique_ids(self) -> None:
        items = [([], "A"), ([], "B"), ([], "C")]
        result = make_library_file(items=items, format_version=2)

        ids = [item["id"] for item in result["libraryItems"]]
        assert len(ids) == len(set(ids))


class TestMakeLibraryFileV1BackwardsCompat:
    """v1 format still works for backwards compatibility."""

    def test_v1_uses_library_key(self) -> None:
        result = make_library_file([[]], format_version=1)

        assert result["version"] == 1
        assert "library" in result
        assert result["library"] == [[]]

    def test_v1_no_library_items_key(self) -> None:
        result = make_library_file([[]], format_version=1)

        assert "libraryItems" not in result

    def test_v1_list_of_elements_only(self) -> None:
        result = make_library_file([[{"type": "rect"}]], format_version=1)

        assert len(result["library"]) == 1
        assert result["library"][0][0]["type"] == "rect"


class TestAppendV2:
    """``append_to_existing`` handles v2 library files."""

    def test_appends_to_v2_library(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.excalidrawlib"
        existing.write_text(
            '{"type":"excalidrawlib","version":2,"source":"https://excalidraw.com",'
            '"libraryItems":[{"id":"id1","status":"published","name":"Existing",'
            '"elements":[],"created":1000000}]}'
        )
        new_file = make_library_file(items=[([], "NewIcon")], format_version=2)
        result = append_to_existing(new_file, existing)

        assert len(result["libraryItems"]) == 2
        names = [item["name"] for item in result["libraryItems"]]
        assert "Existing" in names
        assert "NewIcon" in names

    def test_appends_to_v1_library(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.excalidrawlib"
        existing.write_text(
            '{"type":"excalidrawlib","version":1,"library":[[{"type":"rectangle"}]]}'
        )
        new_file = make_library_file([[{"type": "ellipse"}]])
        result = append_to_existing(new_file, existing)

        assert len(result["library"]) == 2

    def test_raises_for_invalid_file_type(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.excalidrawlib"
        bad.write_text('{"type":"excalidraw","version":1}')
        new_file = make_library_file([[]])

        with pytest.raises(ValueError, match="Invalid library file"):
            append_to_existing(new_file, bad)

    def test_raises_for_missing_library_keys(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.excalidrawlib"
        bad.write_text('{"type":"excalidrawlib"}')
        new_file = make_library_file([[]])

        with pytest.raises(ValueError, match="Invalid library file.*missing"):
            append_to_existing(new_file, bad)

    def test_merges_files_across_v2_libraries(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.excalidrawlib"
        existing.write_text(
            '{"type":"excalidrawlib","version":2,"libraryItems":[],'
            '"files":{"old-id":{"mimeType":"image/png"}}}'
        )
        new_file = make_library_file(
            items=[([], "icon")],
            files={"new-id": {"mimeType": "image/jpeg"}},
            format_version=2,
        )
        result = append_to_existing(new_file, existing)

        assert "old-id" in result["files"]
        assert "new-id" in result["files"]

    def test_preserves_existing_metadata(self, tmp_path: Path) -> None:
        existing = tmp_path / "existing.excalidrawlib"
        existing.write_text(
            '{"type":"excalidrawlib","version":2,"source":"https://example.com",'
            '"libraryItems":[],"customKey":"value"}'
        )
        new_file = make_library_file(items=[([], "icon")], format_version=2)
        result = append_to_existing(new_file, existing)

        assert result["source"] == "https://example.com"
        assert result["customKey"] == "value"
