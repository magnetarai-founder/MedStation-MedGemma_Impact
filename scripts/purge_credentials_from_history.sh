#!/bin/bash
#
# Purge Credentials from Git History
#
# This script removes hardcoded credentials from the entire git history
# using BFG Repo-Cleaner, a faster alternative to git-filter-branch.
#
# ⚠️  WARNING: This rewrites git history! All team members must re-clone.
#
# Usage:
#   1. Backup your repository first!
#   2. Ensure all changes are committed
#   3. Run: ./scripts/purge_credentials_from_history.sh
#   4. Force push: git push --force --all
#   5. Team re-clones the repository
#

set -e  # Exit on error

echo "======================================"
echo "Git Credential History Purge Script"
echo "======================================"
echo ""

# Check we're in a git repo
if [ ! -d .git ]; then
    echo "❌ Error: Not in a git repository root"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "❌ Error: You have uncommitted changes"
    echo "Please commit or stash changes before running this script"
    exit 1
fi

# Create backup
BACKUP_DIR="../MagnetarStudio_backup_$(date +%Y%m%d_%H%M%S)"
echo "📦 Creating backup at: $BACKUP_DIR"
cd ..
cp -R MagnetarStudio "$BACKUP_DIR"
cd MagnetarStudio
echo "✅ Backup created"
echo ""

# Check if BFG is installed
if ! command -v bfg &> /dev/null; then
    echo "📥 BFG Repo-Cleaner not found. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install bfg
    else
        echo "❌ Error: Homebrew not found. Please install BFG manually:"
        echo "   https://rtyley.github.io/bfg-repo-cleaner/"
        exit 1
    fi
fi

# Create credentials file to purge
CREDS_FILE=$(mktemp)
cat > "$CREDS_FILE" << 'EOF'
Jesus33
ELOHIM_FOUNDER_PASSWORD=Jesus33
8ae2ec5497cff953d881ac5b9f948ecacbb02e165396fdcd1ce9ac26b1ab7d00
ELOHIMOS_JWT_SECRET_KEY=8ae2ec5497cff953d881ac5b9f948ecacbb02e165396fdcd1ce9ac26b1ab7d00
JWT_SECRET=hardcoded-secret-12345
DB_ENCRYPTION_KEY=static-key-67890
OLLAMA_API_KEY=exposed-api-key
EOF

echo "🔍 Credentials to purge:"
cat "$CREDS_FILE"
echo ""

# Run BFG to replace credentials
echo "🧹 Running BFG Repo-Cleaner to purge credentials..."
bfg --replace-text "$CREDS_FILE" --no-blob-protection

# Clean up the credentials file
rm "$CREDS_FILE"

# Expire reflog and gc
echo "🗑️  Expiring reflog and running garbage collection..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "✅ Credentials purged from git history!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "1. Review the changes: git log --all --oneline"
echo "2. Force push to remote: git push --force --all"
echo "3. Force push tags: git push --force --tags"
echo "4. Notify team to re-clone repository"
echo "5. Team should run: rm -rf MagnetarStudio && git clone <repo-url>"
echo ""
echo "Backup location: $BACKUP_DIR"
