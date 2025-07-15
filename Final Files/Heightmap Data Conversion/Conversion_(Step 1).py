#!/usr/bin/env python3
"""
Convert a PNG heightmap into a single Lua vector table.

Supports:
- 8/16-bit grayscale or RGBA PNGs
- Pure Python (no PIL/numpy)
- Manual world scaling

Output:
- vector_table.lua — a 1D Lua table with {x, y, z} entries.
"""

import os, struct, zlib, math

# ─── USER CONFIG ──────────────────────────────────────────────────

INPUT_PNG    = "heightmap.png"
OUTPUT_FILE  = "vector_table.lua"
WORLD_WIDTH  = 150000.0  # e.g. 150000 for 150 km
MAX_HEIGHT   = 2512.0    # Max terrain height in studs

# ─── PNG LOADER ──────────────────────────────────────────────────

def read_chunks(data):
    i = 8  # skip PNG header
    while i < len(data):
        length = struct.unpack(">I", data[i:i+4])[0]
        ctype = data[i+4:i+8]
        chunk = data[i+8:i+8+length]
        yield ctype, chunk
        i += length + 12

def parse_png(path):
    with open(path, "rb") as f:
        data = f.read()

    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError("Not a PNG file")

    idat_data = b""
    width = height = depth = ctype = None
    for name, chunk in read_chunks(data):
        if name == b'IHDR':
            width  = struct.unpack(">I", chunk[0:4])[0]
            height = struct.unpack(">I", chunk[4:8])[0]
            depth  = chunk[8]
            ctype  = chunk[9]
        elif name == b'IDAT':
            idat_data += chunk
        elif name == b'IEND':
            break

    raw = zlib.decompress(idat_data)
    bpp = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    pixel_size = (depth // 8) * bpp
    stride = width * pixel_size
    result = []

    offset = 0
    prev = bytearray(stride)
    for y in range(height):
        filt = raw[offset]
        scan = bytearray(raw[offset+1 : offset+1+stride])
        offset += 1 + stride
        recon = bytearray(stride)

        if filt == 0:
            recon = scan
        elif filt == 1:
            for i in range(stride):
                left = recon[i - pixel_size] if i >= pixel_size else 0
                recon[i] = (scan[i] + left) & 0xFF
        elif filt == 2:
            for i in range(stride):
                recon[i] = (scan[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                left = recon[i - pixel_size] if i >= pixel_size else 0
                up = prev[i]
                recon[i] = (scan[i] + ((left + up) >> 1)) & 0xFF
        elif filt == 4:
            for i in range(stride):
                a = recon[i - pixel_size] if i >= pixel_size else 0
                b = prev[i]
                c = prev[i - pixel_size] if i >= pixel_size else 0
                p = a + b - c
                pr = min((abs(p - a), a), (abs(p - b), b), (abs(p - c), c))[1]
                recon[i] = (scan[i] + pr) & 0xFF

        prev = recon
        row = []
        for x in range(width):
            if depth == 8:
                idx = x * bpp
                if ctype == 0:  # grayscale
                    v = recon[idx] / 255.0
                elif ctype == 6:  # RGBA
                    r, g, b = recon[idx:idx+3]
                    v = (0.299*r + 0.587*g + 0.114*b) / 255.0
            elif depth == 16:
                idx = x * bpp * 2
                if ctype == 0:  # grayscale
                    v = struct.unpack(">H", recon[idx:idx+2])[0] / 65535.0
                elif ctype == 6:  # RGBA
                    r = struct.unpack(">H", recon[idx:idx+2])[0]
                    g = struct.unpack(">H", recon[idx+2:idx+4])[0]
                    b = struct.unpack(">H", recon[idx+4:idx+6])[0]
                    v = (0.299*r + 0.587*g + 0.114*b) / 65535.0
            row.append(v)
        result.append(row)

    return result, width, height

# ─── EXPORT LUA VECTOR TABLE ─────────────────────────────────────

def export_vector_table(pixels, width, height, output_file, world_w, max_h):
    dx = world_w / width
    dz = world_w / height
    lines = ["return {"]
    for z in range(height):
        for x in range(width):
            gx = x * dx
            gz = z * dz
            y = pixels[z][x] * max_h
            lines.append(f"    {{x={gx:.2f}, y={y:.2f}, z={gz:.2f}}},")
    lines.append("}")
    with open(output_file, "w") as f:
        f.write("\n".join(lines))
    print(f"Exported {output_file}")

# ─── MAIN ────────────────────────────────────────────────────────

def main():
    print("Reading PNG...")
    pixels, width, height = parse_png(INPUT_PNG)
    print(f"Image loaded: {width} × {height}")
    export_vector_table(pixels, width, height, OUTPUT_FILE, WORLD_WIDTH, MAX_HEIGHT)
    print("Done.")

if __name__ == "__main__":
    main()
