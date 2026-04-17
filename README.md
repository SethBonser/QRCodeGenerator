# QR Code Steganography Generator

A PyQt6 application that creates QR codes hidden within images, making them less conspicuous while remaining scannable.

## Features

- **Two Operation Modes**:
  - **QR Over Image**: The QR code is placed over the background image. White modules become transparent, revealing the background underneath (like an "invisibility cloak")
  - **Image Over QR**: The background image overlays the QR code, with black modules tinted to match colors from the underlying image

- **High Error Correction**: Uses Maximum error correction level (H), allowing ~30% of the QR code to be obscured while still being scannable

- **Customizable Settings**:
  - URL/Content for QR code
  - Error correction level (L, M, Q, H)
  - QR code version/size (1-40)
  - Mask threshold for image processing

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

Required packages:
- `qrcode[art]` - QR code generation
- `Pillow` - Image processing
- `PyQt6` - GUI framework
- `numpy` - Array operations for image manipulation

## Usage

```bash
python qr_steganography.py
```

### Interface Guide:

1. **Input Settings**
   - Enter the URL or text content for your QR code
   - Select error correction level (recommended: High)
   - Choose QR version (higher = larger QR code, more data capacity)

2. **Background Image**
   - Click "Load Image" to select an image file
   - Or click "Use Sample Cat" for a demo image
   - Adjust the mask threshold to control visibility

3. **Mode Selection**
   - **QR Over Image**: QR code visible, background shows through white areas
   - **Image Over QR**: Background mostly visible, QR modules tinted to blend in

4. Click "Generate QR Code" to create the result
5. Click "Save Result" to save as PNG file

## Tips for Best Results

### For Scannability:
- Use **High error correction** (Level H)
- Ensure **high contrast** between black and white modules
- Don't obscure more than ~30% of the QR code area
- Keep alignment patterns visible if possible

### Image Selection:
- Choose images with good color variation for tinting mode
- Simpler, less detailed images work better for overlay modes
- Consider using illustrations or solid-color backgrounds

### Testing:
Always test your generated QR code with multiple scanning apps before distribution.

## Technical Details

The application uses two main techniques:

1. **Transparency Masking**: Converts white QR modules to transparent pixels, allowing the background image to show through

2. **Color Tinting**: Reduces brightness of black QR modules and tints them with colors from the overlay image, maintaining contrast while blending visually

## Example Output

```
[QR Code Module]  [White = Transparent]  
   ████    █████     Background shows through white areas
  ██  ██  ██  ██
   ████    █████
```

Or with color tinting:
```
[Tinted Black Modules]
   ████    █████  (modules tinted to match background colors)
  ██  ██  ██  ██
   ████    █████
```
