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

class TestPagination(unittest.TestCase):

    def setUp(self):
        # Use our custom SessionState
        app.st.session_state = SessionState()

    def test_delete_middle_page(self):
        # Setup: 3 pages, current is page 1 (index 1)
        app.st.session_state.pages = ["Page 1", "Page 2", "Page 3"]
        app.st.session_state.current_page = 1

        # Action
        app.delete_page()

        # Verify: "Page 2" should be gone. List length 2.
        self.assertEqual(len(app.st.session_state.pages), 2)
        # We expect Page 2 to be removed. So remaining are Page 1 and Page 3.
        self.assertEqual(app.st.session_state.pages, ["Page 1", "Page 3"])

        # Current index should stay 1 (which is now "Page 3")
        self.assertEqual(app.st.session_state.current_page, 1)

        # Editor content should update to "Page 3"
        self.assertEqual(app.st.session_state.editor, "Page 3")

    def test_delete_last_page(self):
        # Setup: 3 pages, current is page 2 (index 2, last)
        app.st.session_state.pages = ["Page 1", "Page 2", "Page 3"]
        app.st.session_state.current_page = 2

        # Action
        app.delete_page()

        # Verify: "Page 3" gone. List length 2.
        self.assertEqual(len(app.st.session_state.pages), 2)
        self.assertEqual(app.st.session_state.pages, ["Page 1", "Page 2"])

        # Current index should decrement to 1 (new last page "Page 2")
        self.assertEqual(app.st.session_state.current_page, 1)

        # Editor content should update to "Page 2"
        self.assertEqual(app.st.session_state.editor, "Page 2")

    def test_delete_only_page(self):
        # Setup: 1 page, current 0
        app.st.session_state.pages = ["Page 1"]
        app.st.session_state.current_page = 0

        # Action
        app.delete_page()

        # Verify: List empty
        self.assertEqual(len(app.st.session_state.pages), 0)

        # Current index should be 0 (max(0, -1))
        self.assertEqual(app.st.session_state.current_page, 0)

        # Editor content should be empty string
        self.assertEqual(app.st.session_state.editor, "")

if __name__ == '__main__':
    unittest.main()
