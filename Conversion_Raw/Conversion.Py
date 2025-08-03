import os
import struct
import zlib

def parse_png_header(data):
    # IHDR chunk data should be exactly 13 bytes (after PNG signature and chunk length/type)
    if len(data) < 29:
        raise ValueError("PNG file too short to contain valid IHDR chunk")
    ihdr_data = data[16:29]  # 13 bytes

    width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", ihdr_data)

    # We ignore compression, filter_method, and interlace since they are standard in PNG files
    return width, height, bit_depth, color_type


def read_png_scanlines(filename):
    with open(filename, "rb") as f:
        data = f.read()

    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Not a PNG file")

    width, height, bit_depth, color_type = parse_png_header(data)

    # Extract all IDAT chunks and concatenate
    pos = 8  # after signature
    idat_data = b""
    while pos < len(data):
        if pos + 8 > len(data):
            break
        chunk_len = struct.unpack(">I", data[pos:pos+4])[0]
        chunk_type = data[pos+4:pos+8]
        chunk_data = data[pos+8:pos+8+chunk_len]
        pos += chunk_len + 12  # length(4)+type(4)+data+crc(4)
        if chunk_type == b'IDAT':
            idat_data += chunk_data
        elif chunk_type == b'IEND':
            break

    raw = zlib.decompress(idat_data)

    if color_type == 0:
        channels = 1
    elif color_type == 2:
        channels = 3
    elif color_type == 6:
        channels = 4
    else:
        raise ValueError(f"Unsupported color type {color_type}")

    bpp = channels * (bit_depth // 8)
    stride = bpp * width

    def unfilter_scanline(filter_type, scanline, bpp, prev_line):
        result = bytearray(scanline)
        if filter_type == 0:  # None
            return result
        elif filter_type == 1:  # Sub
            for i in range(bpp, len(result)):
                result[i] = (result[i] + result[i - bpp]) & 0xFF
            return result
        elif filter_type == 2:  # Up
            for i in range(len(result)):
                result[i] = (result[i] + prev_line[i]) & 0xFF
            return result
        elif filter_type == 3:  # Average
            for i in range(len(result)):
                left = result[i - bpp] if i >= bpp else 0
                up = prev_line[i]
                result[i] = (result[i] + ((left + up) >> 1)) & 0xFF
            return result
        elif filter_type == 4:  # Paeth
            def paeth_predictor(a, b, c):
                p = a + b - c
                pa = abs(p - a)
                pb = abs(p - b)
                pc = abs(p - c)
                if pa <= pb and pa <= pc:
                    return a
                elif pb <= pc:
                    return b
                else:
                    return c
            for i in range(len(result)):
                left = result[i - bpp] if i >= bpp else 0
                up = prev_line[i]
                up_left = prev_line[i - bpp] if i >= bpp else 0
                result[i] = (result[i] + paeth_predictor(left, up, up_left)) & 0xFF
            return result
        else:
            raise ValueError(f"Unsupported filter type: {filter_type}")

    scanlines = []
    pos = 0
    prev_line = bytearray(stride)
    for _ in range(height):
        filter_type = raw[pos]
        pos += 1
        scanline = raw[pos:pos+stride]
        pos += stride
        unfiltered = unfilter_scanline(filter_type, scanline, bpp, prev_line)
        scanlines.append(unfiltered)
        prev_line = unfiltered

    return scanlines, width, height, bit_depth, color_type, bpp

def build_lua_table(scanlines, width, height, bpp, scale_x, scale_y, scale_z, bit_depth):
    lua_table = []
    max_value = 65535 if bit_depth == 16 else 255

    for y in range(height):
        row = []
        line = scanlines[y]
        for x in range(width):
            # Calculate pixel height value based on bit depth and color type
            if bpp == 1:
                val = line[x]
            elif bpp == 2:
                val = line[x*2] << 8 | line[x*2+1]
            elif bpp >= 3:
                # For RGB or RGBA, use grayscale approximation or just first channel
                # Here, just use first channel (red) for heightmap
                if bit_depth == 8:
                    val = line[x*bpp]
                else:  # 16 bit per channel
                    val = (line[x*bpp] << 8) | line[x*bpp+1]
            else:
                val = 0
            height_value = val / max_value * scale_y
            # Output in format {height, 0, depth} where depth = x * scale_z
            row.append((round(height_value, 3), 0, round(x * scale_z, 3)))
        lua_table.append(row)
    return lua_table

def chunk_and_write(lua_table, width, height, scale_x, scale_y, scale_z, num_chunks_x, rows_per_file):
    output_root = "output"
    os.makedirs(output_root, exist_ok=True)

    # Calculate number of vertical chunks based on image aspect ratio and horizontal chunks
    num_chunks_z = max(1, round(height / width * num_chunks_x))
    chunk_width_px = width // num_chunks_x
    chunk_height_px = height // num_chunks_z

    # Calculate total number of row folders (files) to output
    total_row_folders = (num_chunks_z + rows_per_file - 1) // rows_per_file

    print(f"Exporting {num_chunks_x} horizontal chunks x {num_chunks_z} vertical chunks")
    print(f"Chunks per row folder: {rows_per_file}, Total row folders: {total_row_folders}")

    # For each row folder
    for row_folder_index in range(total_row_folders):
        row_start = row_folder_index * rows_per_file
        row_end = min(row_start + rows_per_file, num_chunks_z)

        row_folder_name = f"Row{row_start}-{row_end-1}"
        row_folder_path = os.path.join(output_root, row_folder_name)
        os.makedirs(row_folder_path, exist_ok=True)

        # For each vertical chunk in this row folder
        for chunk_z in range(row_start, row_end):
            z_start = chunk_z * chunk_height_px
            z_end = height if chunk_z == num_chunks_z - 1 else (chunk_z + 1) * chunk_height_px

            # For each horizontal chunk
            for chunk_x in range(num_chunks_x):
                x_start = chunk_x * chunk_width_px
                x_end = width if chunk_x == num_chunks_x - 1 else (chunk_x + 1) * chunk_width_px

                # Create chunk folder and file
                chunk_folder_name = f"Chunk{chunk_x}_{chunk_z}"
                chunk_folder_path = os.path.join(row_folder_path, chunk_folder_name)
                os.makedirs(chunk_folder_path, exist_ok=True)

                chunk_file_path = os.path.join(chunk_folder_path, f"{chunk_folder_name}.lua")

                with open(chunk_file_path, "w", encoding="utf-8") as f:
                    f.write(f"-- Chunk {chunk_x},{chunk_z}\n")
                    f.write("return {\n")
                    for y in range(z_start, z_end):
                        f.write("  {")
                        row_vals = []
                        for x in range(x_start, x_end):
                            h, _, d = lua_table[y][x]
                            # Format as {height,0,depth}
                            row_vals.append(f"{{{h},{0},{d}}}")
                        f.write(",".join(row_vals))
                        f.write("},\n")
                    f.write("}\n")
    print("Export complete.")

def main():
    path = input("PNG file path: ").strip()
    scale_y = float(input("Terrain max height in meters: "))
    scale_x = float(input("Terrain width (X) in meters: "))
    num_chunks_x = int(input("Number of horizontal chunks: "))
    rows_per_file = int(input("Rows per file (Z): "))

    print("Reading image...")
    scanlines, img_w, img_h, bit_depth, color_type, bpp = read_png_scanlines(path)

    # Calculate scale_z to maintain aspect ratio
    scale_z = scale_x / img_w

    print(f"Image width: {img_w} px, height: {img_h} px")
    print(f"Bit depth: {bit_depth}, Color type: {color_type}")

    print("Converting to Lua heightmap...")
    lua_table = build_lua_table(scanlines, img_w, img_h, bpp, scale_x, scale_y, scale_z, bit_depth)

    print("Chunking and exporting...")
    chunk_and_write(lua_table, img_w, img_h, scale_x, scale_y, scale_z, num_chunks_x, rows_per_file)

if __name__ == "__main__":
    main()
