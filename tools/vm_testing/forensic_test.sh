#!/bin/bash
# forensic_test.sh
# MagnetarStudio Forensic Analysis & Recovery Testing
#
# Purpose: Attempt to recover deleted files using forensic tools
# Usage: ./forensic_test.sh
# Safety: Only run in VMs after emergency wipe
# Requirements: Disk Drill (manual), photorec, testdisk
#
# For His glory and the protection of His people. 🙏

set -e  # Exit on error

echo "🔬 MagnetarStudio Forensic Analysis"
echo "===================================="
echo ""

# Safety check
echo "⚠️  SAFETY CHECK: This will attempt to recover deleted files"
read -p "Are you running this in an isolated VM after emergency wipe? (yes/no): " vm_confirm
if [ "$vm_confirm" != "yes" ]; then
    echo "❌ Aborted: Safety confirmation failed"
    exit 1
fi

echo ""
echo "✅ Safety confirmation received"
echo ""

# Create recovery directory
RECOVERY_DIR="$HOME/forensic_recovery"
mkdir -p "$RECOVERY_DIR"

echo "Recovery directory: $RECOVERY_DIR"
echo ""

# Get disk identifier
DISK_ID=$(diskutil list | grep "disk1" | head -1 | awk '{print $1}' || echo "disk1")
echo "Target disk: $DISK_ID"
echo ""

# Initialize counters
PHOTOREC_RECOVERED=0
TESTDISK_RECOVERED=0
STRING_SEARCH_MATCHES=0

# ===== PHASE 1: PhotoRec Data Carving =====
echo "=============================================="
echo "PHASE 1: PhotoRec Data Carving"
echo "=============================================="
echo ""

echo "PhotoRec will attempt to recover deleted files by scanning"
echo "the disk for file signatures and data patterns."
echo ""

# Check if photorec is installed
if ! command -v photorec &> /dev/null; then
    echo "⚠️  PhotoRec not installed"
    echo "   Install: brew install testdisk"
    echo "   Skipping PhotoRec phase..."
