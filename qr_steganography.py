"""
QR Code Steganography Generator

Creates QR codes that can be hidden within or overlaid on images,
making the QR code less conspicuous while remaining scannable.
"""

import sys
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from PIL import Image, ImageFilter
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QLineEdit, QSpinBox, QComboBox, QGroupBox,
    QRadioButton, QButtonGroup, QScrollArea, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QPixmap, QImage, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QLineEdit, QSpinBox, QComboBox, QGroupBox,
    QRadioButton, QButtonGroup, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QAction
import io
import numpy as np

class QRCodeProcessor:
    """
    Handles all QR code generation and image processing operations.
    """
    
    def __init__(self):
        self.qr_code = None
        self.qr_image = None
        self.background_image = None
        
    def generate_qr_code(self, data: str, version: int = 7, error_correction: str = 'H') -> Image.Image:
        """
        Generate a QR code image.
        
        Args:
            data: The content to encode in the QR code
            version: QR code version (1-40), affects module count and size
            error_correction: Error correction level ('L', 'M', 'Q', 'H')
                          H = High, can recover ~30% of damaged data
        
        Returns:
            PIL Image containing the generated QR code
        """
        # Map error correction level to constant
        ec_map = {
            'L': ERROR_CORRECT_L,
            'M': ERROR_CORRECT_M,
            'Q': ERROR_CORRECT_Q,
            'H': ERROR_CORRECT_H
        }
        
        qr_code = qrcode.QRCode(
            version=version,
            error_correction=ec_map.get(error_correction, ERROR_CORRECT_H),
            box_size=10,  # Base module size (will be scaled later)
            border=4       # Quiet zone border
        )
        qr_code.add_data(data)
        self.qr_code = qr_code
        
        qr_image = qr_code.make_image(fill_color="black", back_color="white")
        self.qr_image = qr_image
        return qr_image
    
    def resize_qr_to_background(self, qr_size: int) -> Image.Image:
        """
        Resize the QR code to match a specified size.
        """
        if self.qr_image is None:
            raise ValueError("No QR code generated yet")
        
        # Calculate scale factor
        original_width, _ = self.qr_image.size
        scale_factor = qr_size / original_width
        new_height = int(self.qr_image.height * scale_factor)
        
        resized_qr = self.qr_image.resize((qr_size, new_height), Image.Resampling.LANCZOS)
        return resized_qr
    
    def create_mask_from_image(self, image: Image.Image, threshold: float = 0.5) -> Image.Image:
        """
        Create a binary mask from an RGB image.
        Pixels above the brightness threshold become white (QR visible).
        Pixels below become black (image shows through).
        
        Args:
            image: The source image
            threshold: Brightness threshold (0.0-1.0)
            
        Returns:
            Binary mask image (black and white)
        """
        # Convert to grayscale and then binary
        gray = image.convert('L')
        threshold_value = int(255 * threshold)
        
        # Create binary mask
        mask_array = np.array(gray)
        mask_array[mask_array > threshold_value] = 255
        mask_array[mask_array <= threshold_value] = 0
        
        return Image.fromarray(mask_array, mode='L')
    
    def qr_over_image(self, qr_image: Image.Image, bg_image: Image.Image, 
                      resize_qr_to_bg: bool = True) -> Image.Image:
        """
        Place QR code OVER the background image with transparency.
        White modules in QR become transparent, revealing the background.
        Black modules show as black (or tinted).
        
        This creates an "invisibility cloak" effect where parts of the
        background show through the QR code's white areas.
        
        Uses vectorized numpy operations for performance.
        """
        bg_width, bg_height = bg_image.size
        
        # Resize QR to match background if requested
        qr_size = bg_width if resize_qr_to_bg else qr_image.width
        if resize_qr_to_bg:
            qr_image = self.resize_qr_to_background(qr_size)
        
        qr_width, qr_height = qr_image.size
        
        # Center QR on background
        x_offset = max(0, (bg_width - qr_width) // 2)
        y_offset = max(0, (bg_height - qr_height) // 2)
        
        # Convert images to numpy arrays
        bg_array = np.array(bg_image.convert('RGBA'))
        result = bg_array.copy()
        
        qr_rgba_array = np.array(qr_image.convert('RGBA'))
        qr_gray_array = np.array(qr_image.convert('L'))
        
        # Create mask: black modules (value <= 127) should be visible
        # White modules become transparent
        visible_mask = qr_gray_array <= 127
        
        # Calculate destination bounds
        dest_x_start, dest_y_start = x_offset, y_offset
        dest_x_end = min(dest_x_start + qr_width, bg_width)
        dest_y_end = min(dest_y_start + qr_height, bg_height)
        
        src_x_end = dest_x_end - dest_x_start
        src_y_end = dest_y_end - dest_y_start
        
        # Apply QR to result using vectorized operations
        if visible_mask.any():
            # Copy RGBA channels where mask is True (black modules)
            for channel in range(4):
                result[dest_y_start:dest_y_end, dest_x_start:dest_x_end, channel] = np.where(
                    visible_mask[:src_y_end, :src_x_end],
                    qr_rgba_array[:src_y_end, :src_x_end, channel],
                    result[dest_y_start:dest_y_end, dest_x_start:dest_x_end, channel]
                )
        
        return Image.fromarray(result, mode='RGBA')
    
    def image_over_qr_with_tinting(self, qr_image: Image.Image, bg_image: Image.Image,
                                   resize_bg_to_qr: bool = True) -> Image.Image:
        """
        Place background image OVER the QR code with color tinting.
        Black QR modules are tinted to match colors from the background.
        
        This makes the QR code blend into the background while maintaining
        contrast for scanning.
        
        Uses vectorized numpy operations for performance.
        """
        qr_width, qr_height = qr_image.size
        bg_width, bg_height = bg_image.size
        
        # Resize background to match QR if requested
        if resize_bg_to_qr:
            aspect_ratio = qr_height / qr_width
            new_bg_height = int(bg_width * aspect_ratio)
            if new_bg_height > 0:
                bg_image = bg_image.resize((bg_width, new_bg_height), Image.Resampling.LANCZOS)
        
        # Center background on QR
        x_offset = max(0, (qr_width - bg_width) // 2)
        y_offset = max(0, (qr_height - bg_height) // 2)
        
        # Convert images to numpy arrays
        qr_gray_array = np.array(qr_image.convert('L'))
        bg_array = np.array(bg_image.convert('RGB')).astype(np.float32)
        
        # Create result array - start with white background
        result_array = np.ones((qr_height, qr_width, 3), dtype=np.uint8) * 255
        
        # Identify black QR modules (value <= 127)
        black_modules_mask = qr_gray_array <= 127
        
        if black_modules_mask.any():
            # Get coordinates of black modules
            black_y, black_x = np.where(black_modules_mask)
            
            # Calculate corresponding background positions
            bg_x = black_x + x_offset
            bg_y = black_y + y_offset
            
            # Filter valid background positions
            valid_mask = (bg_x >= 0) & (bg_x < bg_width) & (bg_y >= 0) & (bg_y < bg_height)
            
            if valid_mask.any():
                valid_bg_x = bg_x[valid_mask]
                valid_bg_y = bg_y[valid_mask]
                valid_qr_x = black_x[valid_mask]
                valid_qr_y = black_y[valid_mask]
                
                # Get background colors at these positions
                for qx, qy, bx, by in zip(valid_qr_x, valid_bg_y, valid_bg_x, bg_y):
                    if 0 <= bx < bg_width and 0 <= by < bg_height:
                        bg_color = bg_array[by, bx]
                        # Apply tint factor to reduce brightness while maintaining color
                        tinted_color = np.clip(bg_color * 0.3, 0, 255).astype(np.uint8)
                        result_array[qy, qx] = tinted_color
        
        return Image.fromarray(result_array, mode='RGB')
    
    def save_image(self, image: Image.Image, filepath: str):
        """
        Save the generated image to file.
        """
        if image.mode == 'RGBA':
            image.save(filepath, 'PNG')
        else:
            image.save(filepath)


class MainWindow(QMainWindow):
    """
    Main GUI window for QR Code Steganography Generator.
    """
    
    def __init__(self):
        super().__init__()
        self.processor = QRCodeProcessor()
        self.current_result = None
        self.bg_image = None  # Initialize background image to None
        self.setup_ui()
        
    def setup_ui(self):
        """
        Set up the user interface.
        """
        self.setWindowTitle("QR Code Steganography Generator")
        self.setMinimumSize(900, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        
        # Left panel - Controls
        left_panel = QVBoxLayout()
        
        # Title
        title_label = QLabel("QR Code Steganography Generator")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        left_panel.addWidget(title_label)
        
        # Input Group
        input_group = QGroupBox("Input Settings")
        input_layout = QVBoxLayout()
        
        # URL/Content entry
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL or Content:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter text or URL for QR code...")
        url_layout.addWidget(self.url_input)
        input_layout.addLayout(url_layout)
        
        # Error correction
        ec_layout = QHBoxLayout()
        ec_layout.addWidget(QLabel("Error Correction:"))
        self.error_correction = QComboBox()
        self.error_correction.addItems([
            ("L", "Low (~7% recovery)"),
            ("M", "Medium (~15% recovery)"),
            ("Q", "Quaternary (~25% recovery)"),
            ("H", "High (~30% recovery)")
        ])
        self.error_correction.setCurrentIndex(3)  # Default to High
        ec_layout.addWidget(self.error_correction)
        input_layout.addLayout(ec_layout)
        
        # QR Code version/size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("QR Version (1-40):"))
        self.qr_version_spin = QSpinBox()
        self.qr_version_spin.setRange(1, 40)
        self.qr_version_spin.setValue(7)
        size_layout.addWidget(self.qr_version_spin)
        input_layout.addLayout(size_layout)
        
        input_group.setLayout(input_layout)
        left_panel.addWidget(input_group)
        
        # Background Image Group
        bg_group = QGroupBox("Background Image")
        bg_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        self.btn_load_image = QPushButton("Load Image")
        self.btn_load_image.clicked.connect(self.load_background_image)
        btn_layout.addWidget(self.btn_load_image)
        
        self.btn_use_cat = QPushButton("Use Sample Cat")
        self.btn_use_cat.clicked.connect(self.use_sample_cat)
        btn_layout.addWidget(self.btn_use_cat)
        bg_layout.addLayout(btn_layout)
        
        self.bg_label = QLabel()
        self.bg_label.setFixedSize(150, 150)
        self.bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bg_label.setStyleSheet("border: 2px solid gray;")
        bg_layout.addWidget(self.bg_label)
        
        # Background threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Mask Threshold:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setValue(50)
        self.threshold_spin.setSuffix(" %")
        threshold_layout.addWidget(self.threshold_spin)
        bg_layout.addLayout(threshold_layout)
        
        # Mode selection
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup()
        self.mode_over = QRadioButton("QR Over Image")
        self.mode_under = QRadioButton("Image Over QR")
        self.mode_over.setChecked(True)
        self.mode_group.addButton(self.mode_over)
        self.mode_group.addButton(self.mode_under)
        mode_layout.addWidget(QLabel("Mode:"))
        mode_layout.addWidget(self.mode_over)
        mode_layout.addWidget(self.mode_under)
        bg_layout.addLayout(mode_layout)
        
        bg_group.setLayout(bg_layout)
        left_panel.addWidget(bg_group)
        
        # Generate button
        self.btn_generate = QPushButton("Generate QR Code")
        self.btn_generate.clicked.connect(self.generate_qr_code)
        self.btn_generate.setStyleSheet(
            "font-size: 16px; padding: 10px; background-color: #4CAF50; color: white;"
        )
        left_panel.addWidget(self.btn_generate)
        
        # Save button
        self.btn_save = QPushButton("Save Result")
        self.btn_save.clicked.connect(self.save_result)
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet(
            "font-size: 14px; padding: 8px; background-color: #2196F3; color: white;"
        )
        left_panel.addWidget(self.btn_save)
        
        left_panel.addStretch()
        main_layout.addLayout(left_panel, 1)
        
        # Right panel - Preview
        right_panel = QVBoxLayout()
        self.preview_label = QLabel("Preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(
            "border: 2px solid gray; background-color: white; min-width: 400px; min-height: 400px;"
        )
        right_panel.addWidget(self.preview_label, stretch=1)
        main_layout.addLayout(right_panel, 2)
        
        central_widget.setLayout(main_layout)
    
    def load_background_image(self):
        """
        Load a background image from file dialog.
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        
        if filepath:
            try:
                self.bg_image = Image.open(filepath)
                self.bg_image = self.bg_image.convert('RGB')
                
                # Show preview
                pixmap = self.image_to_pixmap(self.bg_image)
                scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
                self.bg_label.setPixmap(scaled_pixmap)
                
                QMessageBox.information(self, "Success", f"Image loaded: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {e}")
    
    def use_sample_cat(self):
        """
        Use a sample cat image (placeholder - generates a simple cat-like shape).
        """
        # Generate a simple placeholder image
        img = Image.new('RGB', (200, 200), (255, 255, 255))
        pixels = img.load()
        
        # Draw a cute cat-like shape
        center_x, center_y = 100, 80
        ear_size = 20
        head_radius = 40
        
        import math
        for y in range(200):
            for x in range(200):
                dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                if dist < head_radius:
                    pixels[x, y] = (218, 165, 32)  # Orange cat color
        
        # Ears
        for angle in range(0, 70):
            rad = math.radians(angle - 35)
            ex = center_x + int(head_radius * math.cos(rad))
            ey = center_y + int(head_radius * math.sin(rad))
            pixels[ex, ey] = (218, 165, 32)
        
        self.bg_image = img
        pixmap = self.image_to_pixmap(img)
        scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
        self.bg_label.setPixmap(scaled_pixmap)
    
    def image_to_pixmap(self, image: Image.Image) -> QPixmap:
        """
        Convert PIL Image to QPixmap.
        """
        if image.mode == 'RGBA':
            rgba_image = np.array(image)
            bytes_per_line = 4 * rgba_image.shape[1]
            buf = rgba_image.tobytes()
            format_str = "RGB32"
        else:
            rgb_image = image.convert('RGB')
            rgb_array = np.array(rgb_image)
            rgba_array = np.zeros((rgb_array.shape[0], rgb_array.shape[1], 4), dtype=np.uint8)
            rgba_array[:, :, :3] = rgb_array
            rgba_array[:, :, 3] = 255
            bytes_per_line = 4 * rgba_array.shape[1]
            buf = rgba_array.tobytes()
            format_str = "RGB32"
        
        qimage = QImage(buf, image.width, image.height, bytes_per_line, format_str)
        return QPixmap.fromImage(qimage)
    
    def generate_qr_code(self):
        """
        Generate the QR code with steganography effects.
        """
        # Get input data
        url_text = self.url_input.text().strip()
        if not url_text:
            QMessageBox.warning(self, "Warning", "Please enter URL or content for the QR code")
            return
        
        error_correction = self.error_correction.currentText()[0]
        qr_version = self.qr_version_spin.value()
        
        # Generate base QR code
        try:
            qr_image = self.processor.generate_qr_code(url_text, qr_version, error_correction)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate QR code: {e}")
            return
        
        # Check if background image is loaded
        if not hasattr(self, 'bg_image') or self.bg_image is None:
            QMessageBox.warning(
                self,
                "Warning",
                "No background image loaded. Generate a plain QR code?"
            )
            reply = QMessageBox.question(
                self,
                "Confirm",
                "Generate plain QR code without background?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Apply steganography mode
        if hasattr(self, 'bg_image') and self.bg_image is not None:
            threshold = self.threshold_spin.value() / 100.0
            
            if self.mode_over.isChecked():
                # QR code OVER background (invisibility cloak style)
                result = self.processor.qr_over_image(qr_image, self.bg_image)
            else:
                # Background image OVER QR code (tinted modules)
                result = self.processor.image_over_qr_with_tinting(qr_image, self.bg_image)
        else:
            result = qr_image.convert('RGB')
        
        self.current_result = result
        
        # Update preview
        pixmap = self.image_to_pixmap(result)
        scaled_pixmap = pixmap.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio)
        self.preview_label.setPixmap(scaled_pixmap)
        self.preview_label.setStyleSheet(
            "border: 2px solid green; background-color: white; min-width: 400px; min-height: 400px;"
        )
        
        # Enable save button
        self.btn_save.setEnabled(True)
    
    def save_result(self):
        """
        Save the generated QR code image.
        """
        if self.current_result is None:
            return
            
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save QR Code Image",
            "qr_code.png",
            "PNG (*.png);;JPEG (*.jpg)"
        )
        
        if filepath:
            try:
                self.processor.save_image(self.current_result, filepath)
                QMessageBox.information(self, "Success", f"Image saved to: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save image: {e}")


def main():
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
