"""
Tests for sample utility functions.
These tests ensure the sample functions are covered for demonstration purposes.
"""

from django.test import SimpleTestCase
from django.utils.sample_utils import (
    sample_string_processor,
    sample_number_validator,
    sample_string_processor_lazy,
)


class SampleUtilsTestCase(SimpleTestCase):
    """Test case for sample utility functions."""

    def test_sample_string_processor_basic(self):
        """Test basic string processing without options."""
        self.assertEqual(sample_string_processor("hello"), "hello")
        self.assertEqual(sample_string_processor("world"), "world")
        self.assertEqual(sample_string_processor(""), "")

    def test_sample_string_processor_uppercase(self):
        """Test string processing with uppercase option."""
        self.assertEqual(sample_string_processor("hello", uppercase=True), "HELLO")
        self.assertEqual(sample_string_processor("world", uppercase=True), "WORLD")
        self.assertEqual(sample_string_processor("", uppercase=True), "")

    def test_sample_string_processor_reverse(self):
        """Test string processing with reverse option."""
        self.assertEqual(sample_string_processor("hello", reverse=True), "olleh")
        self.assertEqual(sample_string_processor("world", reverse=True), "dlrow")
        self.assertEqual(sample_string_processor("", reverse=True), "")

    def test_sample_string_processor_combined(self):
        """Test string processing with both options."""
        self.assertEqual(
            sample_string_processor("hello", uppercase=True, reverse=True), "OLLEH"
        )
        self.assertEqual(
            sample_string_processor("world", uppercase=True, reverse=True), "DLROW"
        )

    def test_sample_string_processor_type_error(self):
        """Test that non-string inputs raise TypeError."""
        with self.assertRaises(TypeError):
            sample_string_processor(123)
        with self.assertRaises(TypeError):
            sample_string_processor(None)
        with self.assertRaises(TypeError):
            sample_string_processor([])

    def test_sample_number_validator_valid(self):
        """Test number validation with valid inputs."""
        self.assertEqual(sample_number_validator(5), (True, "Number 5 is valid"))
        self.assertEqual(sample_number_validator(0), (True, "Number 0 is valid"))
        self.assertEqual(sample_number_validator(-5), (True, "Number -5 is valid"))

    def test_sample_number_validator_with_min(self):
        """Test number validation with minimum value."""
        self.assertEqual(
            sample_number_validator(5, min_value=1), (True, "Number 5 is valid")
        )
        self.assertEqual(
            sample_number_validator(1, min_value=1), (True, "Number 1 is valid")
        )
        self.assertEqual(
            sample_number_validator(0, min_value=1),
            (False, "Number 0 is too low (min: 1)"),
        )

    def test_sample_number_validator_with_max(self):
        """Test number validation with maximum value."""
        self.assertEqual(
            sample_number_validator(5, max_value=10), (True, "Number 5 is valid")
        )
        self.assertEqual(
            sample_number_validator(10, max_value=10), (True, "Number 10 is valid")
        )
        self.assertEqual(
            sample_number_validator(15, max_value=10),
            (False, "Number 15 is too high (max: 10)"),
        )

    def test_sample_number_validator_with_range(self):
        """Test number validation with both min and max values."""
        self.assertEqual(
            sample_number_validator(5, min_value=1, max_value=10),
            (True, "Number 5 is valid"),
        )
        self.assertEqual(
            sample_number_validator(0, min_value=1, max_value=10),
            (False, "Number 0 is too low (min: 1)"),
        )
        self.assertEqual(
            sample_number_validator(15, min_value=1, max_value=10),
            (False, "Number 15 is too high (max: 10)"),
        )

    def test_sample_number_validator_type_error(self):
        """Test that non-numeric inputs return error."""
        self.assertEqual(
            sample_number_validator("not a number"), (False, "Input must be a number")
        )
        self.assertEqual(
            sample_number_validator(None), (False, "Input must be a number")
        )
        self.assertEqual(sample_number_validator([]), (False, "Input must be a number"))

    def test_sample_string_processor_lazy(self):
        """Test the lazy version of the string processor."""
        lazy_result = sample_string_processor_lazy("hello", uppercase=True)
        self.assertEqual(str(lazy_result), "HELLO")

        lazy_result = sample_string_processor_lazy("world", reverse=True)
        self.assertEqual(str(lazy_result), "dlrow")
