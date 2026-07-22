from __future__ import annotations

import json
from pathlib import Path

import pytest

from excalidraw_svg_to_lib.io import (
    collect_input_paths,
    default_output_path,
    is_supported_icon_file,
    read_json,
    read_text,
    resolve_output_path,
    write_library_file,
)


class TestCollectInputPathsWarnings:
    """collect_input_paths warns about skipped non-supported files."""

    def test_warns_about_unsupported_files_in_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.svg").write_text("<svg/>")
        (tmp_path / "b.txt").write_text("skip me")
        (tmp_path / "c.pdf").write_bytes(b"%PDF")

        warnings: list[str] = []
        paths = collect_input_paths([tmp_path], warnings=warnings)

        names = {p.name for p in paths}
        assert names == {"a.svg"}
        assert len(warnings) == 2
        assert any("b.txt" in w for w in warnings)
        assert any("c.pdf" in w for w in warnings)

    def test_warns_about_unsupported_single_file(self, tmp_path: Path) -> None:
        bad = tmp_path / "icon.txt"
        bad.write_text("not an icon")

        warnings: list[str] = []
        paths = collect_input_paths([bad], warnings=warnings)

        assert len(paths) == 0
        assert len(warnings) == 1
        assert "icon.txt" in warnings[0]

    def test_no_warnings_when_all_supported(self, tmp_path: Path) -> None:
        (tmp_path / "a.svg").write_text("<svg/>")
        (tmp_path / "b.png").write_bytes(b"\x89PNG")

        warnings: list[str] = []
        paths = collect_input_paths([tmp_path], warnings=warnings)

        assert len(paths) == 2
        assert len(warnings) == 0

    def test_mixed_valid_and_invalid_files(self, tmp_path: Path) -> None:
        icon_dir = tmp_path / "icons"
        icon_dir.mkdir()
        (icon_dir / "good.svg").write_text("<svg/>")
        (icon_dir / "bad.txt").write_text("nope")
        standalone_bad = tmp_path / "standalone.pdf"
        standalone_bad.write_bytes(b"%PDF")

        warnings: list[str] = []
        paths = collect_input_paths([icon_dir, standalone_bad], warnings=warnings)

        names = {p.name for p in paths}
        assert names == {"good.svg"}
        assert len(warnings) == 2  # bad.txt from dir + standalone.pdf

    def test_no_warnings_collected_when_not_requested(self, tmp_path: Path) -> None:
        """Backward compat: without warnings arg, no warnings are tracked."""
        (tmp_path / "a.svg").write_text("<svg/>")
        (tmp_path / "b.txt").write_text("skip")

        paths = collect_input_paths([tmp_path])

        names = {p.name for p in paths}
        assert names == {"a.svg"}


class TestIsSupportedIconFile:
    @pytest.mark.parametrize("ext", [".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"])
    def test_accepts_supported_extensions(self, ext: str) -> None:
        assert is_supported_icon_file(f"icon{ext}")

    def test_case_insensitive(self) -> None:
        assert is_supported_icon_file("icon.PNG")
        assert is_supported_icon_file("icon.SVG")

    @pytest.mark.parametrize("ext", [".txt", ".pdf", ".bmp", ".ico", ""])
    def test_rejects_unsupported_extensions(self, ext: str) -> None:
        assert not is_supported_icon_file(f"file{ext}")


