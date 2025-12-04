"""
Tests for sample utility functions.
These tests ensure the sample functions are fully covered for demonstration.
"""

from django.test import SimpleTestCase
from django.utils.sample_utils import (
    sample_number_validator,
    sample_string_processor,
    sample_string_processor_lazy,
)


class SampleUtilsTestCase(SimpleTestCase):
    def test_sample_string_processor_basic(self):
        self.assertEqual(sample_string_processor("hello"), "hello")
        self.assertEqual(sample_string_processor(""), "")

    def test_sample_string_processor_uppercase(self):
        self.assertEqual(sample_string_processor("hello", uppercase=True), "HELLO")

    def test_sample_string_processor_reverse(self):
        self.assertEqual(sample_string_processor("hello", reverse=True), "olleh")

    def test_sample_string_processor_combined(self):
        self.assertEqual(
            sample_string_processor("hello", uppercase=True, reverse=True), "OLLEH"
        )

    def test_sample_string_processor_type_error(self):
        for bad in (123, None, [], {}):
            with self.assertRaises(TypeError):
                sample_string_processor(bad)  # type: ignore[arg-type]

    def test_sample_number_validator_valid(self):
        self.assertEqual(sample_number_validator(5), (True, "Number 5 is valid"))

    def test_sample_number_validator_min(self):
        self.assertEqual(
            sample_number_validator(0, min_value=1),
            (False, "Number 0 is too low (min: 1)"),
        )
        self.assertEqual(
            sample_number_validator(1, min_value=1), (True, "Number 1 is valid")
        )

    def test_sample_number_validator_max(self):
        self.assertEqual(
            sample_number_validator(15, max_value=10),
            (False, "Number 15 is too high (max: 10)"),
        )
        self.assertEqual(
            sample_number_validator(10, max_value=10), (True, "Number 10 is valid")
        )

    def test_sample_number_validator_type_error(self):
        for bad in ("x", None, [], object()):
            self.assertEqual(
                sample_number_validator(bad), (False, "Input must be a number")
            )

    def test_sample_string_processor_lazy(self):
        lazy_result = sample_string_processor_lazy("hello", uppercase=True)
        self.assertEqual(str(lazy_result), "HELLO")
        lazy_result = sample_string_processor_lazy("world", reverse=True)
        self.assertEqual(str(lazy_result), "dlrow")
