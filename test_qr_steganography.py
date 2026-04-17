"""
Comprehensive Tests for QR Code Steganography Generator
"""

import unittest
import sys
import io
from PIL import Image
import numpy as np

# Import the module to test (using fixed version)
try:
    from qr_steganography_fixed import QRCodeProcessor, MainWindow
except ImportError:
    from qr_steganography import QRCodeProcessor, MainWindow


class TestQRCodeProcessor(unittest.TestCase):
    """Tests for QRCodeProcessor class."""
    
    def setUp(self):
        self.processor = QRCodeProcessor()
        # Create a simple test background image
        self.bg_image = Image.new('RGB', (200, 200), color=(100, 150, 200))
    
    def test_generate_qr_code_basic(self):
        """Test basic QR code generation."""
        qr_result = self.processor.generate_qr_code("Hello World", version=7, error_correction='H')
        
        self.assertIsNotNone(qr_result)
        # qrcode library returns PilImage wrapper - extract actual PIL Image
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            qr_image = qr_result.img
        else:
            qr_image = qr_result
        
        self.assertIsInstance(qr_image, Image.Image)
        # Version 7 QR code: modules_per_side = 4*version + 17 = 45
        # With box_size=10 and border=4 on each side
        # Size = 45 * 10 + 8 (border) = 458, but actual may vary due to padding
        self.assertGreater(qr_image.width, 400)
        self.assertEqual(qr_image.width, qr_image.height)  # QR codes are square
        print(f"QR code generated successfully: {qr_image.size}")
    
    def test_generate_qr_code_error_correction(self):
        """Test different error correction levels."""
        for level in ['L', 'M', 'Q', 'H']:
            with self.subTest(level=level):
                qr_result = self.processor.generate_qr_code("Test Data", version=5, error_correction=level)
                self.assertIsNotNone(qr_result)
    
    def test_generate_qr_code_version_range(self):
        """Test QR code generation with different versions."""
        for version in [1, 7, 20, 40]:
            with self.subTest(version=version):
                qr_result = self.processor.generate_qr_code("V", version=version, error_correction='H')
                self.assertIsNotNone(qr_result)
    
    def test_resize_qr_to_background(self):
        """Test QR code resizing."""
        qr_result = self.processor.generate_qr_code("Test", version=5, error_correction='H')
        # Extract PIL Image from wrapper
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            self.qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            self.qr_image = qr_result.img
        else:
            self.qr_image = qr_result
        
        resized = self.processor.resize_qr_to_background(100)
        self.assertEqual(resized.width, 100)
        # Height should be proportional (QR codes are square)
        self.assertEqual(resized.height, 100)
    
    def test_resize_qr_to_background_no_qr(self):
        """Test resize when no QR code exists."""
        fresh_processor = QRCodeProcessor()
        with self.assertRaises(ValueError):
            fresh_processor.resize_qr_to_background(100)
    
    def test_create_mask_from_image(self):
        """Test mask creation from image."""
        # Create a gradient image for testing
        gradient = Image.new('L', (100, 100))
        pixels = gradient.load()
        for y in range(100):
            for x in range(100):
                pixels[x, y] = int((y / 99) * 255)
        
        mask = self.processor.create_mask_from_image(gradient, threshold=0.5)
        
        self.assertEqual(mask.size, (100, 100))
        self.assertEqual(mask.mode, 'L')
        
        # Verify thresholding
        mask_array = np.array(mask)
        for y in range(50):  # Lower half should be black (below threshold)
            self.assertTrue(np.all(mask_array[y] == 0))
        for y in range(50, 100):  # Upper half should be white
            self.assertTrue(np.all(mask_array[y] == 255))
    
    def test_qr_over_image(self):
        """Test QR code overlaid on background."""
        qr_result = self.processor.generate_qr_code("TEST", version=3, error_correction='H')
        # Extract PIL Image from wrapper
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            qr_image = qr_result.img
        else:
            qr_image = qr_result
        
        result = self.processor.qr_over_image(qr_image, self.bg_image)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.size, self.bg_image.size)
        self.assertIn(result.mode, ['RGBA', 'RGB'])
    
    def test_qr_over_image_resize(self):
        """Test QR code resized to match background."""
        qr_result = self.processor.generate_qr_code("TEST", version=3, error_correction='H')
        # Extract PIL Image from wrapper
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            qr_image = qr_result.img
        else:
            qr_image = qr_result
        large_bg = Image.new('RGB', (500, 500), color=(200, 100, 50))
        
        result = self.processor.qr_over_image(qr_image, large_bg, resize_qr_to_bg=True)
        
        self.assertEqual(result.size, large_bg.size)
    
    def test_image_over_qr_with_tinting(self):
        """Test background image overlaid on QR code with tinting."""
        qr_result = self.processor.generate_qr_code("TEST", version=3, error_correction='H')
        # Extract PIL Image from wrapper
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            qr_image = qr_result.img
        else:
            qr_image = qr_result
        
        result = self.processor.image_over_qr_with_tinting(qr_image, self.bg_image)
        
        self.assertIsNotNone(result)
        # Result should match QR code size
        self.assertEqual(result.size, qr_image.size)
    
    def test_save_image_png(self):
        """Test saving RGBA image as PNG."""
        test_image = Image.new('RGBA', (50, 50), color=(255, 0, 0, 128))
        
        buffer = io.BytesIO()
        self.processor.save_image(test_image, buffer)
        buffer.seek(0)
        
        loaded = Image.open(buffer)
        self.assertEqual(loaded.size, (50, 50))
    
    def test_save_image_rgb(self):
        """Test saving RGB image."""
        test_image = Image.new('RGB', (50, 50), color=(0, 255, 0))
        
        buffer = io.BytesIO()
        self.processor.save_image(test_image, buffer)
        buffer.seek(0)
        
        loaded = Image.open(buffer)
        self.assertEqual(loaded.size, (50, 50))
    
    def test_long_content(self):
        """Test QR code with longer content."""
        long_text = "A" * 200  # Longer content
        qr_result = self.processor.generate_qr_code(long_text, version=10, error_correction='H')
        
        self.assertIsNotNone(qr_result)
    
    def test_performance_qr_over_image(self):
        """Performance test for qr_over_image method."""
        import time
        
        qr_result = self.processor.generate_qr_code("PERF", version=7, error_correction='H')
        # Extract PIL Image from wrapper
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            qr_image = qr_result.img
        else:
            qr_image = qr_result
        large_bg = Image.new('RGB', (400, 400), color=(128, 128, 128))
        
        start_time = time.perf_counter()
        result = self.processor.qr_over_image(qr_image, large_bg)
        elapsed = time.perf_counter() - start_time
        
        print(f"\nqr_over_image performance: {elapsed:.3f}s for 400x400 image")
        # Should complete in reasonable time (< 5 seconds for this size)
        self.assertLess(elapsed, 5.0, "qr_over_image took too long - consider optimization")
    
    def test_performance_image_over_qr(self):
        """Performance test for image_over_qr_with_tinting method."""
        import time
        
        qr_result = self.processor.generate_qr_code("PERF", version=7, error_correction='H')
        # Extract PIL Image from wrapper
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            qr_image = qr_result.img
        else:
            qr_image = qr_result
        large_bg = Image.new('RGB', (400, 400), color=(128, 128, 128))
        
        start_time = time.perf_counter()
        result = self.processor.image_over_qr_with_tinting(qr_image, large_bg)
        elapsed = time.perf_counter() - start_time
        
        print(f"\nimage_over_qr_with_tinting performance: {elapsed:.3f}s for 400x400 image")
        # This method is known to be slow due to nested loops
        self.assertLess(elapsed, 10.0, "image_over_qr took too long - needs optimization")


