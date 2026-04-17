# QR Code Steganography Generator

A PyQt6 desktop application that creates QR codes blended with background images, making them less conspicuous while remaining scannable. Perfect for embedding URLs in marketing materials, artwork, or any visual content where a plain QR code would be intrusive.

---

## Features

### Core Functionality
- **Two Blending Modes**:
  - **QR Over Image**: QR code is the primary layer; white modules show faded background, black modules are tinted toward background colors
  - **Image Over QR**: Background image overlays the QR code with smart color blending for maximum scannability

- **High Error Correction**: Supports all levels (L/M/Q/H), with H (~30% recovery) recommended for best results

- **Smart Blending Algorithm**:
  - White QR modules: Show faded background at configurable opacity
  - Black QR modules: Solid dark colors tinted toward background hues
  - Maintains high contrast for reliable scanning

### Advanced Features
- **Interactive Preview**: Drag to reposition, scroll wheel to zoom the background image in real-time
- **Background Opacity Slider** (0-75%): Control how visible the background is through white QR modules
- **Tint Intensity Slider** (0-75%): Adjust how much background color tints black QR modules
- **Smart Filename Generation**: Auto-generates filenames from URL domains (e.g., `google_com_qrcode.png`)
- **Background Stretching**: Automatically scales background to fill QR code area without empty space

### User Interface
- Clean two-panel layout: Controls on left, live preview on right
- Real-time preview updates as settings change
- Support for PNG, JPG, JPEG, BMP image formats
- Export to PNG or JPEG format

---

## Installation

### Prerequisites
- Python 3.8 or higher (tested with 3.11.9)
- Windows 10/11 (PyQt6 GUI framework)

### Install Dependencies
```bash
pip install -r requirements.txt
```

**Required packages:**
| Package | Purpose |
|---------|----------|
| `qrcode[pil]` | QR code generation with PIL backend |
| `Pillow` | Image processing and manipulation |
| `PyQt6` | Desktop GUI framework |
| `numpy` | Array operations for image blending |

---

## Usage

### Running the Application

**Development (Source Code):**
```bash
python qr_steganography_fixed_v2.py
```

**Compiled Executable:**
```bash
# Build once, then run anytime without Python installed
pyinstaller --name QRCodeSteganography --windowed --onedir qr_steganography_fixed_v2.py --collect-all PyQt6
.\\dist\\QRCodeSteganography\\QRCodeSteganography.exe
```

### Interface Guide

#### 1. Input Settings Panel
- **URL or Content**: Enter text, URL, or any data for the QR code
- **Error Correction**: Select level (L/M/Q/H) - H recommended for steganography
- **QR Version** (1-40): Controls size; higher = larger QR code with more capacity

#### 2. Background Image Panel
- **Load Image**: Browse and select an image file from your computer
- **Use Sample Cat**: Quick test with built-in placeholder image
- **Background Opacity Slider**: Adjust visibility of background in white modules (0-75%)
- **Tint Intensity Slider**: Control color tinting on black modules (0-75%)
- **Mode Selection**:
  - ○ QR Over Image - QR code is primary, background visible through white areas
  - ○ Image Over QR - Background overlays QR with tinted modules
- **Interactive Preview Checkbox**: Enable drag/zoom positioning in preview
- **Output Filename**: Custom name or auto-generated from URL

#### 3. Action Buttons
- **Generate QR Code**: Create the blended QR code image
- **Save Result**: Export to PNG or JPEG file

### Interactive Preview (When Enabled)

Once you generate a QR code with a background loaded and enable "Interactive Preview":

| Action | Effect |
|--------|--------|
| **Click + Drag** on preview | Reposition background image horizontally/vertically |
| **Scroll Wheel** up/down | Zoom in/out (range: 0.1x to 5.0x) |

The positioning is anchored to the original image dimensions, so zooming doesn't cause the background to "jump" to a new position.

---

## Tips for Best Results

### For Maximum Scannability

**Error Correction:**
- Always use **High (H)** level - allows ~30% of QR code to be obscured
- Use Quaternary (Q) only if you need more data capacity and can tolerate less obscuration

**Background Selection:**
- Choose images with moderate contrast - avoid extremely dark or light backgrounds
- Simpler, less detailed images work better for overlay modes
- Consider using illustrations, logos, or solid-color backgrounds
- Avoid busy patterns that might interfere with QR module detection

**Blending Settings:**
| Setting | Low Value | High Value | Recommendation |
|---------|-----------|-------------|----------------|
| Background Opacity | Subtle watermark effect | More visible background | Start at 15%, adjust to taste |
| Tint Intensity | Pure black modules | Heavily tinted modules | Start at 20% for subtle blending |

**Positioning:**
- Use interactive preview to center important visual elements
- Ensure QR finder patterns (corner squares) remain visible
- Leave some white space around edges if possible

### Testing Your QR Code

