import os
import tempfile
from unittest import TestCase

import pyautogui
from PIL import Image

from auto.simulator.xy import take_screenshot

# Editable constants for test configuration
TOP_CROP = 200  # Pixels to crop from top
LEFT_CROP = 1000  # Pixels to crop from left
CROP_WIDTH = 100  # Width for cropped region
CROP_HEIGHT = 300  # Height for cropped region
LAST_SCREENSHOT_PATH = "../src/last_screenshot.png"


class TestTakeScreenshotWithCropRegion(TestCase):
    @classmethod
    def setUpClass(cls):
        """Create temp directory and get active window before tests"""
        cls.temp_dir = tempfile.mkdtemp(prefix="screenshot_test_")
        cls.window = pyautogui.getActiveWindow()
        if not cls.window:
            raise Exception("No active window found for testing")

    @classmethod
    def tearDownClass(cls):
        """Clean up test directory after tests"""
        for f in os.listdir(cls.temp_dir):
            os.remove(os.path.join(cls.temp_dir, f))
        os.rmdir(cls.temp_dir)

    def setUp(self):
        """Set up fresh screenshot path for each test"""
        self.screenshot_path = os.path.join(self.temp_dir, LAST_SCREENSHOT_PATH)
        take_screenshot.last_screenshot_path = self.screenshot_path

    def test_full_screenshot(self):
        """Test with no cropping (empty crop_region)"""
        result = take_screenshot(crop_region=[])

        self.assertTrue(os.path.exists(result))
        with Image.open(result) as img:
            self.assertEqual(img.width, self.window.width)
            self.assertEqual(img.height, self.window.height)

    def test_top_crop_only(self):
        """Test cropping only from top [x, y, width, height]"""
        result = take_screenshot(crop_region=[0, TOP_CROP, None, None])

        self.assertTrue(os.path.exists(result))
        with Image.open(result) as img:
            self.assertEqual(img.width, self.window.width)
            self.assertEqual(img.height, self.window.height - TOP_CROP)

    def test_left_crop_only(self):
        """Test cropping only from left [x, y, width, height]"""
        result = take_screenshot(crop_region=[LEFT_CROP, 0, None, None])

        self.assertTrue(os.path.exists(result))
        with Image.open(result) as img:
            self.assertEqual(img.width, self.window.width - LEFT_CROP)
            self.assertEqual(img.height, self.window.height)

    def test_position_and_dimensions(self):
        """Test cropping with position and dimensions [x, y, width, height]"""
        result = take_screenshot(crop_region=[LEFT_CROP, TOP_CROP, CROP_WIDTH, CROP_HEIGHT])

        self.assertTrue(os.path.exists(result))
        with Image.open(result) as img:
            self.assertEqual(img.width, CROP_WIDTH)
            self.assertEqual(img.height, CROP_HEIGHT)

    def test_partial_crop_region(self):
        """Test with partial crop region specifications"""
        # Test with just width/height
        result = take_screenshot(crop_region=[None, None, CROP_WIDTH, CROP_HEIGHT])
        self.assertTrue(os.path.exists(result))
        with Image.open(result) as img:
            self.assertLessEqual(img.width, CROP_WIDTH)
            self.assertLessEqual(img.height, CROP_HEIGHT)

    def test_partial_start_region(self):
        # Test with just x/y position
        result = take_screenshot(crop_region=[LEFT_CROP, TOP_CROP, None, None])
        self.assertTrue(os.path.exists(result))
        with Image.open(result) as img:
            self.assertEqual(img.width, self.window.width - LEFT_CROP)
            self.assertEqual(img.height, self.window.height - TOP_CROP)
