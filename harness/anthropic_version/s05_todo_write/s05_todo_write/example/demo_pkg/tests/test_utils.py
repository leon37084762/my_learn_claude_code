"""Tests for demo_pkg.utils."""

import pytest
from demo_pkg.utils import add, subtract, multiply, divide, flatten, unique


class TestAdd:
    def test_positive_numbers(self):
        assert add(2, 3) == 5

    def test_negative_numbers(self):
        assert add(-1, -1) == -2

    def test_mixed_numbers(self):
        assert add(-1, 1) == 0

    def test_floats(self):
        assert add(0.1, 0.2) == pytest.approx(0.3)


class TestSubtract:
    def test_positive_numbers(self):
        assert subtract(5, 3) == 2

    def test_negative_result(self):
        assert subtract(3, 5) == -2

    def test_floats(self):
        assert subtract(1.5, 0.5) == pytest.approx(1.0)


class TestMultiply:
    def test_positive_numbers(self):
        assert multiply(3, 4) == 12

    def test_by_zero(self):
        assert multiply(5, 0) == 0

    def test_negative_numbers(self):
        assert multiply(-2, -3) == 6


class TestDivide:
    def test_even_division(self):
        assert divide(10, 2) == 5.0

    def test_float_result(self):
        assert divide(7, 2) == pytest.approx(3.5)

    def test_divide_by_zero(self):
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(1, 0)


class TestFlatten:
    def test_flat_list(self):
        assert flatten([1, 2, 3]) == [1, 2, 3]

    def test_nested_list(self):
        assert flatten([1, [2, [3, 4], 5]]) == [1, 2, 3, 4, 5]

    def test_empty_list(self):
        assert flatten([]) == []

    def test_deeply_nested(self):
        assert flatten([[[1]], [[2]], [[3]]]) == [1, 2, 3]


class TestUnique:
    def test_no_duplicates(self):
        assert unique([1, 2, 3]) == [1, 2, 3]

    def test_with_duplicates(self):
        assert unique([1, 2, 2, 3, 1]) == [1, 2, 3]

    def test_empty_list(self):
        assert unique([]) == []

    def test_strings(self):
        assert unique(["a", "b", "a", "c"]) == ["a", "b", "c"]

    def test_preserves_order(self):
        assert unique([3, 1, 2, 1, 3]) == [3, 1, 2]
