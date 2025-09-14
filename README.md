# AGS Sprite Extractor

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance Python tool to extract individual sprites from AGS (Adventure Game Studio) `.spr` files. Perfect for game modding, asset extraction, and retro gaming preservation.

## 🎯 Why This Tool?

- **⚡ Ultra-fast**: Extract 250+ sprites per second
- **🔧 Complete**: Supports all AGS sprite formats and compression methods
- **🎮 User-friendly**: Simple command-line interface with progress tracking
- **📦 Modern**: Pure Python, no compilation required
- **🆓 Free**: Open source and actively maintained

## 🚀 Features

- ✅ **Ultra-fast extraction** (250+ sprites/second)
- ✅ **Full sprite decompression** (RLE, LZW, Deflate)
- ✅ **Complete palette handling** for indexed sprites
- ✅ **Support for all AGS sprite file versions** (4-12)
- ✅ **Multiple color depth support** (8-bit, 16-bit, 24-bit, 32-bit)
- ✅ **Batch extraction capabilities**
- ✅ **Range extraction** (e.g., "1000-1999")
- ✅ **Comprehensive sprite information display**

## 📋 Requirements

- Python 3.6+
- Pillow (PIL) library

Install Pillow with:
```bash
pip install Pillow
```

## 🎯 Usage

### List all sprites in a file
```bash
python sprite_extractor.py acsprset.spr -l
```

### Extract a specific sprite
```bash
python sprite_extractor.py acsprset.spr -e 3240
```

### Extract multiple sprites
```bash
python sprite_extractor.py acsprset.spr -e 3240 3241 3242
```

### Extract sprite ranges (NEW!)
```bash
# Extract sprites 1000-1999
python sprite_extractor.py acsprset.spr --range "1000-1999"

# Extract multiple ranges
python sprite_extractor.py acsprset.spr --range "100-200,500-600,1000-1100"
```

### Extract all sprites
```bash
python sprite_extractor.py acsprset.spr -a
```

### Specify output directory
```bash
python sprite_extractor.py acsprset.spr -e 3240 -o my_sprites
```

### Quiet mode (for scripts)
```bash
python sprite_extractor.py acsprset.spr --range "1000-1999" -q
```

## ⚙️ Command Line Options

- `spr_file`: Path to the .spr file (required)
- `-l, --list`: List all sprites in the file
- `-e, --extract`: Extract specific sprite number(s)
- `-a, --all`: Extract all sprites
- `-o, --output`: Output directory (default: extracted_sprites)
- `-q, --quiet`: Quiet mode (less verbose output)
- `--range`: Extract sprite range (e.g., "100-200" or "100-200,300-400")

## 📊 Performance

**Extraction Speed:**
- **250+ sprites/second** (optimized)
- **1000 sprites in ~4.5 seconds**
- **All 21,111 sprites in ~1.4 minutes**

## 📝 Example Output

```
Sprite file: acsprset.spr
Version: 12
Compressed: False
Number of sprites: 21111
Extracted 100/1000 sprites (418.8 sprites/sec, 0.2s elapsed)
Extracted 200/1000 sprites (373.8 sprites/sec, 0.5s elapsed)
...
Batch extraction complete: 1000 extracted, 0 failed in 4.5s (221.1 sprites/sec)
```

## 📋 Notes

- Sprite numbers are 0-based
- Extracted sprites are saved as PNG files with 5-digit zero-padded names (e.g., sprite_03240.png)
- Supports all major AGS sprite formats and compression methods

## 🗂️ File Format Support

The tool supports AGS sprite file formats:
- **Version 4**: Uncompressed with global palette
- **Version 5**: Compressed
- **Version 6-11**: Various compression options
- **Version 12**: Enhanced format with multiple compression methods and palette formats

## 🛠️ Technical Details

- **Decompression**: RLE, LZW, Deflate algorithms
- **Palette Support**: 24-bit RGB, 32-bit RGBA, 16-bit RGB565
- **Color Depths**: 8-bit indexed, 16-bit RGB565, 24-bit RGB, 32-bit RGBA
- **Optimizations**: Batch processing, reduced I/O operations, memory efficiency
