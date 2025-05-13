from PIL import Image

# SETTINGS
input_image = "150x150.png"  # your heightmap file
output_file = "HeightmapData.lua"
max_value = 255.0  # Max pixel brightness

# Open the image
img = Image.open(input_image).convert("L")  # "L" mode = grayscale
width, height = img.size
pixels = img.load()

# Build Lua file
with open(output_file, "w") as f:
    f.write("-- HeightmapData.lua\n")
    f.write("-- Auto-converted from PNG\n\n")
    f.write("return {\n")

    for y in range(height):
        f.write("    {")
        for x in range(width):
            value = pixels[x, y] / max_value
            f.write(f"{value:.4f}")
            if x != width - 1:
                f.write(", ")
        f.write("},\n")

    f.write("}\n")

print(f"✅ Done! HeightmapData.lua saved ({width} x {height} pixels).")
