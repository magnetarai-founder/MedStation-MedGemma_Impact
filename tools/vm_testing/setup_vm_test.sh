#!/bin/bash
# setup_vm_test.sh
# MagnetarStudio VM Testing Environment Setup
#
# Purpose: Populate VM with fake sensitive data for emergency mode testing
# Usage: ./setup_vm_test.sh
# Safety: Only run in isolated VMs, never on production or development machines
#
# For His glory and the protection of His people. 🙏

set -e  # Exit on error

echo "🔧 MagnetarStudio VM Test Environment Setup"
echo "==========================================="
echo ""

# Safety check: Verify this is a VM
echo "⚠️  SAFETY CHECK: This script should ONLY run in VMs"
read -p "Are you running this in an isolated VM? (yes/no): " vm_confirm
if [ "$vm_confirm" != "yes" ]; then
    echo "❌ Aborted: Safety confirmation failed"
    exit 1
fi

echo ""
echo "✅ Safety confirmation received"
echo ""

# Create directories
echo "📁 Creating test directories..."

mkdir -p ~/.magnetar
mkdir -p ~/.magnetar/models
mkdir -p ~/.magnetar/model_cache
mkdir -p ~/.elohimos_backups
mkdir -p ~/Library/Caches/com.magnetarstudio.app
mkdir -p ~/Library/Application\ Support/MagnetarStudio
mkdir -p ~/Library/Logs/MagnetarStudio

echo "   ✅ Created 7 test directories"
echo ""

# Create fake vault databases
echo "🔐 Creating fake vault databases..."

cat > ~/.magnetar/vault_sensitive.db << EOF
FAKE SENSITIVE DATA - VM TEST
=============================
This is simulated sensitive data for testing emergency mode.

User: test_user@example.com
Password: REDACTED_TEST_PASSWORD
API Key: sk-test-1234567890abcdef
Vault Passphrase: SENSITIVE_VAULT_KEY_12345

DO NOT use this on real systems.
EOF

cat > ~/.magnetar/vault_unsensitive.db << EOF
FAKE UNSENSITIVE DATA - VM TEST
================================
This is simulated metadata for testing.

Created: $(date)
Version: 1.0.0-test
EOF

cat > ~/.magnetar/app.db << EOF
FAKE APP DATABASE - VM TEST
============================
User preferences and application state.

Theme: dark
Language: en
Last Login: $(date)
EOF

echo "   ✅ Created 3 vault databases"
echo ""

# Create fake model files
echo "🤖 Creating fake model files..."

# Create 100MB fake model file
dd if=/dev/urandom of=~/.magnetar/models/llama-3.2-3b-test.gguf bs=1M count=100 2>/dev/null

# Create smaller test models
dd if=/dev/urandom of=~/.magnetar/models/embedding-model-test.gguf bs=1M count=10 2>/dev/null
dd if=/dev/urandom of=~/.magnetar/models/whisper-test.gguf bs=1M count=50 2>/dev/null

echo "   ✅ Created 3 model files (~160MB total)"
echo ""

# Create fake model cache
echo "💾 Creating fake model cache..."

mkdir -p ~/.magnetar/model_cache/llama
mkdir -p ~/.magnetar/model_cache/embeddings

dd if=/dev/urandom of=~/.magnetar/model_cache/llama/cache_001.bin bs=1M count=5 2>/dev/null
dd if=/dev/urandom of=~/.magnetar/model_cache/embeddings/cache_002.bin bs=1M count=2 2>/dev/null

echo "   ✅ Created model cache (~7MB)"
echo ""

# Create fake backups
echo "📦 Creating fake encrypted backups..."

cat > ~/.elohimos_backups/backup_$(date +%Y%m%d).tar.gz.enc << EOF
FAKE ENCRYPTED BACKUP - VM TEST
================================
This simulates an encrypted backup file.

Encryption: AES-256-GCM
Key Derivation: PBKDF2
Salt: $(openssl rand -hex 16)
IV: $(openssl rand -hex 12)

[ENCRYPTED PAYLOAD WOULD GO HERE]
EOF

cat > ~/.elohimos_backups/backup_$(date -v-7d +%Y%m%d).tar.gz.enc << EOF
FAKE OLD BACKUP - VM TEST
=========================
Simulated week-old backup.

Encryption: AES-256-GCM
Created: $(date -v-7d)
Size: 250MB (fake)
EOF

echo "   ✅ Created 2 encrypted backups"
echo ""

# Create fake cache files
echo "🗃️  Creating fake cache files..."

mkdir -p ~/Library/Caches/com.magnetarstudio.app/api_responses
mkdir -p ~/Library/Caches/com.magnetarstudio.app/thumbnails

