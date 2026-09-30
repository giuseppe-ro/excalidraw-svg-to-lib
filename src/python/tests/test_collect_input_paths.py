from pathlib import Path

from excalidraw_svg_to_lib.io import collect_input_paths


def test_collects_recursively_and_aggregates_warnings(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.svg").write_text("<svg/>")
    (tmp_path / "sub" / "b.svg").write_text("<svg/>")
    (tmp_path / ".DS_Store").write_text("x")
    for name in ("a.png", "b.jpg", "c.txt"):
        (tmp_path / name).write_text("x")

    warnings: list[str] = []
    paths = collect_input_paths([tmp_path], warnings=warnings)

    assert [p.name for p in paths] == ["a.svg", "b.svg"]
    assert len(warnings) == 1
    assert "3 unsupported file(s)" in warnings[0]


def test_single_unsupported_file_warns_alone(tmp_path: Path) -> None:
    bad = tmp_path / "logo.png"
    bad.write_text("x")

    warnings: list[str] = []
    assert collect_input_paths([bad], warnings=warnings) == []
    assert warnings == ["WARN: skipping unsupported file 'logo.png'"]


def test_ignored_files_silent(tmp_path: Path) -> None:
    (tmp_path / ".DS_Store").write_text("x")
    (tmp_path / "good.svg").write_text("<svg/>")

    warnings: list[str] = []
    assert collect_input_paths([tmp_path / ".DS_Store"], warnings=warnings) == []
    assert collect_input_paths([tmp_path], warnings=warnings)
    assert warnings == []
