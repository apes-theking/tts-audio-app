import unittest
from unittest.mock import MagicMock
import sys
import os

# Mock dependencies globally before import
sys.modules["streamlit"] = MagicMock()
sys.modules["edge_tts"] = MagicMock()
sys.modules["fitz"] = MagicMock()
sys.modules["docx"] = MagicMock()
sys.modules["pytesseract"] = MagicMock()
sys.modules["pdf2image"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["cv2"] = MagicMock()
sys.modules["numpy"] = MagicMock()

# Add repo root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app

class TestExtraction(unittest.TestCase):

    def test_extract_pdf_pages(self):
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        # Make text long enough > 50 chars to avoid OCR fallback
        mock_page1.get_text.return_value = "Page 1 Text " * 10
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "Page 2 Text " * 10
        mock_doc.__iter__.return_value = [mock_page1, mock_page2]

        app.fitz.open.return_value.__enter__.return_value = mock_doc

        file_mock = MagicMock()
        file_mock.read.return_value = b"pdf_content"

        pages = app.extract_text_from_pdf(file_mock)

        self.assertEqual(len(pages), 2)
        self.assertTrue(pages[0].startswith("Page 1 Text"))

    def test_extract_docx_chunks(self):
        mock_doc = MagicMock()
        p1 = MagicMock(); p1.text = "Paragraph 1"
        p2 = MagicMock(); p2.text = "Paragraph 2"
        mock_doc.paragraphs = [p1, p2]

        app.docx.Document.return_value = mock_doc

        file_mock = MagicMock()
        pages = app.extract_text_from_docx(file_mock)

        self.assertEqual(len(pages), 1)
        self.assertIn("Paragraph 1", pages[0])

    def test_extract_docx_large_chunks(self):
        mock_doc = MagicMock()
        p1 = MagicMock(); p1.text = "A" * 600
        p2 = MagicMock(); p2.text = "B" * 600
        mock_doc.paragraphs = [p1, p2]

        app.docx.Document.return_value = mock_doc

        file_mock = MagicMock()
        pages = app.extract_text_from_docx(file_mock)

        self.assertEqual(len(pages), 2)
        self.assertIn("A"*600, pages[0])
        self.assertIn("B"*600, pages[1])

    def test_extract_image(self):
        app.pytesseract.image_to_string.return_value = "Image Text"
        # Since extract_text_from_image now accepts an image directly (PIL or numpy),
        # we pass a mock object representing the image.
        image_mock = MagicMock()

        pages = app.extract_text_from_image(image_mock)

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0], "Image Text")

    def test_clean_text(self):
        raw_text = "Line 1\n\n\nLine 2   \nLine 3"
        cleaned = app.clean_text(raw_text)
        expected = "Line 1\nLine 2\nLine 3"
        self.assertEqual(cleaned, expected)

if __name__ == '__main__':
    unittest.main()
