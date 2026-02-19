import sys
from unittest.mock import MagicMock

# Mock dependencies that are not available in the environment
sys.modules["streamlit"] = MagicMock()
sys.modules["edge_tts"] = MagicMock()
sys.modules["fitz"] = MagicMock()
sys.modules["docx"] = MagicMock()

from app import clean_text

def test_clean_text_empty():
    assert clean_text("") == ""

def test_clean_text_whitespace_only():
    assert clean_text("   ") == ""
    assert clean_text("\n\n\n") == ""
    assert clean_text(" \n \n ") == ""

def test_clean_text_multiple_newlines():
    input_text = "Line 1\n\n\nLine 2"
    expected = "Line 1\nLine 2"
    assert clean_text(input_text) == expected

def test_clean_text_leading_trailing_whitespace():
    input_text = "  Line 1  \n  Line 2  "
    expected = "Line 1\nLine 2"
    assert clean_text(input_text) == expected

def test_clean_text_mixed_whitespace():
    input_text = "\n  Line 1  \n\n \n  Line 2  \n"
    expected = "Line 1\nLine 2"
    assert clean_text(input_text) == expected

def test_clean_text_already_clean():
    input_text = "Line 1\nLine 2"
    assert clean_text(input_text) == input_text