# Create 50 fake API response cache files
for i in {1..50}; do
    echo "FAKE API RESPONSE $i - $(date)" > ~/Library/Caches/com.magnetarstudio.app/api_responses/response_$i.json
done

# Create 20 fake thumbnail files
for i in {1..20}; do
    dd if=/dev/urandom of=~/Library/Caches/com.magnetarstudio.app/thumbnails/thumb_$i.png bs=1K count=10 2>/dev/null
done

echo "   ✅ Created 70 cache files"
echo ""

# Create fake audit logs
echo "📝 Creating fake audit logs..."

cat > ~/.magnetar/audit.db << EOF
FAKE AUDIT LOG - VM TEST
========================
Timestamp: $(date)

[2025-12-01 10:00:00] User login: test_user@example.com
[2025-12-01 10:05:23] Vault unlocked
[2025-12-01 10:10:45] Document accessed: sensitive_doc_001.txt
[2025-12-01 10:15:12] API call: GET /api/v1/documents
[2025-12-01 10:20:34] Vault locked
[2025-12-01 10:25:56] User logout

Total entries: 1000+
EOF

echo "   ✅ Created audit log"
echo ""

# Create fake Application Support files
echo "🗂️  Creating fake Application Support files..."

mkdir -p ~/Library/Application\ Support/MagnetarStudio/user_data
mkdir -p ~/Library/Application\ Support/MagnetarStudio/plugins

cat > ~/Library/Application\ Support/MagnetarStudio/config.json << EOF
{
  "version": "1.0.0-test",
  "user_id": "test-user-12345",
  "api_endpoint": "https://api.magnetarstudio.test",
  "vault_enabled": true,
  "theme": "dark",
  "language": "en"
}
EOF

echo "FAKE USER DATA" > ~/Library/Application\ Support/MagnetarStudio/user_data/preferences.dat

echo "   ✅ Created Application Support files"
echo ""

# Create fake log files
echo "📄 Creating fake log files..."

cat > ~/Library/Logs/MagnetarStudio/app.log << EOF
FAKE APPLICATION LOG - VM TEST
==============================
$(date): App started
$(date): Vault service initialized
$(date): Auth service connected
$(date): User logged in: test_user@example.com
$(date): Document sync started
$(date): Network request: GET /api/v1/health
$(date): Cache cleared: 150MB freed

[LOG CONTINUES FOR 1000+ LINES]
EOF

cat > ~/Library/Logs/MagnetarStudio/error.log << EOF
FAKE ERROR LOG - VM TEST
========================
$(date): Warning: Network latency high (250ms)
$(date): Error: Failed to connect to sync service (retry 1/3)
$(date): Warning: Disk space low (1.2GB remaining)

[ERROR LOG CONTINUES]
EOF

echo "   ✅ Created log files"
echo ""

# Create fake preferences
echo "⚙️  Creating fake preferences..."

cat > ~/Library/Preferences/com.magnetarstudio.app.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>SUEnableAutomaticChecks</key>
    <true/>
    <key>SUHasLaunchedBefore</key>
    <true/>
    <key>LastLogin</key>
    <string>$(date)</string>
    <key>UserId</key>
    <string>test-user-12345</string>
</dict>
</plist>
EOF

echo "   ✅ Created preferences plist"
echo ""

# Create fake LaunchAgents
echo "🚀 Creating fake LaunchAgents..."

mkdir -p ~/Library/LaunchAgents

cat > ~/Library/LaunchAgents/com.magnetarstudio.helper.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.magnetarstudio.helper</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/MagnetarStudio.app/Contents/MacOS/MagnetarHelper</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

echo "   ✅ Created LaunchAgent"
echo ""

# Create fake temporary files
echo "🗑️  Creating fake temporary files..."

mkdir -p /tmp/magnetar_temp

for i in {1..10}; do
    echo "FAKE TEMP FILE $i - $(date)" > /tmp/magnetar_temp/temp_$i.tmp
done

echo "   ✅ Created 10 temporary files"
echo ""

# Generate checksums for forensic comparison
echo "🔬 Generating pre-wipe checksums..."

CHECKSUM_FILE="/tmp/pre_wipe_checksums.txt"
rm -f "$CHECKSUM_FILE"

echo "# Pre-Wipe File Checksums - Generated $(date)" > "$CHECKSUM_FILE"
echo "# These checksums will be used for forensic analysis" >> "$CHECKSUM_FILE"
echo "" >> "$CHECKSUM_FILE"

