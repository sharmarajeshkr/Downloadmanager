"""Generate icons for the browser extension using PIL or simple bytes"""
import sys
import os

def create_icon(size, path):
    """Create a simple WITTGrp-style icon."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Background rounded rect (Teal/Blue theme instead of flat red to look fresh)
        draw.rounded_rectangle([0, 0, size-1, size-1], radius=size//6,
                                fill=(15, 118, 110, 255)) # #0f766e
        # Draw "W" text
        try:
            # Try to load a nice font if possible, else default
            font = ImageFont.truetype("arialbd.ttf", int(size*0.7))
        except:
            font = ImageFont.load_default()
        
        # Calculate text centered
        # Simple centering approximation for W
        text = "W"
        # Just draw it roughly centered
        draw.text((size*0.15, size*0.1), text, font=font, fill=(255, 255, 255, 255))
        img.save(path, 'PNG')
        print(f"Created {path}")
    except ImportError:
        # Fallback raw PNG
        import struct, zlib
        def png_chunk(name, data):
            c = struct.pack('>I', len(data)) + name + data
            c += struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
            return c
        
        w, h = size, size
        ihdr = struct.pack('>II', w, h) + bytes([8, 6, 0, 0, 0])
        png = b'\x89PNG\r\n\x1a\n'
        png += png_chunk(b'IHDR', ihdr)
        
        raw2 = b''
        for y in range(h):
            raw2 += b'\x00'
            for x in range(w):
                raw2 += bytes([15, 118, 110, 255]) # Teal
        png += png_chunk(b'IDAT', zlib.compress(raw2, 9))
        png += png_chunk(b'IEND', b'')
        
        with open(path, 'wb') as f:
            f.write(png)
        print(f"Created basic icon {path}")

if __name__ == '__main__':
    ext_dir = os.path.join(os.path.dirname(__file__), 'browser_extension', 'chrome')
    for size in [16, 48, 128]:
        create_icon(size, os.path.join(ext_dir, f'icon{size}.png'))
    print("Icons generated!")
