"""Tests for ConvertOptions."""

from __future__ import annotations

from excalidraw_svg_to_lib.options import ConvertOptions


class TestConvertOptions:
    def test_defaults(self) -> None:
        opts = ConvertOptions()

        assert opts.normalize is True
        assert opts.add_label is True
        assert opts.scale_to_target is True
        assert opts.target_icon_size == 64.0
        assert opts.uniform_stroke_width == 0.5
        assert opts.format_version == 2

    def test_v1_format(self) -> None:
        opts = ConvertOptions(format_version=1)

        assert opts.format_version == 1

    def test_v2_format_explicit(self) -> None:
        opts = ConvertOptions(format_version=2)

        assert opts.format_version == 2

    def test_all_options(self) -> None:
        opts = ConvertOptions(
            normalize=False,
            add_label=False,
            scale_to_target=False,
            target_icon_size=128,
            uniform_stroke_width=1,
            format_version=1,
        )

        assert opts.normalize is False
        assert opts.add_label is False
        assert opts.scale_to_target is False
        assert opts.target_icon_size == 128
        assert opts.uniform_stroke_width == 1
        assert opts.format_version == 1
