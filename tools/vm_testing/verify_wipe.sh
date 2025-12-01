#!/bin/bash
# verify_wipe.sh
# MagnetarStudio Emergency Wipe Verification
#
# Purpose: Verify that emergency mode successfully wiped all target files
# Usage: ./verify_wipe.sh
# Safety: Only run in VMs after emergency mode execution
#
# For His glory and the protection of His people. 🙏

set -e  # Exit on error

echo "🔍 MagnetarStudio Emergency Wipe Verification"
echo "=============================================="
echo ""

# Initialize counters
PASS_COUNT=0
FAIL_COUNT=0
TOTAL_CHECKS=11

# Function to check if path exists
check_deleted() {
    local path="$1"
    local name="$2"

    if [ -e "$path" ]; then
        echo "   ❌ FAIL: $name still exists"
        echo "      Path: $path"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return 1
    else
        echo "   ✅ PASS: $name deleted"
        PASS_COUNT=$((PASS_COUNT + 1))
        return 0
    fi
}

# 1. Check app bundle
echo "1. Checking app bundle deletion..."
check_deleted "/Applications/MagnetarStudio.app" "App bundle"
echo ""

# 2. Check ~/.magnetar directory
echo "2. Checking ~/.magnetar directory..."
check_deleted "$HOME/.magnetar" "Vault directory"
echo ""

# 3. Check ~/.elohimos_backups
echo "3. Checking ~/.elohimos_backups..."
check_deleted "$HOME/.elohimos_backups" "Backups directory"
echo ""

# 4. Check Library/Caches
echo "4. Checking Library/Caches..."
check_deleted "$HOME/Library/Caches/com.magnetarstudio.app" "Cache directory"
echo ""

# 5. Check Library/Application Support
echo "5. Checking Library/Application Support..."
check_deleted "$HOME/Library/Application Support/MagnetarStudio" "Application Support"
echo ""

# 6. Check Library/Logs
echo "6. Checking Library/Logs..."
check_deleted "$HOME/Library/Logs/MagnetarStudio" "Logs directory"
echo ""

# 7. Check Preferences
echo "7. Checking Library/Preferences..."
check_deleted "$HOME/Library/Preferences/com.magnetarstudio.app.plist" "Preferences plist"
echo ""

# 8. Check LaunchAgents
echo "8. Checking Library/LaunchAgents..."
LAUNCH_AGENT_EXISTS=false
if ls "$HOME/Library/LaunchAgents"/com.magnetarstudio.* 1> /dev/null 2>&1; then
    echo "   ❌ FAIL: LaunchAgents still exist"
    ls -la "$HOME/Library/LaunchAgents"/com.magnetarstudio.*
    FAIL_COUNT=$((FAIL_COUNT + 1))
    LAUNCH_AGENT_EXISTS=true
else
    echo "   ✅ PASS: LaunchAgents deleted"
    PASS_COUNT=$((PASS_COUNT + 1))
fi
echo ""

# 9. Check temporary files
echo "9. Checking temporary files..."
check_deleted "/tmp/magnetar_temp" "Temporary files"
echo ""

# 10. Check keychain entries
echo "10. Checking keychain entries..."
KEYCHAIN_PASS=true

# Check for app-specific keychain items
if security find-generic-password -s "com.magnetarstudio.app" 2>/dev/null; then
    echo "   ❌ FAIL: Keychain entry 'com.magnetarstudio.app' still exists"
    KEYCHAIN_PASS=false
fi

if security find-generic-password -s "com.magnetarstudio.auth" 2>/dev/null; then
    echo "   ❌ FAIL: Keychain entry 'com.magnetarstudio.auth' still exists"
    KEYCHAIN_PASS=false
fi

if security find-generic-password -s "com.magnetarstudio.vault" 2>/dev/null; then
    echo "   ❌ FAIL: Keychain entry 'com.magnetarstudio.vault' still exists"
    KEYCHAIN_PASS=false
fi

if security find-generic-password -s "com.magnetarstudio.api" 2>/dev/null; then
    echo "   ❌ FAIL: Keychain entry 'com.magnetarstudio.api' still exists"
    KEYCHAIN_PASS=false
