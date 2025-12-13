#!/usr/bin/env python3
"""
Enable WAL mode for all SQLite databases in MagnetarStudio.

This is a one-time script to enable Write-Ahead Logging (WAL) mode
for all existing databases. WAL mode provides:
- 5-10x faster concurrent reads
- Reads don't block writes
- Writes don't block reads

Run this once, and all databases will stay in WAL mode.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from api.db_utils import enable_wal_for_existing_db, verify_wal_mode


def main():
    """Enable WAL mode for all MagnetarStudio databases"""

    # Find all .db files in .neutron_data
    neutron_data = Path(__file__).parent / ".neutron_data"

    if not neutron_data.exists():
        print(f"❌ .neutron_data directory not found at {neutron_data}")
        return

    db_files = list(neutron_data.rglob("*.db"))

    if not db_files:
        print("⚠️ No database files found in .neutron_data")
        return

    print(f"Found {len(db_files)} database files:\n")

    results = []
    for db_file in db_files:
        # Check if already in WAL mode
        already_wal = verify_wal_mode(db_file)

        if already_wal:
            print(f"✅ {db_file.relative_to(neutron_data)} - Already in WAL mode")
            results.append((db_file, True, "already_enabled"))
        else:
            # Enable WAL mode
            success = enable_wal_for_existing_db(db_file)

            if success:
                print(f"✅ {db_file.relative_to(neutron_data)} - WAL mode enabled!")
                results.append((db_file, True, "newly_enabled"))
            else:
                print(f"❌ {db_file.relative_to(neutron_data)} - Failed to enable WAL mode")
                results.append((db_file, False, "failed"))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    already_enabled = sum(1 for _, _, status in results if status == "already_enabled")
    newly_enabled = sum(1 for _, _, status in results if status == "newly_enabled")
    failed = sum(1 for _, _, status in results if status == "failed")

    print(f"Total databases: {len(results)}")
    print(f"Already in WAL mode: {already_enabled}")
    print(f"Newly enabled: {newly_enabled}")
    print(f"Failed: {failed}")

    if newly_enabled > 0:
        print(f"\n🎉 Successfully enabled WAL mode for {newly_enabled} database(s)!")
        print("   Your database operations are now 5-10x faster for concurrent reads!")

    if failed > 0:
        print(f"\n⚠️ {failed} database(s) failed to enable WAL mode.")
        print("   Check the error messages above for details.")

    if already_enabled == len(results):
        print("\n✨ All databases already have WAL mode enabled. You're all set!")


if __name__ == "__main__":
    main()
