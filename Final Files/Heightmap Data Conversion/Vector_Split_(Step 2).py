import os

# CONFIGURATION
INPUT_FILE = "vector_table.lua"
OUTPUT_DIR = "vector_table_chunks"
CHUNKS = 10  # number of chunks to generate

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Read Lua vector table
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Strip Lua syntax
lines = [line.strip() for line in lines if line.strip()]
if lines[0].startswith("return"):
    lines = lines[1:]
if lines[0] == "{":
    lines = lines[1:]
if lines[-1] == "}":
    lines = lines[:-1]

# Calculate chunk size
total_lines = len(lines)
chunk_size = (total_lines + CHUNKS - 1) // CHUNKS  # ceil division

# Write each chunk
for i in range(CHUNKS):
    start = i * chunk_size
    end = min(start + chunk_size, total_lines)
    chunk_data = lines[start:end]
    if not chunk_data:
        continue
    out_lines = ["return {"] + ["    " + line for line in chunk_data] + ["}"]
    out_path = os.path.join(OUTPUT_DIR, f"vector_chunk_{i+1}.lua")
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("\n".join(out_lines))
    print(f"Wrote {out_path} with {len(chunk_data)} vectors.")
