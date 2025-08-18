"""
Sample utility functions for testing coverage reporting.
This file is created to demonstrate the test coverage system.
"""

from django.utils.functional import lazy


def sample_string_processor(text, uppercase=False, reverse=False):
    """
    A sample function that processes strings in various ways.
    
    Args:
        text (str): Input text to process
        uppercase (bool): Whether to convert to uppercase
        reverse (bool): Whether to reverse the string
        
    Returns:
        str: Processed string
        
    Examples:
        >>> sample_string_processor("hello")
        'hello'
        >>> sample_string_processor("hello", uppercase=True)
        'HELLO'
        >>> sample_string_processor("hello", reverse=True)
        'olleh'
        >>> sample_string_processor("hello", uppercase=True, reverse=True)
        'OLLEH'
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
    A sample function that validates numbers within ranges.
    
    Args:
        number: Number to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        
    Returns:
        tuple: (is_valid, message)
        
    Examples:
        >>> sample_number_validator(5, 1, 10)
        (True, 'Number 5 is valid')
        >>> sample_number_validator(15, 1, 10)
        (False, 'Number 15 is too high (max: 10)')
    """
    if not isinstance(number, (int, float)):
        return False, "Input must be a number"
    
    if min_value is not None and number < min_value:
        return False, f"Number {number} is too low (min: {min_value})"
    
    if max_value is not None and number > max_value:
        return False, f"Number {number} is too high (max: {max_value})"
    
    return True, f"Number {number} is valid"


# Lazy version for testing lazy evaluation coverage
sample_string_processor_lazy = lazy(sample_string_processor, str) 