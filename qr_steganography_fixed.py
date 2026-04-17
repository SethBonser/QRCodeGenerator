"""
QR Code Steganography Generator

Creates QR codes that can be hidden within or overlaid on images,
making the QR code less conspicuous while remaining scannable.
"""

import sys
import re
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H
from PIL import Image
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QLineEdit, QSpinBox, QComboBox, QGroupBox,
    QRadioButton, QButtonGroup, QMessageBox, QApplication, QSlider, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
import io
import numpy as np


class PreviewWidget(QLabel):
    """
    Custom QLabel that handles mouse events for interactive preview.
    Emits signals when user drags or zooms the background image.
    """
    
    # Signals emitted to parent window
    position_changed = pyqtSignal(int, int)  # x_offset_delta, y_offset_delta
    scale_changed = pyqtSignal(float)        # scale_factor_multiplier
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "border: 2px solid gray; background-color: white; min-width: 400px; min-height: 400px;"
        )
        self.setMouseTracking(True)  # Enable mouse tracking
        self.dragging = False
        self.drag_start_pos = None
        self.interactive_mode = False
    
    def set_interactive_mode(self, enabled):
        """Enable/disable interactive drag/zoom mode."""
        self.interactive_mode = enabled
        if enabled:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.setToolTip("Drag to reposition, Wheel to zoom")
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setToolTip("")
    
    def mousePressEvent(self, event):
        """Handle mouse press - start dragging."""
        if not self.interactive_mode or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        
        self.dragging = True
        self.drag_start_pos = event.position()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)  # Show grabbing cursor
    
    def mouseMoveEvent(self, event):
        """Handle mouse move - update position while dragging."""
        if not self.dragging:
            super().mouseMoveEvent(event)
            return
        
        # Calculate delta from drag start
        current_pos = event.position()
        delta_x = int(current_pos.x() - self.drag_start_pos.x())
        delta_y = int(current_pos.y() - self.drag_start_pos.y())
        
        if delta_x != 0 or delta_y != 0:
            # Emit position changed signal
            self.position_changed.emit(delta_x, delta_y)
            # Reset drag start to current position for continuous dragging
            self.drag_start_pos = current_pos
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - stop dragging."""
        if self.dragging:
            self.dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)  # Restore open hand cursor
        super().mouseReleaseEvent(event)
    
    def wheelEvent(self, event):
        """Handle mouse wheel - zoom in/out."""
        if not self.interactive_mode:
            super().wheelEvent(event)
            return
        
        # Determine scroll direction and emit scale change
        delta = event.angleDelta().y()
        if delta > 0:  # Scroll up - zoom in (increase scale)
            self.scale_changed.emit(1.1)  # Scale factor to multiply by
        else:  # Scroll down - zoom out (decrease scale)
            self.scale_changed.emit(0.9)  # Scale factor to multiply by


class QRCodeProcessor:
    """
    Handles all QR code generation and image processing operations.
    """
    
    def __init__(self):
        self.qr_code = None
        self.qr_image = None
        
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
            box_size=10,
            border=4
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
        gray = image.convert('L')
        threshold_value = int(255 * threshold)
        
        mask_array = np.array(gray)
        mask_array[mask_array > threshold_value] = 255
        mask_array[mask_array <= threshold_value] = 0
        
        return Image.fromarray(mask_array, mode='L')
    
    def qr_over_image(self, qr_image: Image.Image, bg_image: Image.Image, 
                      resize_qr_to_bg: bool = True,
                      fade_factor: float = 0.15,
                      tint_intensity: float = 0.20,
                      bg_scale: float = 1.0,
                      bg_x_offset: int = 0,
                      bg_y_offset: int = 0) -> Image.Image:
        """
        Place QR code OVER the background image with smart blending.
        
        IMPROVED APPROACH for maximum scannability:
        - Background is FADED (fade_factor visibility) - subtle watermark
        - Black QR modules are SOLID dark colors tinted toward background  
        - White QR modules remain WHITE or very light
        
        This creates HIGH contrast while still visually integrating with the image.
        Result size matches QR code size to prevent any cropping.
        
        Args:
            qr_image: The QR code PIL Image
            bg_image: Background image to blend with
            resize_qr_to_bg: Whether to resize QR to match background width
            fade_factor: Background visibility (0.0 = invisible, 1.0 = full opacity)
        """
        bg_width, bg_height = bg_image.size
        qr_width, qr_height = qr_image.size
        
        # Resize QR to match background if requested
        if resize_qr_to_bg:
            qr_size = bg_width
            qr_image = self.resize_qr_to_background(qr_size)
            qr_width, qr_height = qr_image.size
        else:
            # Apply scale factor to background (for interactive zoom)
            scaled_w = int(bg_width * bg_scale)
            scaled_h = int(bg_height * bg_scale)
            if scaled_w > 0 and scaled_h > 0:
                bg_image = bg_image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            bg_width, bg_height = scaled_w, scaled_h
        
        # Convert images to numpy arrays
        bg_array = np.array(bg_image.convert('RGB')).astype(np.float32)
        qr_gray_array = np.array(qr_image.convert('L'))
        
        # Create result array with SAME SIZE as QR code (prevents cropping!)
        # fade_factor is now passed as parameter - allows user to adjust via UI
        result_array = np.ones((qr_height, qr_width, 3), dtype=np.float32) * 255
        
        # Calculate offset for placing background on QR (for interactive positioning)
        # Center the scaled background, then apply user offsets
        x_offset = max(0, (qr_width - bg_width) // 2 + bg_x_offset)
        y_offset = max(0, (qr_height - bg_height) // 2 + bg_y_offset)
        
        # Process WHITE modules: show faded background
        white_mask = qr_gray_array > 127
        if white_mask.any():
            for y in range(qr_height):
                for x in range(qr_width):
                    if white_mask[y, x]:
                        bg_x = x_offset + x
                        bg_y = y_offset + y
                        # Check bounds - if outside background, keep white
                        if 0 <= bg_x < bg_width and 0 <= bg_y < bg_height:
                            bg_color = bg_array[bg_y, bg_x]
                            # Blend: mostly white with hint of faded background
                            result_array[y, x] = bg_color * fade_factor + \
                                                  np.array([255.0, 255.0, 255.0]) * (1.0 - fade_factor)
        
        # Process BLACK modules: solid dark color tinted toward background
        black_mask = qr_gray_array <= 127
        if black_mask.any():
            for y in range(qr_height):
                for x in range(qr_width):
                    if black_mask[y, x]:
                        bg_x = x_offset + x
                        bg_y = y_offset + y
                        # Check bounds - if outside background, use pure black
                        if 0 <= bg_x < bg_width and 0 <= bg_y < bg_height:
                            bg_color = bg_array[bg_y, bg_x]
                            # Blend: mostly black with adjustable tint intensity
                            black_portion = 1.0 - tint_intensity
                            qr_color = np.array([0, 0, 0], dtype=np.float32) * black_portion + \
                                       bg_color * tint_intensity
                            result_array[y, x] = qr_color
                        else:
                            # Outside background area - use pure black
                            result_array[y, x] = np.array([0, 0, 0], dtype=np.float32)
        
        # Convert to uint8 and create image
        result_array = np.clip(result_array, 0, 255).astype(np.uint8)
        return Image.fromarray(result_array, mode='RGB')
    
    def image_over_qr_with_tinting(self, qr_image: Image.Image, bg_image: Image.Image,
                                   resize_bg_to_qr: bool = True,
                                   fade_factor: float = 0.15,
                                   tint_intensity: float = 0.20,
                                   bg_scale: float = 1.0,
                                   bg_x_offset: int = 0,
                                   bg_y_offset: int = 0) -> Image.Image:
        """
        Place background image OVER the QR code with smart tinting.
        
        IMPROVED APPROACH for maximum scannability:
        - White QR modules show FADED background (fade_factor visibility)
        - Black QR modules are SOLID dark colors tinted toward background
        
        This maintains HIGH contrast while visually integrating with the image.
        Result size matches QR code size to prevent any cropping.
        
        Args:
            qr_image: The QR code PIL Image
            bg_image: Background image to blend with
            resize_bg_to_qr: Whether to resize background to match QR width
            fade_factor: Background visibility (0.0 = invisible, 1.0 = full opacity)
        """
        qr_width, qr_height = qr_image.size
        bg_width, bg_height = bg_image.size
        
        # Resize background to match QR size with scale factor
        if resize_bg_to_qr:
            scaled_w = int(bg_width * bg_scale)
            scaled_h = int(bg_height * bg_scale)
            if scaled_w > 0 and scaled_h > 0:
                bg_image = bg_image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            bg_width, bg_height = scaled_w, scaled_h
        
        # Calculate offset for placing background on QR (for interactive positioning)
        # Center the scaled background, then apply user offsets
        x_offset = max(0, (qr_width - bg_width) // 2 + bg_x_offset)
        y_offset = max(0, (qr_height - bg_height) // 2 + bg_y_offset)
        
        # Convert images to numpy arrays
        qr_gray_array = np.array(qr_image.convert('L'))
        bg_array = np.array(bg_image.convert('RGB')).astype(np.float32)
        
        # Create result array with SAME SIZE as QR code (prevents cropping!)
        # fade_factor is now passed as parameter - allows user to adjust via UI
        result_array = np.ones((qr_height, qr_width, 3), dtype=np.float32) * 255
        
        # Process WHITE modules: show faded background
        white_mask = qr_gray_array > 127
        if white_mask.any():
            for y in range(qr_height):
                for x in range(qr_width):
                    if white_mask[y, x]:
                        bg_x = x_offset + x
                        bg_y = y_offset + y
                        # Check bounds - if outside background, keep white
                        if 0 <= bg_x < bg_width and 0 <= bg_y < bg_height:
                            bg_color = bg_array[bg_y, bg_x]
                            # Blend: mostly white with hint of faded background
                            result_array[y, x] = bg_color * fade_factor + \
                                                  np.array([255.0, 255.0, 255.0]) * (1.0 - fade_factor)
        
        # Process BLACK modules: solid dark color tinted toward background
        black_mask = qr_gray_array <= 127
        if black_mask.any():
            for y in range(qr_height):
                for x in range(qr_width):
                    if black_mask[y, x]:
                        bg_x = x_offset + x
                        bg_y = y_offset + y
                        # Check bounds - if outside background, use pure black
                        if 0 <= bg_x < bg_width and 0 <= bg_y < bg_height:
                            bg_color = bg_array[bg_y, bg_x]
                            # Blend: mostly black with adjustable tint intensity
                            black_portion = 1.0 - tint_intensity
                            qr_color = np.array([0, 0, 0], dtype=np.float32) * black_portion + \
                                       bg_color * tint_intensity
                            result_array[y, x] = qr_color
                        else:
                            # Outside background area - use pure black
                            result_array[y, x] = np.array([0, 0, 0], dtype=np.float32)
        
        # Convert to uint8 and create image
        result_array = np.clip(result_array, 0, 255).astype(np.uint8)
        return Image.fromarray(result_array, mode='RGB')
    
    def save_image(self, image: Image.Image, filepath):
        """
        Save the generated image to file or buffer.
        
        Args:
            image: PIL Image to save
            filepath: File path string or BytesIO buffer
        """
        if isinstance(filepath, io.BytesIO):
            # Saving to buffer - specify format explicitly
            if image.mode == 'RGBA':
                image.save(filepath, 'PNG')
            else:
                image.save(filepath, 'JPEG' if image.mode == 'RGB' else 'PNG')
        elif image.mode == 'RGBA':
            filepath_str = str(filepath)
            if not filepath_str.lower().endswith('.png'):
                filepath_str += '.png'
            image.save(filepath_str, 'PNG')
        else:
            filepath_str = str(filepath)
            if filepath_str.lower().endswith(('.jpg', '.jpeg')):
                image.convert('RGB').save(filepath_str, 'JPEG')
            elif filepath_str.lower().endswith('.png'):
                image.save(filepath_str, 'PNG')
            else:
                image.save(filepath_str)


class MainWindow(QMainWindow):
    """
    Main GUI window for QR Code Steganography Generator.
    """
    
    def __init__(self):
        super().__init__()
        self.processor = QRCodeProcessor()
        self.current_result = None
        self.bg_image = None  # Initialize background image to None
        self.background_opacity = 0.15  # Default: 15% visible (85% white)
        self.tint_intensity = 0.20  # Default: 20% tint on black modules
        self.bg_scale_factor = 1.0   # Background zoom level (1.0 = original size)
        self.bg_x_offset = 0          # Horizontal position offset
        self.bg_y_offset = 0          # Vertical position offset
        self.interactive_preview = False  # Enable interactive drag/zoom in preview
        self.preview_widget = None  # Custom PreviewWidget instance
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
            "L - Low (~7% recovery)",
            "M - Medium (~15% recovery)",
            "Q - Quaternary (~25% recovery)",
            "H - High (~30% recovery)"
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
        
        # Background opacity slider
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Background Opacity:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 75)  # 0-75% (max 75% to keep QR visible)
        self.opacity_slider.setValue(15)  # Default: 15%
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_slider.setTickInterval(10)
        opacity_layout.addWidget(self.opacity_slider, stretch=1)
        
        self.opacity_label = QLabel("15%")
        self.opacity_label.setMinimumWidth(40)
        opacity_layout.addWidget(self.opacity_label)
        
        # Connect slider to update label and internal value
        self.opacity_slider.valueChanged.connect(
            lambda v: setattr(self, 'background_opacity', v / 100.0)
        )
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )
        
        # Apply style to the slider widget directly
        self.opacity_slider.setStyleSheet("QSlider::groove { height: 4px; background: #ddd; }")
        bg_layout.addLayout(opacity_layout)
        
        # Tint intensity slider - controls how much background color tints black modules
        tint_layout = QHBoxLayout()
        tint_layout.addWidget(QLabel("Tint Intensity:"))
        self.tint_slider = QSlider(Qt.Orientation.Horizontal)
        self.tint_slider.setRange(0, 75)  # 0-75% tint intensity
        self.tint_slider.setValue(20)  # Default: 20%
        self.tint_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.tint_slider.setTickInterval(10)
        tint_layout.addWidget(self.tint_slider, stretch=1)
        
        self.tint_label = QLabel("20%")
        self.tint_label.setMinimumWidth(40)
        tint_layout.addWidget(self.tint_label)
        
        # Connect slider to update label and internal value
        self.tint_slider.valueChanged.connect(
            lambda v: setattr(self, 'tint_intensity', v / 100.0)
        )
        self.tint_slider.valueChanged.connect(
            lambda v: self.tint_label.setText(f"{v}%")
        )
        
        # Apply style to the slider widget directly
        self.tint_slider.setStyleSheet("QSlider::groove { height: 4px; background: #ddd; }")
        bg_layout.addLayout(tint_layout)
        
        # Output filename field
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel("Output Filename:"))
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("Auto-generate from URL or custom name")
        filename_layout.addWidget(self.filename_input, stretch=1)
        bg_layout.addLayout(filename_layout)
        
        # Background threshold (kept for compatibility, but opacity is primary control now)
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
        
        # Interactive Preview checkbox
        interactive_checkbox = QCheckBox("Interactive Preview (Drag to Position, Wheel to Zoom)")
        interactive_checkbox.setChecked(False)
        interactive_checkbox.toggled.connect(self.toggle_interactive_preview)
        bg_layout.addWidget(interactive_checkbox)
        
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
        self.preview_widget = PreviewWidget()
        
        # Connect signals from preview widget to handlers
        self.preview_widget.position_changed.connect(self.on_preview_position_changed)
        self.preview_widget.scale_changed.connect(self.on_preview_scale_changed)
        
        right_panel.addWidget(self.preview_widget, stretch=1)
        main_layout.addLayout(right_panel, 2)
        
        central_widget.setLayout(main_layout)
    
    def toggle_interactive_preview(self, checked):
        """
        Enable/disable interactive preview mode.
        When enabled, user can drag to reposition and scroll wheel to zoom background.
        """
        self.interactive_preview = checked
        # Update cursor on preview widget
        if self.preview_widget:
            self.preview_widget.set_interactive_mode(checked)
    
    def on_preview_position_changed(self, delta_x, delta_y):
        """
        Signal handler: Update position when user drags in preview.
        Called by PreviewWidget.position_changed signal.
        """
        self.bg_x_offset += delta_x
        self.bg_y_offset += delta_y
        self.update_preview_with_positioning()
    
    def on_preview_scale_changed(self, scale_multiplier):
        """
        Signal handler: Update scale when user scrolls wheel in preview.
        Called by PreviewWidget.scale_changed signal.
        """
        self.bg_scale_factor *= scale_multiplier
        # Clamp to valid range
        self.bg_scale_factor = max(0.3, min(2.0, self.bg_scale_factor))
        self.update_preview_with_positioning()
    
    def update_preview_with_positioning(self):
        """
        Update the preview with current positioning settings.
        Called after drag or zoom operations.
        """
        if not hasattr(self, 'current_qr_image') or self.bg_image is None:
            return
        
        # Get current mode and regenerate with positioning
        fade_factor = self.background_opacity
        tint_intensity = self.tint_intensity
        
        if self.mode_over.isChecked():
            result = self.processor.qr_over_image(
                self.current_qr_image, self.bg_image,
                resize_qr_to_bg=False,  # Don't auto-resize - we handle positioning
                fade_factor=fade_factor,
                tint_intensity=tint_intensity,
                bg_scale=self.bg_scale_factor,
                bg_x_offset=self.bg_x_offset,
                bg_y_offset=self.bg_y_offset
            )
        else:
            result = self.processor.image_over_qr_with_tinting(
                self.current_qr_image, self.bg_image,
                resize_bg_to_qr=False,  # Don't auto-resize - we handle positioning
                fade_factor=fade_factor,
                tint_intensity=tint_intensity,
                bg_scale=self.bg_scale_factor,
                bg_x_offset=self.bg_x_offset,
                bg_y_offset=self.bg_y_offset
            )
        
        self.current_result = result
        pixmap = self.image_to_pixmap(result)
        scaled_pixmap = pixmap.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio)
        if self.preview_widget:
            self.preview_widget.setPixmap(scaled_pixmap)
    
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
        head_radius = 40
        
        import math
        for y in range(200):
            for x in range(200):
                dist = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                if dist < head_radius:
                    pixels[x, y] = (218, 165, 32)  # Orange cat color
        
        self.bg_image = img
        pixmap = self.image_to_pixmap(img)
        scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
        self.bg_label.setPixmap(scaled_pixmap)
    
    def image_to_pixmap(self, image: Image.Image) -> QPixmap:
        """
        Convert PIL Image to QPixmap.
        Uses PyQt6's QImage.Format enum for proper format specification.
        """
        # Always convert to RGBA for consistent handling
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Get image dimensions
        width, height = image.size
        
        # Convert to numpy array and get bytes
        rgba_array = np.array(image)
        buf = rgba_array.tobytes()
        bytes_per_line = 4 * width  # 4 bytes per pixel (RGBA)
        
        # Use QImage.Format enum - Format_RGBA8888 for 32-bit RGBA
        qimage = QImage(buf, width, height, bytes_per_line, QImage.Format.Format_RGBA8888)
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
        
        # Extract error correction level from display text (e.g., "H - High..." -> "H")
        ec_text = self.error_correction.currentText()
        error_correction = ec_text.split(' ')[0] if ec_text else 'H'
        qr_version = self.qr_version_spin.value()
        
        # Generate base QR code
        try:
            qr_image = self.processor.generate_qr_code(url_text, qr_version, error_correction)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate QR code: {e}")
            return
        
        # Check if background image is loaded
        if self.bg_image is None:
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
        if self.bg_image is not None:
            threshold = self.threshold_spin.value() / 100.0
            fade_factor = self.background_opacity  # Use slider value (from opacity_slider)
            tint_intensity = self.tint_intensity   # Use slider value (from tint_slider)
            
            if self.mode_over.isChecked():
                # QR code OVER background (invisibility cloak style)
                result = self.processor.qr_over_image(
                    qr_image, self.bg_image,
                    resize_qr_to_bg=True,  # Auto-resize for final output
                    fade_factor=fade_factor,
                    tint_intensity=tint_intensity,
                    bg_scale=self.bg_scale_factor,
                    bg_x_offset=self.bg_x_offset,
                    bg_y_offset=self.bg_y_offset
                )
            else:
                # Background image OVER QR code (tinted modules)
                result = self.processor.image_over_qr_with_tinting(
                    qr_image, self.bg_image,
                    resize_bg_to_qr=True,  # Auto-resize for final output
                    fade_factor=fade_factor,
                    tint_intensity=tint_intensity,
                    bg_scale=self.bg_scale_factor,
                    bg_x_offset=self.bg_x_offset,
                    bg_y_offset=self.bg_y_offset
                )
        else:
            result = qr_image.convert('RGB')
        
        self.current_result = result
        self.current_qr_image = qr_image  # Store for interactive preview
        # Get input data
        url_text = self.url_input.text().strip()
        if not url_text:
            QMessageBox.warning(self, "Warning", "Please enter URL or content for the QR code")
            return
        
        # Extract error correction level from display text (e.g., "H - High..." -> "H")
        ec_text = self.error_correction.currentText()
        error_correction = ec_text.split(' ')[0] if ec_text else 'H'
        qr_version = self.qr_version_spin.value()
        
        # Generate base QR code
        try:
            qr_image = self.processor.generate_qr_code(url_text, qr_version, error_correction)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate QR code: {e}")
            return
        
        # Check if background image is loaded
        if self.bg_image is None:
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
        if self.bg_image is not None:
            threshold = self.threshold_spin.value() / 100.0
            fade_factor = self.background_opacity  # Use slider value (from opacity_slider)
            
            if self.mode_over.isChecked():
                # QR code OVER background (invisibility cloak style)
                result = self.processor.qr_over_image(qr_image, self.bg_image, fade_factor=fade_factor)
            else:
                # Background image OVER QR code (tinted modules)
                result = self.processor.image_over_qr_with_tinting(qr_image, self.bg_image, fade_factor=fade_factor)
        else:
            result = qr_image.convert('RGB')
        
        self.current_result = result
        
        # Update preview
        pixmap = self.image_to_pixmap(result)
        scaled_pixmap = pixmap.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio)
        if self.preview_widget:
            self.preview_widget.setPixmap(scaled_pixmap)
            self.preview_widget.setStyleSheet(
                "border: 2px solid green; background-color: white; min-width: 400px; min-height: 400px;"
            )
        
        # Enable save button
        self.btn_save.setEnabled(True)
    
    def save_result(self):
        """
        Save the generated QR code image.
        Auto-generates filename from URL domain or uses custom name.
        """
        if self.current_result is None:
            return
            
        # Get filename - use custom input or auto-generate from URL
        custom_filename = self.filename_input.text().strip()
        url_text = self.url_input.text().strip()
        
        if custom_filename:
            # Use custom filename if provided
            base_name = custom_filename
        elif url_text.startswith(('http://', 'https://')):
            # Extract domain from URL for auto-generated name
            try:
                match = re.search(r'^(?:https?://)?([^/]+)', url_text)
                if match:
                    domain = match.group(1).replace('.', '_').replace('www_', '')
                    base_name = f"{domain}_qrcode"
                else:
                    base_name = "qrcode"
            except:
                base_name = "qrcode"
        else:
            # For non-URL content, use first 20 chars
            base_name = url_text[:20].replace('/', '_').replace('\\', '_')
            if not base_name:
                base_name = "qrcode"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save QR Code Image",
            f"{base_name}.png",
            "PNG (*.png);;JPEG (*.jpg)"
        )
        
        if filepath:
            try:
                self.processor.save_image(self.current_result, filepath)
                QMessageBox.information(self, "Success", f"Image saved to: {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save image: {e}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
