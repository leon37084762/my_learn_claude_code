"""Utility functions for demo_pkg."""

from typing import Any, List


def add(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Return the difference of two numbers."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Return the product of two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """Return the quotient of two numbers.

    Raises:
        ValueError: If b is zero.
    """
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


def flatten(nested: List[Any]) -> List[Any]:
    """Recursively flatten a nested list.

    Args:
        nested: A list that may contain nested lists.

    Returns:
        A flat list with all elements.
    """
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def unique(items: List[Any]) -> List[Any]:
    """Return a list of unique items, preserving order.

    Args:
        items: A list that may contain duplicates.

    Returns:
        A list with duplicates removed, order preserved.
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
