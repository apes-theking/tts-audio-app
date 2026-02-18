import unittest
from unittest.mock import MagicMock, call
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

class TestPreprocessing(unittest.TestCase):

    def test_process_image_pipeline(self):
        # Setup mocks
        mock_pil_image = MagicMock()
        mock_np_array = MagicMock()
        # Mock shape to be RGB (H, W, 3)
        mock_np_array.shape = (100, 100, 3)
        app.np.array.return_value = mock_np_array

        mock_gray = MagicMock()
        app.cv2.cvtColor.return_value = mock_gray

        mock_blurred = MagicMock()
        app.cv2.GaussianBlur.return_value = mock_blurred

        mock_thresh = MagicMock()
        app.cv2.adaptiveThreshold.return_value = mock_thresh

        # Call function
        result = app.process_image_for_ocr(mock_pil_image)

        # Verify result is the final thresholded image
        self.assertEqual(result, mock_thresh)

        # Verify steps
        # 1. Convert to numpy
        app.np.array.assert_called_once_with(mock_pil_image)

        # 2. Convert to Grayscale
        app.cv2.cvtColor.assert_called_once_with(mock_np_array, app.cv2.COLOR_RGB2GRAY)

        # 3. Gaussian Blur
        app.cv2.GaussianBlur.assert_called_once_with(mock_gray, (5, 5), 0)

        # 4. Adaptive Threshold
        app.cv2.adaptiveThreshold.assert_called_once_with(
            mock_blurred, 255, app.cv2.ADAPTIVE_THRESH_GAUSSIAN_C, app.cv2.THRESH_BINARY, 11, 2
        )

if __name__ == '__main__':
    unittest.main()