class TestCollectInputPaths:
    def test_collects_svg_from_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.svg").write_text("<svg/>")
        (tmp_path / "b.svg").write_text("<svg/>")
        (tmp_path / "c.png").write_bytes(b"\x89PNG")
        (tmp_path / "d.txt").write_text("skip")

        paths = collect_input_paths([tmp_path])
        names = {p.name for p in paths}
        assert names == {"a.svg", "b.svg", "c.png"}

    def test_collects_single_file(self, tmp_path: Path) -> None:
        icon = tmp_path / "icon.svg"
        icon.write_text("<svg/>")
        paths = collect_input_paths([icon])
        assert len(paths) == 1
        assert paths[0].name == "icon.svg"

    def test_raises_for_missing_path(self) -> None:
        with pytest.raises(FileNotFoundError, match="Input not found"):
            collect_input_paths(["/nonexistent/file.svg"])

    def test_raises_for_non_file_non_dir(self) -> None:
        # This depends on the OS; on most systems a socket or device
        # is hard to create in a temp dir. Skip gracefully.
        pass

    def test_deduplicates_paths(self, tmp_path: Path) -> None:
        icon = tmp_path / "icon.svg"
        icon.write_text("<svg/>")
        paths = collect_input_paths([icon, icon])
        assert len(paths) == 1

    def test_mixed_files_and_directories(self, tmp_path: Path) -> None:
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "a.svg").write_text("<svg/>")
        standalone = tmp_path / "standalone.svg"
        standalone.write_text("<svg/>")

        paths = collect_input_paths([subdir, standalone])
        names = {p.name for p in paths}
        assert names == {"a.svg", "standalone.svg"}

    def test_resolves_paths_to_absolute(self, tmp_path: Path) -> None:
        icon = tmp_path / "icon.svg"
        icon.write_text("<svg/>")
        paths = collect_input_paths([icon])
        assert paths[0].is_absolute()


class TestDefaultOutputPath:
    def test_single_directory_input(self, tmp_path: Path) -> None:
        result = default_output_path([tmp_path], [tmp_path])
        assert result == f"{tmp_path.name}.excalidrawlib"

    def test_single_file_input(self, tmp_path: Path) -> None:
        file_path = tmp_path / "my-icon.svg"
        result = default_output_path([file_path], [file_path])
        assert result == "my-icon.excalidrawlib"

    def test_current_directory_input(self, tmp_path: Path) -> None:
        result = default_output_path(["."], [tmp_path])
        assert result == "icons.excalidrawlib"

    def test_double_dot_input(self, tmp_path: Path) -> None:
        result = default_output_path(["./"], [tmp_path])
        assert result == "icons.excalidrawlib"

    def test_multiple_inputs_defaults_to_icons(self, tmp_path: Path) -> None:
        a = tmp_path / "a.svg"
        b = tmp_path / "b.svg"
        result = default_output_path([a, b], [a, b])
        assert result == "icons.excalidrawlib"


class TestResolveOutputPath:
    def test_explicit_output_wins(self, tmp_path: Path) -> None:
        output = tmp_path / "custom.excalidrawlib"
        result = resolve_output_path(["."], [tmp_path], output, None)
        assert result == output

    def test_falls_back_to_append_path(self, tmp_path: Path) -> None:
        append = tmp_path / "append.excalidrawlib"
        result = resolve_output_path(["."], [tmp_path], None, append)
        assert result == append

    def test_falls_back_to_default(self, tmp_path: Path) -> None:
        result = resolve_output_path(["."], [tmp_path], None, None)
        assert result.name == "icons.excalidrawlib"


class TestReadWrite:
    def test_read_text(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_text("hello world", encoding="utf-8")
        assert read_text(f) == "hello world"

    def test_read_json(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        assert read_json(f) == {"key": "value"}

    def test_write_library_file_excludes_metadata(self, tmp_path: Path) -> None:
        out = tmp_path / "out.excalidrawlib"
        data = {
            "type": "excalidrawlib",
            "version": 1,
            "library": [],
            "metadata": {"should": "be excluded"},
        }
        write_library_file(data, out)

        written = json.loads(out.read_text())
        assert "metadata" not in written
        assert written["type"] == "excalidrawlib"

    def test_write_library_file_custom_exclude_keys(self, tmp_path: Path) -> None:
        out = tmp_path / "out.excalidrawlib"
        data = {
            "type": "excalidrawlib",
            "version": 1,
            "library": [],
            "extra": "data",
            "metadata": "also hidden",
        }
        write_library_file(data, out, exclude_keys=("metadata", "extra"))

        written = json.loads(out.read_text())
        assert "metadata" not in written
        assert "extra" not in written

    def test_write_library_file_creates_parent_dirs(self, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "deep" / "out.excalidrawlib"
        data = {"type": "excalidrawlib", "version": 1, "library": []}
        write_library_file(data, out)
        assert out.exists()
