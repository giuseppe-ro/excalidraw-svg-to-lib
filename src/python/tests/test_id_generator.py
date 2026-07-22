from __future__ import annotations

import random

import pytest

from excalidraw_svg_to_lib.id_generator import IdGenerator


class TestIdGenerator:
    def test_random_id_has_correct_length(self) -> None:
        gen = IdGenerator(rng=random.Random(42))
        assert len(gen.random_id()) == 21

    def test_random_id_contains_valid_characters(self) -> None:
        gen = IdGenerator(rng=random.Random(42))
        import string

        alphabet = set(string.ascii_letters + string.digits + "_-")
        for _ in range(10):
            rid = gen.random_id()
            assert all(c in alphabet for c in rid)

    def test_seeded_generator_is_deterministic(self) -> None:
        gen_a = IdGenerator(rng=random.Random(123))
        gen_b = IdGenerator(rng=random.Random(123))

        assert gen_a.random_id() == gen_b.random_id()
        assert gen_a.random_id() == gen_b.random_id()
        assert gen_a.random_int() == gen_b.random_int()

    def test_unseeded_generators_produce_different_ids(self) -> None:
        gen_a = IdGenerator()
        gen_b = IdGenerator()
        # With independent unseeded generators, IDs should differ
        assert gen_a.random_id() != gen_b.random_id()

    def test_random_int_within_range(self) -> None:
        gen = IdGenerator(rng=random.Random(42))
        for _ in range(100):
            value = gen.random_int(1000)
            assert 0 <= value < 1000

    def test_random_int_default_max_is_2_pow_31(self) -> None:
        gen = IdGenerator(rng=random.Random(42))
        value = gen.random_int()
        assert 0 <= value < 2**31

    def test_random_int_custom_max(self) -> None:
        gen = IdGenerator(rng=random.Random(42))
        value = gen.random_int(50)
        assert 0 <= value < 50

    def test_multiple_ids_are_unique_in_sequence(self) -> None:
        gen = IdGenerator(rng=random.Random(42))
        ids = {gen.random_id() for _ in range(1000)}
        # With 21 chars from 64-char alphabet, collisions are astronomically unlikely
        assert len(ids) == 1000