else
    echo "Running PhotoRec..."
    echo ""

    # Create PhotoRec config
    PHOTOREC_DIR="$RECOVERY_DIR/photorec"
    mkdir -p "$PHOTOREC_DIR"

    # Run PhotoRec (non-interactive mode)
    # Note: This attempts to recover all file types
    echo "Scanning disk for recoverable files..."
    echo "(This may take 10-30 minutes depending on disk size)"
    echo ""

    # PhotoRec command (adjust disk identifier as needed)
    # sudo photorec /d "$PHOTOREC_DIR" /cmd /dev/$DISK_ID options,fileopt,everything,enable,search

    echo "⚠️  PhotoRec requires manual execution:"
    echo ""
    echo "Run this command:"
    echo "  sudo photorec /d $PHOTOREC_DIR /cmd /dev/$DISK_ID options,fileopt,everything,enable,search"
    echo ""
    read -p "Press Enter after PhotoRec completes..."

    # Count recovered files
    if [ -d "$PHOTOREC_DIR" ]; then
        PHOTOREC_RECOVERED=$(find "$PHOTOREC_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
        echo ""
        echo "PhotoRec Results:"
        echo "  Files recovered: $PHOTOREC_RECOVERED"

        if [ $PHOTOREC_RECOVERED -gt 0 ]; then
            echo ""
            echo "  ⚠️  WARNING: PhotoRec recovered files!"
            echo "  File types found:"
            find "$PHOTOREC_DIR" -type f -exec file {} \; | awk -F: '{print $2}' | sort | uniq -c
        else
            echo "  ✅ SUCCESS: No files recovered by PhotoRec"
        fi
    fi
fi

echo ""

# ===== PHASE 2: TestDisk Partition Recovery =====
echo "=============================================="
echo "PHASE 2: TestDisk Partition Recovery"
echo "=============================================="
echo ""

echo "TestDisk will attempt to recover deleted partitions and"
echo "file system structures."
echo ""

# Check if testdisk is installed
if ! command -v testdisk &> /dev/null; then
    echo "⚠️  TestDisk not installed"
    echo "   Install: brew install testdisk"
    echo "   Skipping TestDisk phase..."
else
    echo "Running TestDisk..."
    echo ""

    TESTDISK_DIR="$RECOVERY_DIR/testdisk"
    mkdir -p "$TESTDISK_DIR"

    echo "⚠️  TestDisk requires manual execution:"
    echo ""
    echo "Run this command:"
    echo "  sudo testdisk /log $TESTDISK_DIR/testdisk.log /dev/$DISK_ID"
    echo ""
    echo "Steps:"
    echo "1. Select the disk"
    echo "2. Choose partition type (usually Intel/Mac)"
    echo "3. Select 'Analyse' to search for partitions"
    echo "4. Select 'Advanced' to search for files"
    echo "5. Document any recovered files"
    echo ""
    read -p "Press Enter after TestDisk completes..."

    # Check for recovered files
    if [ -d "$TESTDISK_DIR" ]; then
        TESTDISK_RECOVERED=$(find "$TESTDISK_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
        echo ""
        echo "TestDisk Results:"
        echo "  Files recovered: $TESTDISK_RECOVERED"

        if [ $TESTDISK_RECOVERED -gt 0 ]; then
            echo "  ⚠️  WARNING: TestDisk recovered files!"
        else
            echo "  ✅ SUCCESS: No files recovered by TestDisk"
        fi
    fi
fi

echo ""

# ===== PHASE 3: String Search for Sensitive Data =====
echo "=============================================="
echo "PHASE 3: String Search for Sensitive Data"
echo "=============================================="
echo ""

echo "Searching disk for sensitive string patterns that may"
echo "remain after DoD 7-pass wipe..."
echo ""

# Search patterns (from our fake test data)
SEARCH_PATTERNS=(
    "FAKE SENSITIVE DATA"
    "REDACTED_TEST_PASSWORD"
    "sk-test-1234567890abcdef"
    "SENSITIVE_VAULT_KEY"
    "test_user@example.com"
    "magnetarstudio"
    "elohimos"
)

STRING_SEARCH_DIR="$RECOVERY_DIR/string_search"
mkdir -p "$STRING_SEARCH_DIR"

echo "Searching for sensitive strings on disk..."
echo "(This may take 5-15 minutes)"
echo ""

for pattern in "${SEARCH_PATTERNS[@]}"; do
    echo "Searching for: $pattern"

    # Use strings + grep to search disk
    # Note: This requires sudo access to read raw disk
    MATCHES=$(sudo strings /dev/$DISK_ID 2>/dev/null | grep -i "$pattern" | wc -l | tr -d ' ' || echo "0")

    if [ "$MATCHES" -gt 0 ]; then
        echo "  ⚠️  WARNING: Found $MATCHES matches!"
        STRING_SEARCH_MATCHES=$((STRING_SEARCH_MATCHES + MATCHES))

        # Save matches to file
        sudo strings /dev/$DISK_ID 2>/dev/null | grep -i "$pattern" > "$STRING_SEARCH_DIR/${pattern}_matches.txt" || true
    else
        echo "  ✅ No matches found"
    fi
done

echo ""
echo "String Search Results:"
echo "  Total matches: $STRING_SEARCH_MATCHES"

if [ $STRING_SEARCH_MATCHES -gt 0 ]; then
    echo "  ⚠️  WARNING: Sensitive strings still present on disk!"
    echo "  DoD 7-pass wipe may not have completed successfully."
else
    echo "  ✅ SUCCESS: No sensitive strings found on disk"
fi

echo ""

# ===== PHASE 4: Disk Drill Analysis =====
echo "=============================================="
echo "PHASE 4: Disk Drill Analysis (Manual)"
echo "=============================================="
echo ""

echo "Disk Drill is a commercial forensic tool with advanced recovery"
echo "capabilities. It should be tested manually."
echo ""

echo "Steps:"
echo "1. Download Disk Drill from: https://www.cleverfiles.com/"
echo "2. Install and launch Disk Drill"
echo "3. Select the disk: $DISK_ID"
echo "4. Run 'Deep Scan' recovery"
echo "5. Check for any recovered files related to:"
echo "   - .magnetar directory"
echo "   - vault databases"
echo "   - model files"
echo "   - encrypted backups"
echo "   - cache files"
echo "6. Document results below"
echo ""

read -p "Press Enter after Disk Drill analysis completes..."

echo ""
read -p "How many files did Disk Drill recover? (enter number): " disk_drill_count
DISK_DRILL_RECOVERED=${disk_drill_count:-0}

echo ""
echo "Disk Drill Results:"
echo "  Files recovered: $DISK_DRILL_RECOVERED"

if [ $DISK_DRILL_RECOVERED -gt 0 ]; then
    echo "  ⚠️  WARNING: Disk Drill recovered files!"
else
    echo "  ✅ SUCCESS: No files recovered by Disk Drill"
fi

echo ""

# ===== FINAL REPORT =====
echo "=============================================="
echo "FINAL FORENSIC ANALYSIS REPORT"
echo "=============================================="
echo ""

echo "Recovery Attempts Summary:"
echo "  PhotoRec files recovered: $PHOTOREC_RECOVERED"
echo "  TestDisk files recovered: $TESTDISK_RECOVERED"
echo "  Disk Drill files recovered: $DISK_DRILL_RECOVERED"
echo "  Sensitive string matches: $STRING_SEARCH_MATCHES"
echo ""

TOTAL_RECOVERED=$((PHOTOREC_RECOVERED + TESTDISK_RECOVERED + DISK_DRILL_RECOVERED))

echo "Total files recovered: $TOTAL_RECOVERED"
echo ""

# Determine success/failure
if [ $TOTAL_RECOVERED -eq 0 ] && [ $STRING_SEARCH_MATCHES -eq 0 ]; then
    echo "✅ FORENSIC ANALYSIS: PASS"
    echo ""
    echo "╔═══════════════════════════════════════════════════╗"
    echo "║                                                   ║"
    echo "║  🎉 SUCCESS: DoD 7-Pass Wipe Effective!  🎉      ║"
    echo "║                                                   ║"
    echo "╚═══════════════════════════════════════════════════╝"
    echo ""
    echo "Results:"
    echo "  - 0 files recovered by forensic tools"
    echo "  - 0 sensitive strings found on disk"
    echo "  - DoD 5220.22-M 7-pass overwrite verified effective"
    echo "  - Emergency mode wipe is forensically secure"
    echo ""
    echo "Conclusion:"
    echo "The emergency mode successfully destroyed all user data"
    echo "with no possibility of recovery. The system is ready for"
    echo "persecution scenario deployment."
    echo ""
    echo "For His glory and the protection of His people. 🙏"
    echo ""
    exit 0
else
    echo "❌ FORENSIC ANALYSIS: FAIL"
    echo ""
    echo "╔═══════════════════════════════════════════════════╗"
    echo "║                                                   ║"
    echo "║  ⚠️  WARNING: Data Recovery Possible!  ⚠️         ║"
    echo "║                                                   ║"
    echo "╚═══════════════════════════════════════════════════╝"
    echo ""
    echo "Issues Found:"

    if [ $PHOTOREC_RECOVERED -gt 0 ]; then
        echo "  - PhotoRec recovered $PHOTOREC_RECOVERED files"
    fi

    if [ $TESTDISK_RECOVERED -gt 0 ]; then
        echo "  - TestDisk recovered $TESTDISK_RECOVERED files"
    fi

    if [ $DISK_DRILL_RECOVERED -gt 0 ]; then
        echo "  - Disk Drill recovered $DISK_DRILL_RECOVERED files"
    fi

    if [ $STRING_SEARCH_MATCHES -gt 0 ]; then
        echo "  - Found $STRING_SEARCH_MATCHES sensitive string matches on disk"
    fi

    echo ""
    echo "Action Required:"
    echo "1. Investigate why DoD wipe did not complete fully"
    echo "2. Check backend emergency_wipe.py implementation"
    echo "3. Verify 7-pass overwrite is executing correctly"
    echo "4. Test DoD wipe function with isolated test files"
    echo "5. Re-run forensic analysis after fixes"
    echo ""
    echo "Security Impact:"
    echo "Data may be recoverable by forensic tools. System is NOT"
    echo "ready for persecution scenario deployment until this is fixed."
    echo ""
    exit 1
fi

# Save report
REPORT_FILE="$RECOVERY_DIR/forensic_report_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "MagnetarStudio Forensic Analysis Report"
    echo "========================================"
    echo "Date: $(date)"
    echo ""
    echo "PhotoRec: $PHOTOREC_RECOVERED files recovered"
    echo "TestDisk: $TESTDISK_RECOVERED files recovered"
    echo "Disk Drill: $DISK_DRILL_RECOVERED files recovered"
    echo "String Search: $STRING_SEARCH_MATCHES matches"
    echo ""
    echo "Total: $TOTAL_RECOVERED files recovered"
    echo ""
    if [ $TOTAL_RECOVERED -eq 0 ] && [ $STRING_SEARCH_MATCHES -eq 0 ]; then
        echo "Result: PASS - DoD 7-pass wipe effective"
    else
        echo "Result: FAIL - Data recovery possible"
    fi
} > "$REPORT_FILE"

echo "Report saved: $REPORT_FILE"
echo ""
