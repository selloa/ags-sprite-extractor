# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-05-27

### Fixed

- v12 `fmt=33` (32-bit palette) sprites: read palette entries as **BGRA** (`A8R8G8B8`) instead of RGBA.
- Palette alpha handling: `alpha=0` entries are treated as **opaque** except the AGS magenta transparency color `(255, 0, 255)`.

### Added

- `__version__` module constant and `--version` CLI flag.

### Changed

- `.gitignore` excludes local `runs/`, `source/`, and test artifacts.

## [1.0.0] - 2025-09-15

### Added

- Initial release: AGS `.spr` extraction (versions 4–12), RLE/LZW/Deflate decompression, batch and range extraction, palette support for indexed sprites.
