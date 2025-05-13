import os
import struct
import zlib

# -- SETTINGS --
INPUT_PATH = 'heightmap.png'
CHUNK_SIZE = 256
OUTPUT_DIR = 'HeightmapChunks'

def read_png_grayscale(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()

    # Verify PNG header
    assert data[:8] == b'\x89PNG\r\n\x1a\n', "Invalid PNG file"
    pos = 8
    width = height = None
    image_data = b''

    while pos < len(data):
        chunk_len = struct.unpack(">I", data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8]
        chunk_data = data[pos+8:pos+8+chunk_len]
        pos += 12 + chunk_len

        if chunk_type == b'IHDR':
            width, height = struct.unpack(">II", chunk_data[:8])
            bit_depth = chunk_data[8]
            
            assert bit_depth == 8, "Only 8-bit grayscale PNGs are supported"
        elif chunk_type == b'IDAT':
            image_data += chunk_data
        elif chunk_type == b'IEND':
            break

    decompressed = zlib.decompress(image_data)
    stride = width + 1  # 1 filter byte per row
    pixels = []

    for y in range(height):
        row_start = y * stride + 1  # Skip filter byte
        row = list(decompressed[row_start:row_start + width])
        pixels.append(row)

    return pixels, width, height

def save_lua_chunk(chunk_data, chunk_x, chunk_y):
    lua_rows = ["    {" + ", ".join(map(str, row)) + "}" for row in chunk_data]
    lua_data = "{\n" + ",\n".join(lua_rows) + "\n}"
    lua_module = f"""-- Heightmap Chunk {chunk_x}, {chunk_y}
local chunk = {lua_data}
return chunk
"""
    file_name = f"Chunk_{chunk_x}_{chunk_y}.lua"
    with open(os.path.join(OUTPUT_DIR, file_name), 'w') as f:
        f.write(lua_module)

def split_and_export(pixels, width, height):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    chunks_x = width // CHUNK_SIZE
    chunks_y = height // CHUNK_SIZE

    print(f"Splitting {width}x{height} into {chunks_x * chunks_y} chunks...")

    for y in range(chunks_y):
        for x in range(chunks_x):
            chunk = [row[x * CHUNK_SIZE:(x + 1) * CHUNK_SIZE] for row in pixels[y * CHUNK_SIZE:(y + 1) * CHUNK_SIZE]]
            save_lua_chunk(chunk, x, y)

    print(f"Chunks saved to: {OUTPUT_DIR}/")

# --- MAIN EXECUTION ---
pixels, w, h = read_png_grayscale('heightmap.png')
split_and_export(pixels, w, h)