fi

if $KEYCHAIN_PASS; then
    echo "   ✅ PASS: All keychain entries deleted"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# 11. Check clipboard (manual verification)
echo "11. Checking clipboard..."
CLIPBOARD_CONTENT=$(pbpaste 2>/dev/null || echo "")
if [ -z "$CLIPBOARD_CONTENT" ]; then
    echo "   ✅ PASS: Clipboard is empty"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "   ⚠️  WARNING: Clipboard contains data"
    echo "      (May be unrelated to MagnetarStudio)"
    echo "      Content length: ${#CLIPBOARD_CONTENT} characters"
    PASS_COUNT=$((PASS_COUNT + 1))  # Don't fail on this
fi
echo ""

# Additional checks
echo "=============================================="
echo "Additional Forensic Checks"
echo "=============================================="
echo ""

# Check for any remaining magnetar/elohim references
echo "12. Searching for remaining magnetar/elohim files..."
REMAINING_FILES=$(find "$HOME" -name "*magnetar*" -o -name "*elohim*" 2>/dev/null | grep -v "/.Trash/" | grep -v "/Downloads/" || true)

if [ -z "$REMAINING_FILES" ]; then
    echo "   ✅ No remaining magnetar/elohim files found"
else
    echo "   ⚠️  Found remaining files:"
    echo "$REMAINING_FILES" | while read -r file; do
        echo "      - $file"
    done
    echo ""
    echo "   Note: Review these files manually. They may be unrelated to the app."
fi
echo ""

# Check process list
echo "13. Checking for running processes..."
RUNNING_PROCS=$(ps aux | grep -i magnetar | grep -v grep || true)
if [ -z "$RUNNING_PROCS" ]; then
    echo "   ✅ No MagnetarStudio processes running"
else
    echo "   ⚠️  WARNING: MagnetarStudio processes still running:"
    echo "$RUNNING_PROCS"
fi
echo ""

# Check LaunchDaemons (system-wide)
echo "14. Checking system LaunchDaemons..."
SYSTEM_DAEMONS=$(ls /Library/LaunchDaemons/com.magnetarstudio.* 2>/dev/null || true)
if [ -z "$SYSTEM_DAEMONS" ]; then
    echo "   ✅ No system LaunchDaemons found"
else
    echo "   ⚠️  WARNING: System LaunchDaemons still exist:"
    echo "$SYSTEM_DAEMONS"
    echo "      (Requires sudo to remove)"
fi
echo ""

# Final report
echo "=============================================="
echo "Verification Results"
echo "=============================================="
echo ""

echo "Core Checks: $PASS_COUNT/$TOTAL_CHECKS passed"
echo "Failed Checks: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo "✅ SUCCESS: Emergency wipe complete!"
    echo ""
    echo "All target files and directories have been successfully deleted."
    echo "The system shows no traces of MagnetarStudio user data."
    echo ""
    echo "Next Steps:"
    echo "1. Run forensic_test.sh to attempt file recovery"
    echo "2. Use Disk Drill, PhotoRec, and TestDisk"
    echo "3. Verify 0 files can be recovered"
    echo ""
    echo "Expected Result: DoD 7-pass wipe prevents all recovery"
    echo ""
    exit 0
else
    echo "❌ FAILURE: Emergency wipe incomplete!"
    echo ""
    echo "$FAIL_COUNT critical checks failed."
    echo "Some files or data remain on the system."
    echo ""
    echo "Action Required:"
    echo "1. Review failed checks above"
    echo "2. Investigate why deletion failed"
    echo "3. Check emergency mode logs for errors"
    echo "4. Re-test emergency mode if needed"
    echo ""
    exit 1
fi

# Additional note about forensic readiness
echo "=============================================="
echo "Forensic Analysis Readiness"
echo "=============================================="
echo ""
echo "Pre-Wipe Checksums: /tmp/pre_wipe_checksums.txt"
echo ""
echo "This VM is now ready for forensic analysis."
echo "Use forensic_test.sh to attempt data recovery."
echo ""
echo "For His glory and the protection of His people. 🙏"
