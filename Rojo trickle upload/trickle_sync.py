import os
import shutil
import time

# CONFIGURATION
SRC_FULL = "src_full"
SRC_STAGING = "src_staging"
BATCH_SIZE = 1          # Files per batch
WAIT_SECONDS = 10        # Wait time between batches

def get_lua_files(directory):
    lua_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".lua"):
                lua_files.append(os.path.join(root, file))
    return lua_files

def relative_path(base, full):
    return os.path.relpath(full, base)

def trickle_move():
    while True:
        files = get_lua_files(SRC_FULL)
        if not files:
            print("✅ All files have been moved. Sync complete.")
            break

        batch = files[:BATCH_SIZE]
        for file in batch:
            rel_path = relative_path(SRC_FULL, file)
            dest_path = os.path.join(SRC_STAGING, rel_path)

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.move(file, dest_path)
            print(f"Moved: {rel_path}")

        print(f"✅ Moved {len(batch)} files. Waiting {WAIT_SECONDS} seconds for Rojo + Studio to sync...\n")
        time.sleep(WAIT_SECONDS)

if __name__ == "__main__":
    print(f"Starting trickle-feed: {BATCH_SIZE} files per batch, {WAIT_SECONDS}s wait between batches.")
    trickle_move()
