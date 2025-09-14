#!/usr/bin/env python3
"""
AGS Sprite Extractor

A tool to extract individual sprites from AGS (.spr) files.
Based on the AGS sprite file format specification.
"""

import struct
import os
import sys
import zlib
from typing import Optional, Tuple, List
from PIL import Image
import argparse

class AGSSpriteFile:
    """AGS Sprite File Reader"""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.file = None
        self.version = 0
        self.num_sprites = 0
        self.compressed = False
        self.id = 0
        self.offsets = []
        self.palette = None
        
    def __enter__(self):
        self.file = open(self.filename, 'rb')
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
    
    def read_uchar(self) -> int:
        """Read unsigned char (1 byte)"""
        return struct.unpack('<B', self.file.read(1))[0]
    
    def read_ushort(self) -> int:
        """Read unsigned short (2 bytes, little-endian)"""
        return struct.unpack('<H', self.file.read(2))[0]
    
    def read_uint(self) -> int:
        """Read unsigned int (4 bytes, little-endian)"""
        return struct.unpack('<I', self.file.read(4))[0]
    
    def read_short(self) -> int:
        """Read signed short (2 bytes, little-endian)"""
        return struct.unpack('<h', self.file.read(2))[0]
    
    def read_int(self) -> int:
        """Read signed int (4 bytes, little-endian)"""
        return struct.unpack('<i', self.file.read(4))[0]
    
    def read_data(self, size: int) -> bytes:
        """Read raw data"""
        return self.file.read(size)
    
    def seek(self, position: int):
        """Seek to position"""
        self.file.seek(position)
    
    def tell(self) -> int:
        """Get current position"""
        return self.file.tell()
    
    def read_header(self) -> bool:
        """Read sprite file header"""
        self.seek(0)
        
        # Read version
        self.version = self.read_ushort()
        
        # Read magic string " Sprite File "
        magic = self.read_data(13)
        if magic != b' Sprite File ':
            print(f"Error: Invalid magic string: {magic}")
            return False
        
        # Parse version-specific header
        if self.version == 4:
            self.compressed = False
            # Read palette (256 colors * 3 bytes)
            self.palette = self.read_data(256 * 3)
        elif self.version == 5:
            self.compressed = True
        elif self.version >= 6:
            # Read compression flag
            comp_flag = self.read_uchar()
            self.compressed = (comp_flag == 1)
            self.id = self.read_uint()
        else:
            print(f"Error: Unsupported sprite file version: {self.version}")
            return False
        
        # Read number of sprites
        if self.version >= 11:
            self.num_sprites = self.read_uint()
        else:
            self.num_sprites = self.read_ushort()
        
        # Version 4 has fixed 200 sprites
        if self.version < 4:
            self.num_sprites = 200
        
        self.num_sprites += 1  # AGS uses 1-based indexing
        
        # Skip sprite storage flags for version >= 12
        if self.version >= 12:
            self.read_uint()
        
        return True
    
    def read_sprite_index(self) -> bool:
        """Read sprite index (table of contents)"""
        self.offsets = []
        
        for i in range(self.num_sprites):
            current_pos = self.tell()
            self.offsets.append(current_pos)
            
            # Read sprite header
            coldep = self.read_uchar()  # Color depth
            fmt = self.read_uchar()     # Format (version >= 12)
            
            if coldep == 0:
                # Empty sprite
                self.offsets[i] = 0
                continue
            
            if self.version >= 12:
                palsz = self.read_uchar() + 1  # Palette size
                compr = self.read_uchar()      # Compression
            else:
                palsz = 0
                compr = 0
            
            width = self.read_ushort()
            height = self.read_ushort()
            
            # Calculate data size
            if self.version < 12:
                if self.compressed:
                    data_size = self.read_uint()
                else:
                    data_size = coldep * width * height
            else:
                # Skip palette data
                pal_bytes = 0
                if fmt != 0:  # fmt_none
                    if fmt == 32:  # fmt_888
                        pal_bytes = 3 * palsz
                    elif fmt == 33:  # fmt_8888
                        pal_bytes = 4 * palsz
                    elif fmt == 34:  # fmt_565
                        pal_bytes = 2 * palsz
                
                if pal_bytes > 0:
                    self.read_data(pal_bytes)
                
                data_size = self.read_uint()
            
            # Skip sprite data
            self.read_data(data_size)
        
        return True
    
    def get_sprite_info(self, sprite_num: int) -> Optional[dict]:
        """Get information about a specific sprite"""
        if sprite_num >= len(self.offsets) or self.offsets[sprite_num] == 0:
            return None
        
        self.seek(self.offsets[sprite_num])
        
        coldep = self.read_uchar()
        fmt = self.read_uchar()
        
        if self.version >= 12:
            palsz = self.read_uchar() + 1
            compr = self.read_uchar()
        else:
            palsz = 0
            compr = 0
        
        width = self.read_ushort()
        height = self.read_ushort()
        
        return {
            'sprite_num': sprite_num,
            'coldep': coldep,
            'fmt': fmt,
            'palsz': palsz,
            'compr': compr,
            'width': width,
            'height': height,
            'offset': self.offsets[sprite_num]
        }
    
    def extract_sprite_optimized(self, sprite_num: int) -> Optional[Image.Image]:
        """Optimized sprite extraction that caches file position"""
        info = self.get_sprite_info(sprite_num)
        if not info:
            return None
        
        # Store current position to restore later
        current_pos = self.tell()
        
        try:
            # Seek to sprite data (we're already at the right position from get_sprite_info)
            # Skip header data that was already read
            if self.version >= 12:
                # Skip palette data if present
                if info['fmt'] != 0:
                    pal_bytes = 0
                    if info['fmt'] == 32:  # fmt_888
                        pal_bytes = 3 * info['palsz']
                    elif info['fmt'] == 33:  # fmt_8888
                        pal_bytes = 4 * info['palsz']
                    elif info['fmt'] == 34:  # fmt_565
                        pal_bytes = 2 * info['palsz']
                    
                    if pal_bytes > 0:
                        self.read_data(pal_bytes)
                
                data_size = self.read_uint()
            else:
                if self.compressed:
                    data_size = self.read_uint()
                else:
                    data_size = info['coldep'] * info['width'] * info['height']
            
            sprite_data = self.read_data(data_size)
            
            # Decompress the data
            expected_size = info['width'] * info['height'] * info['coldep']
            if self.version >= 12:
                if info['compr'] == 1:  # RLE compression
                    sprite_data = self.rle_decompress(sprite_data, info['width'], info['height'], info['coldep'])
                elif info['compr'] == 2:  # LZW compression
                    sprite_data = self.lzw_decompress(sprite_data, expected_size)
                elif info['compr'] == 3:  # Deflate compression
                    sprite_data = self.deflate_decompress(sprite_data, expected_size)
            elif self.compressed:
                # For older versions, assume RLE compression
                sprite_data = self.rle_decompress(sprite_data, info['width'], info['height'], info['coldep'])
            
            # Apply palette if needed
            if self.version >= 12 and info['fmt'] != 0:
                # Read palette data
                self.seek(self.offsets[sprite_num])
                self.read_uchar()  # coldep
                self.read_uchar()  # fmt
                self.read_uchar()  # palsz
                self.read_uchar()  # compr
                self.read_ushort()  # width
                self.read_ushort()  # height
                
                pal_bytes = 0
                if info['fmt'] == 32:  # fmt_888
                    pal_bytes = 3 * info['palsz']
                elif info['fmt'] == 33:  # fmt_8888
                    pal_bytes = 4 * info['palsz']
                elif info['fmt'] == 34:  # fmt_565
                    pal_bytes = 2 * info['palsz']
                
                palette_data = None
                if pal_bytes > 0:
                    palette_data = self.read_data(pal_bytes)
                    sprite_data = self.apply_palette(sprite_data, palette_data, info['fmt'], info['palsz'], info['width'], info['height'])
                    info['coldep'] = 4  # Palette output is always RGBA
            
            # Convert to PIL Image
            if info['coldep'] == 1:
                # 8-bit indexed
                img = Image.frombytes('L', (info['width'], info['height']), sprite_data)
            elif info['coldep'] == 2:
                # 16-bit RGB565 - convert to RGB
                rgb_data = bytearray(info['width'] * info['height'] * 3)
                for i in range(0, len(sprite_data), 2):
                    if i + 1 < len(sprite_data):
                        rgb565 = struct.unpack('<H', sprite_data[i:i+2])[0]
                        r = ((rgb565 >> 11) & 0x1F) << 3
                        g = ((rgb565 >> 5) & 0x3F) << 2
                        b = (rgb565 & 0x1F) << 3
                        rgb_data[i//2*3] = r
                        rgb_data[i//2*3+1] = g
                        rgb_data[i//2*3+2] = b
                img = Image.frombytes('RGB', (info['width'], info['height']), bytes(rgb_data))
            elif info['coldep'] == 3:
                # 24-bit RGB
                img = Image.frombytes('RGB', (info['width'], info['height']), sprite_data)
            elif info['coldep'] == 4:
                # 32-bit RGBA
                img = Image.frombytes('RGBA', (info['width'], info['height']), sprite_data)
            else:
                print(f"Warning: Unsupported color depth {info['coldep']}")
                return None
            
            return img
            
        finally:
            # Restore file position
            self.seek(current_pos)
    
    def rle_decompress(self, data: bytes, width: int, height: int, bpp: int) -> bytes:
        """Decompress RLE-compressed sprite data"""
        result = bytearray(width * height * bpp)
        data_pos = 0
        result_pos = 0
        
        while data_pos < len(data) and result_pos < len(result):
            if data_pos >= len(data):
                break
                
            count_byte = data[data_pos]
            data_pos += 1
            
            count = (count_byte & 0x7F) + 1
            is_repeat = (count_byte & 0x80) != 0
            
            if is_repeat:
                # Repeat the next pixel 'count' times
                if data_pos + bpp > len(data):
                    break
                    
                pixel_data = data[data_pos:data_pos + bpp]
                data_pos += bpp
                
                for _ in range(count):
                    if result_pos + bpp <= len(result):
                        result[result_pos:result_pos + bpp] = pixel_data
                        result_pos += bpp
            else:
                # Copy 'count' pixels directly
                copy_bytes = count * bpp
                if data_pos + copy_bytes > len(data) or result_pos + copy_bytes > len(result):
                    break
                    
                result[result_pos:result_pos + copy_bytes] = data[data_pos:data_pos + copy_bytes]
                data_pos += copy_bytes
                result_pos += copy_bytes
        
        return bytes(result)
    
    def lzw_decompress(self, data: bytes, expected_size: int) -> bytes:
        """Decompress LZW-compressed sprite data"""
        # This is a simplified LZW implementation
        # For full compatibility, we'd need the exact LZW algorithm used by AGS
        # For now, return the data as-is if it's already the right size
        if len(data) == expected_size:
            return data
        
        # Try to decompress with zlib as a fallback
        try:
            decompressed = zlib.decompress(data)
            if len(decompressed) == expected_size:
                return decompressed
        except:
            pass
        
        # If all else fails, return the original data
        return data
    
    def deflate_decompress(self, data: bytes, expected_size: int) -> bytes:
        """Decompress Deflate-compressed sprite data"""
        try:
            decompressed = zlib.decompress(data)
            if len(decompressed) == expected_size:
                return decompressed
        except:
            pass
        
        return data
    
    def apply_palette(self, data: bytes, palette_data: bytes, fmt: int, palsz: int, width: int, height: int) -> bytes:
        """Apply palette to indexed sprite data"""
        if fmt == 0:  # fmt_none
            return data
        
        result = bytearray(width * height * 4)  # Always output RGBA
        data_pos = 0
        result_pos = 0
        
        for _ in range(width * height):
            if data_pos >= len(data):
                break
                
            palette_index = data[data_pos]
            data_pos += 1
            
            if palette_index >= palsz:
                palette_index = 0
            
            # Get color from palette based on format
            if fmt == 32:  # fmt_888 (24-bit RGB)
                pal_offset = palette_index * 3
                if pal_offset + 2 < len(palette_data):
                    r = palette_data[pal_offset]
                    g = palette_data[pal_offset + 1]
                    b = palette_data[pal_offset + 2]
                    a = 255
                else:
                    r = g = b = 0
                    a = 255
            elif fmt == 33:  # fmt_8888 (32-bit RGBA)
                pal_offset = palette_index * 4
                if pal_offset + 3 < len(palette_data):
                    r = palette_data[pal_offset]
                    g = palette_data[pal_offset + 1]
                    b = palette_data[pal_offset + 2]
                    a = palette_data[pal_offset + 3]
                else:
                    r = g = b = a = 0
            elif fmt == 34:  # fmt_565 (16-bit RGB565)
                pal_offset = palette_index * 2
                if pal_offset + 1 < len(palette_data):
                    rgb565 = struct.unpack('<H', palette_data[pal_offset:pal_offset + 2])[0]
                    r = ((rgb565 >> 11) & 0x1F) << 3
                    g = ((rgb565 >> 5) & 0x3F) << 2
                    b = (rgb565 & 0x1F) << 3
                    a = 255
                else:
                    r = g = b = 0
                    a = 255
            else:
                r = g = b = 0
                a = 255
            
            result[result_pos] = r
            result[result_pos + 1] = g
            result[result_pos + 2] = b
            result[result_pos + 3] = a
            result_pos += 4
        
        return bytes(result)
    
    def extract_sprite(self, sprite_num: int) -> Optional[Image.Image]:
        """Extract a specific sprite as PIL Image"""
        info = self.get_sprite_info(sprite_num)
        if not info:
            return None
        
        self.seek(self.offsets[sprite_num])
        
        # Read header
        coldep = self.read_uchar()
        fmt = self.read_uchar()
        
        if self.version >= 12:
            palsz = self.read_uchar() + 1
            compr = self.read_uchar()
        else:
            palsz = 0
            compr = 0
        
        width = self.read_ushort()
        height = self.read_ushort()
        
        # Read palette if present
        palette_data = None
        if self.version >= 12 and fmt != 0:
            pal_bytes = 0
            if fmt == 32:  # fmt_888
                pal_bytes = 3 * palsz
            elif fmt == 33:  # fmt_8888
                pal_bytes = 4 * palsz
            elif fmt == 34:  # fmt_565
                pal_bytes = 2 * palsz
            
            if pal_bytes > 0:
                palette_data = self.read_data(pal_bytes)
        
        # Read sprite data
        if self.version < 12:
            if self.compressed:
                data_size = self.read_uint()
            else:
                data_size = coldep * width * height
        else:
            data_size = self.read_uint()
        
        sprite_data = self.read_data(data_size)
        
        # Decompress the data
        expected_size = width * height * coldep
        if self.version >= 12:
            if compr == 1:  # RLE compression
                sprite_data = self.rle_decompress(sprite_data, width, height, coldep)
            elif compr == 2:  # LZW compression
                sprite_data = self.lzw_decompress(sprite_data, expected_size)
            elif compr == 3:  # Deflate compression
                sprite_data = self.deflate_decompress(sprite_data, expected_size)
        elif self.compressed:
            # For older versions, assume RLE compression
            sprite_data = self.rle_decompress(sprite_data, width, height, coldep)
        
        # Apply palette if needed
        if palette_data and fmt != 0:
            sprite_data = self.apply_palette(sprite_data, palette_data, fmt, palsz, width, height)
            coldep = 4  # Palette output is always RGBA
        
        # Convert to PIL Image
        if coldep == 1:
            # 8-bit indexed
            img = Image.frombytes('L', (width, height), sprite_data)
        elif coldep == 2:
            # 16-bit RGB565 - convert to RGB
            rgb_data = bytearray(width * height * 3)
            for i in range(0, len(sprite_data), 2):
                if i + 1 < len(sprite_data):
                    rgb565 = struct.unpack('<H', sprite_data[i:i+2])[0]
                    r = ((rgb565 >> 11) & 0x1F) << 3
                    g = ((rgb565 >> 5) & 0x3F) << 2
                    b = (rgb565 & 0x1F) << 3
                    rgb_data[i//2*3] = r
                    rgb_data[i//2*3+1] = g
                    rgb_data[i//2*3+2] = b
            img = Image.frombytes('RGB', (width, height), bytes(rgb_data))
        elif coldep == 3:
            # 24-bit RGB
            img = Image.frombytes('RGB', (width, height), sprite_data)
        elif coldep == 4:
            # 32-bit RGBA
            img = Image.frombytes('RGBA', (width, height), sprite_data)
        else:
            print(f"Warning: Unsupported color depth {coldep}")
            return None
        
        return img

def extract_sprites_batch(spr, sprite_numbers, output_dir, verbose=True):
    """Optimized batch extraction of multiple sprites"""
    import time
    start_time = time.time()
    extracted_count = 0
    failed_count = 0
    
    for i, sprite_num in enumerate(sprite_numbers):
        if sprite_num >= spr.num_sprites:
            if verbose:
                print(f"Error: Sprite number {sprite_num} out of range (0-{spr.num_sprites-1})")
            failed_count += 1
            continue
        
        info = spr.get_sprite_info(sprite_num)
        if not info:
            if verbose:
                print(f"Sprite {sprite_num} is empty")
            failed_count += 1
            continue
        
        img = spr.extract_sprite_optimized(sprite_num)
        if img:
            output_path = os.path.join(output_dir, f'sprite_{sprite_num:05d}.png')
            img.save(output_path)
            extracted_count += 1
            
            # Progress reporting
            if verbose and (extracted_count % 100 == 0 or i == len(sprite_numbers) - 1):
                elapsed = time.time() - start_time
                rate = extracted_count / elapsed if elapsed > 0 else 0
                print(f"Extracted {extracted_count}/{len(sprite_numbers)} sprites "
                      f"({rate:.1f} sprites/sec, {elapsed:.1f}s elapsed)")
        else:
            if verbose:
                print(f"Failed to extract sprite {sprite_num}")
            failed_count += 1
    
    total_time = time.time() - start_time
    if verbose:
        print(f"Batch extraction complete: {extracted_count} extracted, {failed_count} failed "
              f"in {total_time:.1f}s ({extracted_count/total_time:.1f} sprites/sec)")
    
    return extracted_count, failed_count

def main():
    parser = argparse.ArgumentParser(description='Extract sprites from AGS .spr files')
    parser.add_argument('spr_file', help='Path to the .spr file')
    parser.add_argument('-l', '--list', action='store_true', help='List all sprites in the file')
    parser.add_argument('-e', '--extract', type=int, nargs='+', help='Extract specific sprite number(s)')
    parser.add_argument('-a', '--all', action='store_true', help='Extract all sprites')
    parser.add_argument('-o', '--output', default='extracted_sprites', help='Output directory')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode (less verbose output)')
    parser.add_argument('--range', help='Extract sprite range (e.g., "100-200" or "100-200,300-400")')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.spr_file):
        print(f"Error: File {args.spr_file} not found")
        return 1
    
    verbose = not args.quiet
    
    with AGSSpriteFile(args.spr_file) as spr:
        if not spr.read_header():
            return 1
        
        if verbose:
            print(f"Sprite file: {args.spr_file}")
            print(f"Version: {spr.version}")
            print(f"Compressed: {spr.compressed}")
            print(f"Number of sprites: {spr.num_sprites}")
        
        if not spr.read_sprite_index():
            print("Error reading sprite index")
            return 1
        
        if args.list:
            if verbose:
                print("\nSprite list:")
            for i in range(spr.num_sprites):
                info = spr.get_sprite_info(i)
                if info:
                    print(f"Sprite {i}: {info['width']}x{info['height']}, "
                          f"depth={info['coldep']}, offset=0x{info['offset']:x}")
                else:
                    print(f"Sprite {i}: (empty)")
        
        # Handle range extraction
        if args.range:
            sprite_numbers = []
            ranges = args.range.split(',')
            for range_str in ranges:
                if '-' in range_str:
                    start, end = map(int, range_str.split('-'))
                    sprite_numbers.extend(range(start, end + 1))
                else:
                    sprite_numbers.append(int(range_str))
            
            os.makedirs(args.output, exist_ok=True)
            extract_sprites_batch(spr, sprite_numbers, args.output, verbose)
        
        elif args.extract is not None:
            os.makedirs(args.output, exist_ok=True)
            extract_sprites_batch(spr, args.extract, args.output, verbose)
        
        elif args.all:
            os.makedirs(args.output, exist_ok=True)
            all_sprites = list(range(spr.num_sprites))
            extract_sprites_batch(spr, all_sprites, args.output, verbose)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
