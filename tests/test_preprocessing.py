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
sys.modules["PIL.ImageOps"] = MagicMock()
sys.modules["cv2"] = MagicMock()
sys.modules["numpy"] = MagicMock()

# Add repo root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app

class TestPreprocessing(unittest.TestCase):

    def setUp(self):
        # Reset mock call counts before each test
        app.np.array.reset_mock()
        app.ImageOps.exif_transpose.reset_mock()
        app.cv2.cvtColor.reset_mock()
        app.cv2.filter2D.reset_mock()
        app.cv2.threshold.reset_mock()

    def test_process_image_pipeline(self):
        # Setup mocks
        mock_pil_image = MagicMock()
        mock_pil_image.width = 1000  # Small image, no resize
        app.ImageOps.exif_transpose.return_value = mock_pil_image

        mock_np_array = MagicMock()
        mock_np_array.shape = (100, 100, 3) # RGB
        # side_effect needs to cover all calls. np.array is called for the image AND for kernel creation
        # We'll just set return_value instead of side_effect to avoid StopIteration if called more than expected
        app.np.array.return_value = mock_np_array

        mock_gray = MagicMock()
        app.cv2.cvtColor.return_value = mock_gray

        mock_sharpened = MagicMock()
        app.cv2.filter2D.return_value = mock_sharpened

        mock_thresh_ret = (0, MagicMock())
        app.cv2.threshold.return_value = mock_thresh_ret

        # Call function
        result = app.process_image_for_ocr(mock_pil_image, threshold_value=128)

        # Verify result
        self.assertEqual(result, mock_thresh_ret[1])

        # Verify Steps:
        # 1. EXIF Transpose
        app.ImageOps.exif_transpose.assert_called_once_with(mock_pil_image)

        # 2. Convert to Numpy (should happen at least once for image)
        app.np.array.assert_any_call(mock_pil_image)

        # 3. Sharpening
        # Verify filter2D is called
        app.cv2.filter2D.assert_called_once_with(mock_gray, -1, unittest.mock.ANY)

        # 4. Threshold
        app.cv2.threshold.assert_called_once_with(
            mock_sharpened, 128, 255, app.cv2.THRESH_BINARY
        )

    def test_process_image_resize(self):
        # Setup large image mock
        mock_pil_image = MagicMock()
        mock_pil_image.width = 4000
        mock_pil_image.height = 2000
        # exif_transpose returns the same image mock
        app.ImageOps.exif_transpose.return_value = mock_pil_image

        # Mock resize return value
        resized_image = MagicMock()
        resized_image.width = 3000
        mock_pil_image.resize.return_value = resized_image

        app.np.array.return_value = MagicMock() # Mock array conversion
        app.cv2.cvtColor.return_value = MagicMock()
        app.cv2.filter2D.return_value = MagicMock()
        app.cv2.threshold.return_value = (0, MagicMock())

        # Call function
        app.process_image_for_ocr(mock_pil_image)

        # Verify Resize was called on the transposed image (mock_pil_image)
        expected_new_height = int(3000 * (2000 / 4000)) # 1500

        # We need to verify resize is called on the object returned by exif_transpose
        mock_pil_image.resize.assert_called_once_with(
            (3000, expected_new_height), app.Image.Resampling.LANCZOS
        )

if __name__ == '__main__':
    unittest.main()
