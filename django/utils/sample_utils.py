"""
Sample utility functions for testing coverage reporting.
This module is intentionally simple and is used to demonstrate
PR diff coverage when paired with its tests.
"""

from django.utils.functional import lazy


def sample_string_processor(
    text: str, uppercase: bool = False, reverse: bool = False
) -> str:
    """
    Process strings with optional transformations.

    - If ``uppercase`` is True, convert the string to uppercase.
    - If ``reverse`` is True, reverse the string.

    Raises TypeError if ``text`` is not a string.
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")

    result = text

    if uppercase:
        result = result.upper()

    if reverse:
        result = result[::-1]

    return result


def sample_number_validator(number, min_value=None, max_value=None):
    """
    Validate that a number is within optional min/max bounds.

    Returns a tuple: (is_valid: bool, message: str)
    """
    if not isinstance(number, (int, float)):
        return False, "Input must be a number"

    if min_value is not None and number < min_value:
        return False, f"Number {number} is too low (min: {min_value})"

    if max_value is not None and number > max_value:
        return False, f"Number {number} is too high (max: {max_value})"

    return True, f"Number {number} is valid"


# Lazy wrapper for demonstration of lazy evaluation
sample_string_processor_lazy = lazy(sample_string_processor, str)