find ~/.magnetar -type f -exec shasum -a 256 {} \; >> "$CHECKSUM_FILE" 2>/dev/null
find ~/.elohimos_backups -type f -exec shasum -a 256 {} \; >> "$CHECKSUM_FILE" 2>/dev/null
find ~/Library/Caches/com.magnetarstudio.app -type f -exec shasum -a 256 {} \; >> "$CHECKSUM_FILE" 2>/dev/null
find ~/Library/Application\ Support/MagnetarStudio -type f -exec shasum -a 256 {} \; >> "$CHECKSUM_FILE" 2>/dev/null
find ~/Library/Logs/MagnetarStudio -type f -exec shasum -a 256 {} \; >> "$CHECKSUM_FILE" 2>/dev/null

echo "   ✅ Checksums saved to $CHECKSUM_FILE"
echo ""

# Generate file count report
echo "📊 Generating file count report..."

echo ""
echo "========================================="
echo "VM Test Environment Summary"
echo "========================================="
echo ""

echo "Directories Created:"
echo "  - ~/.magnetar"
echo "  - ~/.magnetar/models"
echo "  - ~/.magnetar/model_cache"
echo "  - ~/.elohimos_backups"
echo "  - ~/Library/Caches/com.magnetarstudio.app"
echo "  - ~/Library/Application Support/MagnetarStudio"
echo "  - ~/Library/Logs/MagnetarStudio"
echo "  - /tmp/magnetar_temp"
echo ""

echo "Files Created:"
VAULT_COUNT=$(find ~/.magnetar -type f 2>/dev/null | wc -l | tr -d ' ')
BACKUP_COUNT=$(find ~/.elohimos_backups -type f 2>/dev/null | wc -l | tr -d ' ')
CACHE_COUNT=$(find ~/Library/Caches/com.magnetarstudio.app -type f 2>/dev/null | wc -l | tr -d ' ')
SUPPORT_COUNT=$(find ~/Library/Application\ Support/MagnetarStudio -type f 2>/dev/null | wc -l | tr -d ' ')
LOG_COUNT=$(find ~/Library/Logs/MagnetarStudio -type f 2>/dev/null | wc -l | tr -d ' ')
TEMP_COUNT=$(find /tmp/magnetar_temp -type f 2>/dev/null | wc -l | tr -d ' ')
PLIST_COUNT=2  # Preferences + LaunchAgent

TOTAL_FILES=$((VAULT_COUNT + BACKUP_COUNT + CACHE_COUNT + SUPPORT_COUNT + LOG_COUNT + TEMP_COUNT + PLIST_COUNT))

echo "  - Vault files: $VAULT_COUNT"
echo "  - Backup files: $BACKUP_COUNT"
echo "  - Cache files: $CACHE_COUNT"
echo "  - Application Support files: $SUPPORT_COUNT"
echo "  - Log files: $LOG_COUNT"
echo "  - Temporary files: $TEMP_COUNT"
echo "  - Preferences/LaunchAgents: $PLIST_COUNT"
echo ""
echo "  Total files: $TOTAL_FILES"
echo ""

# Calculate disk usage
DISK_USAGE=$(du -sh ~/.magnetar ~/.elohimos_backups ~/Library/Caches/com.magnetarstudio.app ~/Library/Application\ Support/MagnetarStudio ~/Library/Logs/MagnetarStudio /tmp/magnetar_temp 2>/dev/null | awk '{s+=$1} END {print s}')

echo "Disk Usage:"
echo "  - ~/.magnetar: $(du -sh ~/.magnetar 2>/dev/null | awk '{print $1}')"
echo "  - ~/.elohimos_backups: $(du -sh ~/.elohimos_backups 2>/dev/null | awk '{print $1}')"
echo "  - Caches: $(du -sh ~/Library/Caches/com.magnetarstudio.app 2>/dev/null | awk '{print $1}')"
echo "  - Application Support: $(du -sh ~/Library/Application\ Support/MagnetarStudio 2>/dev/null | awk '{print $1}')"
echo "  - Logs: $(du -sh ~/Library/Logs/MagnetarStudio 2>/dev/null | awk '{print $1}')"
echo "  - Temporary: $(du -sh /tmp/magnetar_temp 2>/dev/null | awk '{print $1}')"
echo ""

echo "========================================="
echo "✅ VM Test Environment Setup Complete!"
echo "========================================="
echo ""
echo "Next Steps:"
echo "1. Install/build MagnetarStudio in this VM"
echo "2. Run emergency mode test"
echo "3. Use verify_wipe.sh to check results"
echo ""
echo "Checksum file: $CHECKSUM_FILE"
echo "Total test files: $TOTAL_FILES"
echo ""
echo "For His glory and the protection of His people. 🙏"