class TestMainWindow(unittest.TestCase):
    """Tests for MainWindow class."""
    
    def test_initialization(self):
        """Test window initialization doesn't crash."""
        # Note: This requires a Qt event loop, so we skip in headless mode
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication(sys.argv)
            window = MainWindow()
            self.assertIsInstance(window, MainWindow)
            self.assertIsNotNone(window.processor)
        except ImportError:
            self.skipTest("PyQt6 not available")
    
    def test_bg_image_initialization(self):
        """Test that bg_image and related attributes are properly initialized."""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication(sys.argv)
            window = MainWindow()
            # This should not raise AttributeError - bg_image should be None initially
            self.assertTrue(hasattr(window, 'bg_image'))
            self.assertIsNone(window.bg_image)  # Should be None by default
            
            # Also check background_opacity is initialized (default 15%)
            self.assertTrue(hasattr(window, 'background_opacity'))
            self.assertEqual(window.background_opacity, 0.15)  # Default: 15%
            
            # Check tint_intensity is initialized (default 20%)
            self.assertTrue(hasattr(window, 'tint_intensity'))
            self.assertEqual(window.tint_intensity, 0.20)  # Default: 20%
            
            # Check positioning attributes are initialized
            self.assertTrue(hasattr(window, 'bg_scale_factor'))
            self.assertEqual(window.bg_scale_factor, 1.0)
            self.assertTrue(hasattr(window, 'bg_x_offset'))
            self.assertEqual(window.bg_x_offset, 0)
            self.assertTrue(hasattr(window, 'bg_y_offset'))
            self.assertEqual(window.bg_y_offset, 0)
            self.assertTrue(hasattr(window, 'interactive_preview'))
            self.assertFalse(window.interactive_preview)  # Default: False
        except ImportError:
            self.skipTest("PyQt6 not available")


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow."""
    
    def test_full_workflow_qr_over_image(self):
        """Test complete QR over image workflow."""
        processor = QRCodeProcessor()
        bg_image = Image.new('RGB', (300, 300), color=(50, 100, 150))
        
        # Generate QR code
        qr_result = processor.generate_qr_code("https://example.com", version=7, error_correction='H')
        self.assertIsNotNone(qr_result)
        # Extract PIL Image from wrapper
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            qr_image = qr_result.img
        else:
            qr_image = qr_result
        
        # Apply steganography
        result = processor.qr_over_image(qr_image, bg_image)
        self.assertEqual(result.size, (300, 300))
        
        # Save to buffer
        buffer = io.BytesIO()
        processor.save_image(result, buffer)
        self.assertGreater(len(buffer.getvalue()), 0)
    
    def test_full_workflow_tinted_qr(self):
        """Test complete tinted QR workflow."""
        processor = QRCodeProcessor()
        bg_image = Image.new('RGB', (300, 300), color=(200, 150, 100))
        
        # Generate QR code
        qr_result = processor.generate_qr_code("TEST DATA", version=5, error_correction='H')
        self.assertIsNotNone(qr_result)
        # Extract PIL Image from wrapper
        if hasattr(qr_result, '_img') and qr_result._img is not None:
            qr_image = qr_result._img
        elif hasattr(qr_result, 'img'):
            qr_image = qr_result.img
        else:
            qr_image = qr_result
        
        # Apply tinted steganography
        result = processor.image_over_qr_with_tinting(qr_image, bg_image)
        self.assertEqual(result.size, qr_image.size)
        
        # Save to buffer
        buffer = io.BytesIO()
        processor.save_image(result, buffer)
        self.assertGreater(len(buffer.getvalue()), 0)


def run_tests():
    """Run all tests and return results."""
    print("="*60)
    print("Running QR Code Steganography Tests")
    print("="*60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestQRCodeProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestMainWindow))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
