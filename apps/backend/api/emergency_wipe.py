#!/usr/bin/env python3
"""
DoD 5220.22-M Emergency Wipe Functions

Standalone module for 7-pass secure file deletion.
Extracted from panic_mode_router.py for independent testing.

⚠️  CRITICAL: These functions PERMANENTLY DELETE data.
Only use in authorized emergency scenarios or isolated tests.
"""

import os
import glob
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


async def perform_dod_wipe(file_paths: List[str]) -> Dict[str, Any]:
    """
    Perform DoD 5220.22-M 7-pass overwrite on files and directories.

    ⚠️  CRITICAL: This function PERMANENTLY DELETES data.
    Only call in authorized emergency scenarios or isolated tests.

    **DoD 5220.22-M Standard:**
    - Pass 1: Write 0x00 (all zeros)
    - Pass 2: Write 0xFF (all ones)
    - Pass 3: Write 0x00
    - Pass 4: Write 0xFF
    - Pass 5: Write 0x00
    - Pass 6: Write 0xFF
    - Pass 7: Write random data
    - Final: Securely delete file

    Args:
        file_paths: List of file paths or directories to wipe

    Returns:
        Dict with 'count' (files wiped) and 'errors' (list of error messages)
    """
    count = 0
    errors = []

    for path in file_paths:
        expanded_path = os.path.expanduser(path)

        # Handle glob patterns (e.g., *.plist)
        if '*' in expanded_path:
            matched_files = glob.glob(expanded_path)
            for matched_file in matched_files:
                try:
                    await wipe_single_file(matched_file)
                    count += 1
                except Exception as e:
                    errors.append(f"{matched_file}: {str(e)}")
            continue

        # Handle directories recursively
        if os.path.isdir(expanded_path):
            for root, dirs, files in os.walk(expanded_path, topdown=False):
                # Wipe files
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        await wipe_single_file(file_path)
                        count += 1
                    except Exception as e:
                        errors.append(f"{file_path}: {str(e)}")

                # Remove empty directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        os.rmdir(dir_path)
                    except Exception as e:
                        errors.append(f"{dir_path}: {str(e)}")

            # Remove root directory
            try:
                os.rmdir(expanded_path)
            except Exception as e:
                errors.append(f"{expanded_path}: {str(e)}")

        # Handle single file
        elif os.path.isfile(expanded_path):
            try:
                await wipe_single_file(expanded_path)
                count += 1
            except Exception as e:
                errors.append(f"{expanded_path}: {str(e)}")

    return {
        "count": count,
        "errors": errors
    }


async def wipe_single_file(file_path: str):
    """
    Wipe a single file using DoD 5220.22-M 7-pass overwrite.

    ⚠️  CRITICAL: This function PERMANENTLY DELETES the file.

    Args:
        file_path: Path to file to wipe
    """
    if not os.path.exists(file_path):
        return

    file_size = os.path.getsize(file_path)

    # Perform 7-pass overwrite
    with open(file_path, "r+b") as f:
        for pass_num in range(7):
            f.seek(0)

            if pass_num == 6:
                # Pass 7: Random data (write in 1MB chunks for large files)
                chunk_size = 1024 * 1024  # 1MB
                remaining = file_size
                while remaining > 0:
                    chunk = min(chunk_size, remaining)
                    f.write(os.urandom(chunk))
                    remaining -= chunk
            elif pass_num % 2 == 0:
                # Passes 1, 3, 5: Write 0x00
                f.write(b'\x00' * file_size)
            else:
                # Passes 2, 4, 6: Write 0xFF
                f.write(b'\xFF' * file_size)

            # Force write to disk
            f.flush()
            os.fsync(f.fileno())

    # Securely delete file
    os.remove(file_path)
    logger.debug(f"   Wiped: {file_path}")
