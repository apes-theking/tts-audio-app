import unittest
from unittest.mock import MagicMock, call
import sys
import os
import io

# Mock dependencies globally before import
sys.modules["streamlit"] = MagicMock()
sys.modules["edge_tts"] = MagicMock()
sys.modules["fitz"] = MagicMock()
sys.modules["docx"] = MagicMock()
sys.modules["pytesseract"] = MagicMock()
sys.modules["pdf2image"] = MagicMock()
sys.modules["PIL"] = MagicMock()
sys.modules["PIL.Image"] = MagicMock()
sys.modules["PIL.ImageOps"] = MagicMock()
sys.modules["cv2"] = MagicMock()
sys.modules["numpy"] = MagicMock()

# Add repo root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app

# Helper to emulate Streamlit Session State
class SessionState(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

class TestApp(unittest.TestCase):

    def setUp(self):
        # Use our custom SessionState
        app.st.session_state = SessionState()
        # Reset mocks
        app.st.file_uploader.reset_mock()
        app.st.slider.reset_mock()
        app.st.spinner.reset_mock()
        app.st.button.reset_mock()

        # Mock selectbox to return a valid key
        app.st.sidebar.selectbox.return_value = "Australian Female"

        # Mock columns to return 4 dummy objects so unpacking works
        app.st.columns.return_value = (MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_named_bytes_io(self):
        # Verify the helper class works
        wrapper = app.NamedBytesIO(b"content", "file.pdf", 123)
        self.assertEqual(wrapper.getvalue(), b"content")
        self.assertEqual(wrapper.name, "file.pdf")
        self.assertEqual(wrapper.size, 123)
        self.assertIsInstance(wrapper, io.BytesIO)

    def test_upload_persistence(self):
        # Mock file uploader returning a file
        mock_file = MagicMock()
        mock_file.name = "test.pdf"
        mock_file.size = 100
        mock_file.getvalue.return_value = b"test_pdf_content"
        app.st.file_uploader.return_value = mock_file

        # We need to mock extract_text_from_pdf to avoid calling mocked fitz directly which might crash
        # And mock clean_text to avoid string ops on mocks
        with unittest.mock.patch('app.extract_text_from_pdf') as mock_extract, \
             unittest.mock.patch('app.clean_text') as mock_clean:

            mock_extract.return_value = ["Page 1"]
            mock_clean.return_value = "Cleaned Text"

            app.main()

            # Verify bytes are stored in session state
            self.assertEqual(app.st.session_state.uploaded_file_bytes, b"test_pdf_content")
            self.assertEqual(app.st.session_state.uploaded_file_name, "test.pdf")

            # Verify processing uses the bytes (active_file in main)
            # We check if extract_text_from_pdf was called with a BytesIO object containing our content
            # And crucially, checking if it has .name and .size attributes
            args, _ = mock_extract.call_args
            passed_file = args[0]
            self.assertIsInstance(passed_file, io.BytesIO) # NamedBytesIO inherits BytesIO
            self.assertEqual(passed_file.getvalue(), b"test_pdf_content")
            # If we were using raw BytesIO, passed_file.name would fail or be missing if not set.
            # In our main code, we create NamedBytesIO if persisting.
            # Wait, in the FIRST run (upload just happened), active_file is derived from session state ONLY IF persisted.
            # In `main`:
            # 1. uploaded_file is saved to session state.
            # 2. active_file is constructed from session state.
            # So passed_file SHOULD be NamedBytesIO.
            self.assertIsInstance(passed_file, app.NamedBytesIO)
            self.assertEqual(passed_file.name, "test.pdf")

    def test_upload_persistence_recovery(self):
        # Simulate case where file_uploader returns None but session has bytes
        app.st.file_uploader.return_value = None
        # Pre-populate session state
        app.st.session_state.uploaded_file_bytes = b"persisted_content"
        app.st.session_state.uploaded_file_name = "persisted.pdf"
        app.st.session_state.uploaded_file_size = 200

        # Run main logic
        with unittest.mock.patch('app.extract_text_from_pdf') as mock_extract, \
             unittest.mock.patch('app.clean_text') as mock_clean:

            mock_extract.return_value = ["Page 1"]
            mock_clean.return_value = "Cleaned Text"

            app.main()

            # Verify processing still happens with persisted bytes
            # extract_text_from_pdf should be called
            self.assertTrue(mock_extract.called)
            args, _ = mock_extract.call_args
            passed_file = args[0]
            self.assertIsInstance(passed_file, app.NamedBytesIO)
            self.assertEqual(passed_file.getvalue(), b"persisted_content")
            self.assertEqual(passed_file.name, "persisted.pdf")

    def test_reset_app(self):
        # Setup session state with some data
        app.st.session_state.uploaded_file_bytes = b"data"

        # Call reset
        app.reset_app()

        # Verify clear called
        self.assertEqual(len(app.st.session_state), 0)

        # Verify rerun called
        app.st.rerun.assert_called_once()

if __name__ == '__main__':
    unittest.main()
