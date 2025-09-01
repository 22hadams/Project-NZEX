
import struct
import os
import zlib
import math


VOXEL_RESOLUTION = 4.0  # meters per voxel step - keeping this consistent with engine


def read_png_chunk(file_handle):
    # Read the chunk length (4 bytes, big endian)
    chunk_len = struct.unpack(">I", file_handle.read(4))[0]
    chunk_type = file_handle.read(4).decode("ascii")
    chunk_data = file_handle.read(chunk_len)
    file_handle.read(4)  # skip CRC - were trusting the file is valid
    return chunk_type, chunk_data

def paeth_predictor(a, b, c):
    # PNG Paeth filter predictor - this is from the PNG spec
    p_val = a + b - c
    pa = abs(p_val - a)
    pb = abs(p_val - b) 
    pc = abs(p_val - c)
    
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    else:
        return c

def load_png_heightmap(file_path):
    
    #Load a PNG and return width, height, bit_depth, color_type, and normalized heightmap (0..1)
    #I only support grayscale (type 0) and RGBA (type 6) for now, both 8-bit and 16-bit.
    #Maybe I'll add more formats if I need them later.

    with open(file_path, "rb") as png_file:
        # Check PNG signature
        png_signature = png_file.read(8)
        if png_signature != b"\x89PNG\r\n\x1a\n":
            raise ValueError("This doesn't look like a valid PNG file!")

        # Initialize variables
        img_width = None
        img_height = None
        bit_depth = None
        color_type = None
        image_data = b""
        
        # Read chunks until we hit IEND
        while True:
            chunk_type, chunk_data = read_png_chunk(png_file)
            
            if chunk_type == "IHDR":
                header_data = struct.unpack(">IIBBBBB", chunk_data)
                img_width = header_data[0]
                img_height = header_data[1]
                bit_depth = header_data[2]
                color_type = header_data[3]
               
                
            elif chunk_type == "IDAT":
              
                image_data += chunk_data
                
            elif chunk_type == "IEND":
                break

    # Decompress the image data
    raw_pixel_data = zlib.decompress(image_data)


    bytes_per_pixel = 0
    if color_type == 0:  # grayscale
        bytes_per_pixel = 2 if bit_depth == 16 else 1
    elif color_type == 6:  # RGBA
        bytes_per_pixel = 8 if bit_depth == 16 else 4
    else:
        raise ValueError(f"Sorry, color type {color_type} isn't supported yet. Only grayscale (0) and RGBA (6) work.")

    bytes_per_row = img_width * bytes_per_pixel
    pixel_rows = []
    data_offset = 0
    

    for row_num in range(img_height):

        filter_type = raw_pixel_data[data_offset]
        data_offset += 1
        

        current_row = bytearray(raw_pixel_data[data_offset:data_offset + bytes_per_row])
        data_offset += bytes_per_row
        

        previous_row = pixel_rows[-1] if pixel_rows else bytearray(bytes_per_row)


        if filter_type == 0:

            pass
        elif filter_type == 1:  
            for i in range(bytes_per_pixel, bytes_per_row):
                current_row[i] = (current_row[i] + current_row[i - bytes_per_pixel]) & 0xFF
        elif filter_type == 2:  
            for i in range(bytes_per_row):
                current_row[i] = (current_row[i] + previous_row[i]) & 0xFF
        elif filter_type == 3:  
            for i in range(bytes_per_row):
                left_val = current_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                up_val = previous_row[i]
                current_row[i] = (current_row[i] + ((left_val + up_val) // 2)) & 0xFF
        elif filter_type == 4:  
            for i in range(bytes_per_row):
                left_val = current_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                up_val = previous_row[i]
                up_left_val = previous_row[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
                predicted = paeth_predictor(left_val, up_val, up_left_val)
                current_row[i] = (current_row[i] + predicted) & 0xFF
        else:
            raise ValueError(f"Unknown PNG filter type: {filter_type}")

        pixel_rows.append(current_row)


    height_data = []
    for row_idx in range(img_height):
        row_heights = []
        for col_idx in range(img_width):
            if color_type == 0:  # grayscale
                if bit_depth == 16:

                    pixel_value = (pixel_rows[row_idx][2 * col_idx] << 8) | pixel_rows[row_idx][2 * col_idx + 1]
                    max_value = 65535
                else:

                    pixel_value = pixel_rows[row_idx][col_idx]
                    max_value = 255
            else:  # RGBA - use red channel for height
                if bit_depth == 16:
                    # 16-bit RGBA: 8 bytes per pixel (R_hi, R_lo, G_hi, G_lo, B_hi, B_lo, A_hi, A_lo)
                    pixel_value = (pixel_rows[row_idx][8 * col_idx] << 8) | pixel_rows[row_idx][8 * col_idx + 1]
                    max_value = 65535
                else:
                    # 8-bit RGBA: 4 bytes per pixel, take red channel
                    pixel_value = pixel_rows[row_idx][4 * col_idx]
                    max_value = 255
            
            normalized_height = pixel_value / max_value
            row_heights.append(normalized_height)
        height_data.append(row_heights)

    return img_width, img_height, bit_depth, color_type, height_data

#Just some help with alliginment (found that roblox spits out errors if I don't)
def snap_to_resolution(value, resolution):
    """Snap a value to the nearest resolution step"""
    return round(value / resolution) * resolution


def process_heightmap():
    #user inputs
    input_png = input("Enter PNG heightmap file path: ").strip()
    world_size_meters = float(input("Enter world width in meters: ").strip())
    max_elevation = float(input("Enter maximum height in meters: ").strip())
    num_chunks_x = int(input("Enter number of chunks horizontally: ").strip())
    chunks_per_folder = int(input("Enter chunks per folder row (usually 10): ").strip())


    print("Loading PNG file...")
    png_width, png_height, bit_depth, color_type, heightmap_data = load_png_heightmap(input_png)
    print(f"Loaded {png_width}x{png_height} PNG, {bit_depth}-bit, color type {color_type}")

    # Calculate scaling factors
    # You give width as an input and we use the resolution of the image to determine the depth
    x_scale = world_size_meters / png_width
    z_scale = world_size_meters / png_height

 
    chunk_size_px = png_width // num_chunks_x
    if chunk_size_px <= 0:
        raise ValueError("Too many chunks for image width!")
    

    chunk_height_px = chunk_size_px
    num_chunks_z = (png_height + chunk_height_px - 1) // chunk_height_px

    # Create output directory
    output_dir = "Chunks"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")


    quantized_y_size = math.ceil(max_elevation / VOXEL_RESOLUTION) * VOXEL_RESOLUTION
    grid_y_count = int(quantized_y_size // VOXEL_RESOLUTION)

    # Generate metadata
    metadata_content = f"""return {{
  source_png = "{os.path.basename(input_png)}",
  image_size = {{width = {png_width}, height = {png_height}}},
  world_size = {{width_m = {world_size_meters}, max_height_m = {max_elevation}}},
  scale = {{x = {x_scale}, y = {max_elevation}, z = {z_scale}}},
  quantization = {{step_m = {VOXEL_RESOLUTION}}},
  chunks = {{chunk_width_px = {chunk_size_px}, chunks_x = {num_chunks_x}, chunks_z = {num_chunks_z}}},
  folder_rows = {chunks_per_folder},
  notes = "Chunks use gridH format with top voxel indices (-1 = empty). rSize.y rounded up to RES, gy = rSize.y / RES"
}}
"""
    
    metadata_path = os.path.join(output_dir, "metadata.lua")
    with open(metadata_path, "w", encoding="utf-8") as meta_file:
        meta_file.write(metadata_content)
    print("Generated metadata.lua")

    # Process each
    total_chunks = num_chunks_x * num_chunks_z
    processed_chunks = 0
    
    print(f"Processing {total_chunks} chunks...")
    
    for chunk_z in range(num_chunks_z):
        # Create folder grouping for chunks
        folder_group_start = (chunk_z // chunks_per_folder) * chunks_per_folder
        folder_group_end = folder_group_start + chunks_per_folder - 1
        folder_name = f"Y_{folder_group_start}-{folder_group_end}"
        folder_full_path = os.path.join(output_dir, folder_name)
        os.makedirs(folder_full_path, exist_ok=True)

        for chunk_x in range(num_chunks_x):
            chunk_id = f"Chunk{chunk_x}_{chunk_z}"
            chunk_dir = os.path.join(folder_full_path, chunk_id)
            os.makedirs(chunk_dir, exist_ok=True)
            
            # Create Assets sub-folder
            assets_dir = os.path.join(chunk_dir, "Assets")
            os.makedirs(assets_dir, exist_ok=True)

            # Calculate pixel
            px_start_x = chunk_x * chunk_size_px
            px_end_x = min((chunk_x + 1) * chunk_size_px, png_width)
            px_start_z = chunk_z * chunk_height_px
            px_end_z = min((chunk_z + 1) * chunk_height_px, png_height)

            # Calculate world coordinates, snapped to resolution
            world_min_x = snap_to_resolution(chunk_x * chunk_size_px * x_scale, VOXEL_RESOLUTION)
            world_min_z = snap_to_resolution(chunk_z * chunk_height_px * z_scale, VOXEL_RESOLUTION)
            world_min_y = 0.0

            # Calculate actual world dimensions fo this chunk
            actual_chunk_width = (px_end_x - px_start_x) * x_scale
            actual_chunk_depth = (px_end_z - px_start_z) * z_scale

            
            grid_x_count = max(1, int(math.ceil(actual_chunk_width / VOXEL_RESOLUTION)))
            grid_z_count = max(1, int(math.ceil(actual_chunk_depth / VOXEL_RESOLUTION)))

            
            final_size_x = grid_x_count * VOXEL_RESOLUTION
            final_size_z = grid_z_count * VOXEL_RESOLUTION
            final_size_y = quantized_y_size

        
            height_grid = [[-1 for _ in range(grid_z_count)] for _ in range(grid_x_count)]

           
            for pixel_z in range(px_start_z, px_end_z):
                for pixel_x in range(px_start_x, px_end_x):
                    
                    local_pixel_x = pixel_x - px_start_x
                    local_pixel_z = pixel_z - px_start_z
                    
                    
                    world_x = world_min_x + (local_pixel_x + 0.5) * x_scale
                    world_z = world_min_z + (local_pixel_z + 0.5) * z_scale

                   
                    normalized_height = heightmap_data[pixel_z][pixel_x]  # 0..1
                    world_height = normalized_height * max_elevation

                   
                    height_index = int(round(world_height / VOXEL_RESOLUTION))
                    
                  
                    if height_index < 0:
                        height_index = 0
                    elif height_index >= grid_y_count:
                        height_index = grid_y_count - 1

                    
                    grid_x_idx = int(math.floor((world_x - world_min_x) / VOXEL_RESOLUTION))
                    grid_z_idx = int(math.floor((world_z - world_min_z) / VOXEL_RESOLUTION))

                    
                    if grid_x_idx < 0: 
                        grid_x_idx = 0
                    elif grid_x_idx >= grid_x_count: 
                        grid_x_idx = grid_x_count - 1
                        
                    if grid_z_idx < 0: 
                        grid_z_idx = 0
                    elif grid_z_idx >= grid_z_count: 
                        grid_z_idx = grid_z_count - 1

                    if height_index > height_grid[grid_x_idx][grid_z_idx]:
                        height_grid[grid_x_idx][grid_z_idx] = height_index


            chunk_filename = os.path.join(chunk_dir, f"{chunk_id}.lua")
            with open(chunk_filename, "w", encoding="utf-8") as chunk_file:
                chunk_file.write(f"-- Generated chunk: {chunk_id}\n")
                chunk_file.write("return {\n")
                chunk_file.write(f"  gx = {grid_x_count}, gy = {grid_y_count}, gz = {grid_z_count},\n")
                chunk_file.write(f"  rMin = {{ x = {world_min_x:.3f}, y = {world_min_y:.3f}, z = {world_min_z:.3f} }},\n")
                chunk_file.write(f"  rSize = {{ x = {final_size_x:.3f}, y = {final_size_y:.3f}, z = {final_size_z:.3f} }}, -- world dimensions in meters\n")
                chunk_file.write("  gridH = {\n")
                

                for x_idx in range(grid_x_count):
                    height_values = ", ".join(str(int(height_val)) for height_val in height_grid[x_idx])
                    chunk_file.write("    { " + height_values + " },\n")
                    
                chunk_file.write("  }\n")
                chunk_file.write("}\n")

            processed_chunks += 1
            if processed_chunks % 10 == 0:  # Progress update every 10 chunks; to reduce lag
                print(f"Processed {processed_chunks}/{total_chunks} chunks...")

    print(f"Complete, Generated {total_chunks} chunks")
    print(f"Output directory: {output_dir}")

if __name__ == "__main__":
    process_heightmap()