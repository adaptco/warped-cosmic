import os
import hashlib
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
TARGET_DIR = r"c:\Users\eqhsp\.claude\projects\agents"
MAX_FILE_SIZE_CANDIDATE = 1024 * 1024 * 5  # 5 MB - Above this size, files will be chunked
MAX_CHUNK_SIZE = 1024 * 1024 * 1  # 1 MB chunk limit
EXCLUDED_EXTENSIONS = {".pyc", ".pyd", ".dll", ".exe", ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz"}
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache"}

def get_file_hash(filepath, blocksize=65536):
    """Calculates SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as afile:
            buf = afile.read(blocksize)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(blocksize)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return None

def deduplicate_directory(target_path):
    """Scans for and deletes identical file contents across the specific directory."""
    logger.info(f"Starting deduplication scan in: {target_path}")
    hashes = {}
    duplicates_removed = 0
    bytes_saved = 0

    for root, dirs, files in os.walk(target_path):
        # Prevent searching in excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in EXCLUDED_EXTENSIONS:
                continue
                
            filepath = os.path.join(root, filename)
            # Skip empty files or symlinks
            if os.path.islink(filepath) or os.path.getsize(filepath) == 0:
                continue

            file_hash = get_file_hash(filepath)
            if not file_hash:
                continue

            if file_hash in hashes:
                original = hashes[file_hash]
                logger.info(f"Duplicate found:\n  Keeping: {original}\n  Removing: {filepath}")
                try:
                    bytes_saved += os.path.getsize(filepath)
                    os.remove(filepath)
                    duplicates_removed += 1
                except Exception as e:
                    logger.error(f"Failed to remove {filepath}: {e}")
            else:
                hashes[file_hash] = filepath

    logger.info(f"Deduplication complete. Removed {duplicates_removed} duplicates. Saved {bytes_saved / 1024 / 1024:.2f} MB.")


def chunk_file(filepath, max_chunk_size=MAX_CHUNK_SIZE):
    """Splits a large file into smaller chunks, appending part numbers."""
    try:
        file_size = os.path.getsize(filepath)
        if file_size <= max_chunk_size:
            return

        logger.info(f"Chunking large file: {filepath} ({file_size / 1024 / 1024:.2f} MB)")
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            chunk_num = 1
            while True:
                # Read chunks of lines roughly matching chunk size to preserve newlines
                lines = f.readlines(max_chunk_size)
                if not lines:
                    break
                    
                chunk_path = f"{filepath}.part{chunk_num}"
                with open(chunk_path, 'w', encoding='utf-8') as out_f:
                    out_f.writelines(lines)
                logger.info(f"Created chunk: {chunk_path}")
                chunk_num += 1

        # Delete the original file after successful chunking
        os.remove(filepath)
        logger.info(f"Removed original large file: {filepath}")

    except Exception as e:
         logger.error(f"Error chunking {filepath}: {e}")

def chunk_large_files(target_path):
    """Scans specifically for large context files and chunks them."""
    logger.info("Starting chunking scan...")
    for root, dirs, files in os.walk(target_path):
         dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
         for filename in files:
             filepath = os.path.join(root, filename)
             if not os.path.exists(filepath):
                 continue
                 
             if os.path.getsize(filepath) > MAX_FILE_SIZE_CANDIDATE:
                 chunk_file(filepath)


if __name__ == "__main__":
    if not os.path.exists(TARGET_DIR):
        logger.error(f"Target directory {TARGET_DIR} does not exist.")
    else:
        logger.info("--- AGENT CONTEXT MANAGER START ---")
        deduplicate_directory(TARGET_DIR)
        chunk_large_files(TARGET_DIR)
        logger.info("--- AGENT CONTEXT MANAGER FINISH ---")