Always test before distribution:
1. **Multiple Apps**: Test with at least 3 different QR scanner apps (iOS Camera, Android Camera, dedicated scanner apps)
2. **Different Distances**: Scan from various distances and angles
3. **Different Lighting**: Test in bright light, dim light, and mixed lighting conditions
4. **Printed Version**: If printing, test the actual printed output - screen preview may differ

---

## Technical Details

### Architecture
```
┌───────────────────┐      Signals         ┌───────────────────┐
│  PreviewWidget    │──position_changed──►│   MainWindow      │
│  (QLabel subclass)│──scale_changed─────►│                   │
└───────────────────┘◄──setPixmap────────┤  State & Logic    │
         ▲                                   └───────────────────┘
         │
     User Events
```

### Blending Algorithm

**QR Over Image Mode:**
```python
# White modules: Faded background visible
result = background_color * fade_factor + white * (1 - fade_factor)

# Black modules: Tinted toward background
result = black * (1 - tint_intensity) + background_color * tint_intensity
```

**Image Over QR Mode:**
- Same blending formula, but applied with different layer priorities
- Background is the primary visible layer
- QR code structure preserved through contrast maintenance

### Performance Characteristics
| Operation | Typical Time (400×400 image) |
|-----------|------------------------------|
| QR Code Generation | ~50ms |
| Image Blending | ~500ms |
| Interactive Preview Update | ~600ms |

*Note: Uses per-pixel processing for precise control; vectorization possible for optimization*

---

## Project Structure

```
QRCodeGenerator/
├── qr_steganography_fixed_v2.py   # Main application source
├── test_qr_steganography.py        # Test suite (18 tests)
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

### Key Classes
- **`QRCodeProcessor`**: Handles QR generation and image blending operations
  - `generate_qr_code()` - Create QR code from data
  - `qr_over_image()` - Blend QR over background
  - `image_over_qr_with_tinting()` - Blend background over QR
  
- **`PreviewWidget(QLabel)`**: Custom widget for interactive preview
  - Handles mouse drag events → emits `position_changed`
  - Handles wheel scroll events → emits `scale_changed`
  
- **`MainWindow(QMainWindow)`**: Main application window
  - Manages UI state and user interactions
  - Coordinates between processor and preview

---

## Testing

Run the test suite:
```bash
python -m unittest test_qr_steganography.py -v
```

**Test Coverage:**
- QR code generation with various data types
- Both blending modes (QR over image, Image over QR)
- Error correction levels
- Fade and tint parameter ranges
- Positioning and scaling operations
- Image format compatibility

---

## Known Limitations

| Area | Current State | Potential Improvement |
|------|---------------|----------------------|
| Performance | ~0.5s per regeneration (per-pixel loops) | Vectorize black module tinting like white modules |
| Zoom Range | 0.1x to 5.0x scale factor | Configurable range, snap-to-grid options |
| Positioning | Free-form drag (pixel-level) | Snap alignments, boundary constraints |
| Undo/Redo | Not implemented | State history for positioning changes |

---

## Troubleshooting

### Common Issues

**"No module named 'PyQt6'" when running .exe:**
- Rebuild with `--collect-all PyQt6` flag in pyinstaller command

**QR code won't scan after generation:**
- Increase error correction to High (H)
- Reduce background opacity or tint intensity
- Ensure finder patterns are visible
- Try the other blending mode

**Background not appearing in generated QR:**
- Verify image was loaded successfully (check thumbnail preview)
- Adjust background opacity slider higher
- Check that correct mode is selected

**Wheel zoom not working in interactive preview:**
- Ensure "Interactive Preview" checkbox is checked
- Hover mouse directly over the preview area
- Try scrolling more slowly - some mice have high sensitivity

---

## Build Instructions

### Create Standalone Executable

```powershell
# Clean previous builds (optional)
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# Build executable
pyinstaller --name QRCodeSteganography \
    --windowed \
    --onedir \
    qr_steganography_fixed_v2.py \
    --collect-all PyQt6 \
    --icon=app_icon.ico  # Optional: custom icon
```

**Output:** `dist/QRCodeSteganography/QRCodeSteganography.exe`

### Build Options Explained
- `--windowed`: No console window (GUI-only application)
- `--onedir`: Extract to folder with dependencies (easier debugging, larger size)
- `--collect-all PyQt6`: Include all PyQt6 plugins and resources

---

## License

MIT License - Free for personal and commercial use.

---

## Version History

**v2.0** (Current) - Complete rewrite with signal/slot architecture
- Fixed file corruption from multi-edit conflicts
- Interactive drag/zoom preview
- Background opacity and tint intensity sliders
- Smart filename generation from URLs
- Extended zoom range (0.1x to 5.0x)
- Stable positioning during zoom operations

**v1.0** - Initial release
- Basic QR over image / Image over QR modes
- Error correction selection
- PNG/JPEG export

---

## Contributing

Bug reports and feature suggestions welcome! Please include:
- Python version and OS
- Steps to reproduce the issue
- Sample images that trigger problems (if applicable)

For questions or feedback, open an issue on GitHub.
