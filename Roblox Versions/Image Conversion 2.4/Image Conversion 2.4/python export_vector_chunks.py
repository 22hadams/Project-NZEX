#!/usr/bin/env python3
"""
Export PNG heightmap as Lua vector table chunks.

Supports:
- 8/16-bit grayscale or RGBA PNGs
- Custom world width and height scaling
- Pure Python (no PIL, numpy)

Output:
- A folder "vector_chunks/" with Lua modules:
    Chunk_0_0.lua, Chunk_1_0.lua, ...
"""

import os, struct, zlib, math

# ─── CONFIG ─────────────────────────────────────────────────────

INPUT_PNG = "Image Conversion 2.4/heightmap.png"
OUTPUT_DIR   = "vector_chunks"
CHUNK_SIZE   = 250
WORLD_WIDTH  = 150000.0  # meters or studs
MAX_HEIGHT   = 2753.0    # vertical height

# ─── PNG LOADER ─────────────────────────────────────────────────

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
    for ctype_name, chunk in read_chunks(data):
        if ctype_name == b'IHDR':
            width, height, depth, ctype, *_ = struct.unpack(">IIBBBBB", chunk[:13])
        elif ctype_name == b'IDAT':
            idat_data += chunk
        elif ctype_name == b'IEND':
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
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                recon[i] = (scan[i] + pr) & 0xFF

        prev = recon
        row = []
        for x in range(width):
            if depth == 8:
                idx = x * bpp
                if ctype == 0:  # grayscale 8-bit
                    v = recon[idx] / 255.0
                elif ctype == 6:  # RGBA 8-bit
                    r, g, b = recon[idx:idx+3]
                    v = (0.299*r + 0.587*g + 0.114*b) / 255.0
            elif depth == 16:
                idx = x * bpp * 2
                if ctype == 0:  # grayscale 16-bit
                    v = struct.unpack(">H", recon[idx:idx+2])[0] / 65535.0
                elif ctype == 6:  # RGBA 16-bit
                    r = struct.unpack(">H", recon[idx:idx+2])[0]
                    g = struct.unpack(">H", recon[idx+2:idx+4])[0]
                    b = struct.unpack(">H", recon[idx+4:idx+6])[0]
                    v = (0.299*r + 0.587*g + 0.114*b) / 65535.0
            row.append(v)
        result.append(row)

    return result

# ─── CHUNKING ──────────────────────────────────────────────────

def pad_image(pixels, chunk_size):
    h = len(pixels)
    w = len(pixels[0])
    new_w = math.ceil(w / chunk_size) * chunk_size
    new_h = math.ceil(h / chunk_size) * chunk_size
    padded = [[0.0 for _ in range(new_w)] for _ in range(new_h)]
    for y in range(h):
        for x in range(w):
            padded[y][x] = pixels[y][x]
    return padded, new_w, new_h

def export_chunks(pixels, width, height, chunk_size, outdir, world_w, max_h):
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    chunks_x = width // chunk_size
    chunks_z = height // chunk_size

    dx = world_w / width
    dz = world_w / height

    for cz in range(chunks_z):
        for cx in range(chunks_x):
            lines = [f"-- Chunk_{cx}_{cz}.lua", "return {"]
            for z in range(chunk_size):
                row = []
                for x in range(chunk_size):
                    gx = (cx * chunk_size + x) * dx
                    gz = (cz * chunk_size + z) * dz
                    yval = pixels[cz * chunk_size + z][cx * chunk_size + x] * max_h
                    row.append(f"{{x={gx:.2f}, y={yval:.2f}, z={gz:.2f}}}")
                lines.append("    {" + ", ".join(row) + "},")
            lines.append("}")
            with open(f"{outdir}/Chunk_{cx}_{cz}.lua", "w") as f:
                f.write("\n".join(lines))
            print(f"Exported Chunk_{cx}_{cz}.lua")

# ─── MAIN ──────────────────────────────────────────────────────

def main():
    print("Reading PNG...")
    pixels = parse_png(INPUT_PNG)
    padded, new_w, new_h = pad_image(pixels, CHUNK_SIZE)
    print(f"Size padded to {new_w}×{new_h}")
    export_chunks(padded, new_w, new_h, CHUNK_SIZE, OUTPUT_DIR, WORLD_WIDTH, MAX_HEIGHT)
    print("Done.")

if __name__ == "__main__":
    main()
