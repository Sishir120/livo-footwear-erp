import struct
import zlib
import os

def create_png(width, height, draw_func, filepath):
    # RGBA
    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # filter type 0 (None)
        for x in range(width):
            r, g, b, a = draw_func(x, y, width, height)
            raw_data.extend([r, g, b, a])
    
    compressed = zlib.compress(bytes(raw_data), 9)
    
    png = bytearray(b'\x89PNG\r\n\x1a\n')
    
    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
    png.extend(struct.pack(">I", 13) + b'IHDR' + ihdr_data + struct.pack(">I", ihdr_crc))
    
    # IDAT
    idat_crc = zlib.crc32(b'IDAT' + compressed)
    png.extend(struct.pack(">I", len(compressed)) + b'IDAT' + compressed + struct.pack(">I", idat_crc))
    
    # IEND
    iend_crc = zlib.crc32(b'IEND')
    png.extend(struct.pack(">I", 0) + b'IEND' + struct.pack(">I", iend_crc))
    
    with open(filepath, "wb") as f:
        f.write(png)
    print(f"Generated PNG: {filepath} ({width}x{height})")

def livo_logo_pixel(x, y, w, h):
    # Normalized coords [0, 1]
    nx = x / w
    ny = y / h
    
    # Background: Rounded dark industrial navy square
    corner_r = 0.18
    # Distance to rounded box
    dx = max(0, abs(nx - 0.5) - (0.5 - corner_r))
    dy = max(0, abs(ny - 0.5) - (0.5 - corner_r))
    if (dx*dx + dy*dy) > corner_r * corner_r:
        return (0, 0, 0, 0) # Transparent outside
    
    # Border
    if nx < 0.04 or nx > 0.96 or ny < 0.04 or ny > 0.96:
        return (59, 130, 246, 255) # Electric blue border
    
    # LIVO Geometric "L" Monogram
    # Vertical bar of L: nx between 0.22 and 0.40, ny between 0.20 and 0.80
    in_vert = (0.22 <= nx <= 0.40) and (0.20 <= ny <= 0.80)
    # Horizontal bar of L: nx between 0.22 and 0.78, ny between 0.62 and 0.80
    in_horiz = (0.22 <= nx <= 0.78) and (0.62 <= ny <= 0.80)
    
    # Accent top-right dot (manufacturing diamond)
    in_accent = (0.58 <= nx <= 0.76) and (0.22 <= ny <= 0.40)
    
    if in_vert or in_horiz:
        return (255, 255, 255, 255) # Crisp White
    elif in_accent:
        return (59, 130, 246, 255) # Steel Blue accent dot
    else:
        # Industrial Dark Navy Background #0f172a
        return (15, 23, 42, 255)

out_dir = r"d:\Antigravity\Footwear app\frontend\public"
os.makedirs(out_dir, exist_ok=True)

create_png(192, 192, livo_logo_pixel, os.path.join(out_dir, "icon-192.png"))
create_png(512, 512, livo_logo_pixel, os.path.join(out_dir, "icon-512.png"))
create_png(180, 180, livo_logo_pixel, os.path.join(out_dir, "apple-touch-icon.png"))
create_png(32, 32, livo_logo_pixel, os.path.join(out_dir, "favicon-32.png"))

# Create valid Windows ICO file containing 32x32 PNG
with open(os.path.join(out_dir, "favicon-32.png"), "rb") as f:
    png_32 = f.read()

ico_header = struct.pack("<HHH", 0, 1, 1) # Reserved, Type 1 (ICO), 1 image
ico_entry = struct.pack("<BBBBHHII", 32, 32, 0, 0, 1, 32, len(png_32), 6 + 16)
with open(os.path.join(out_dir, "favicon.ico"), "wb") as f:
    f.write(ico_header + ico_entry + png_32)
print("Generated ICO: favicon.ico")
