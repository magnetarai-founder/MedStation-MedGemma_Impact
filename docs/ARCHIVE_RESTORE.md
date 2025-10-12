# 📦 Archive & Restore Guide

## 🎯 Quick Reference

### Current Archive Points

| Tag | Description | Date | Features |
|-----|-------------|------|----------|
| `v1.0-sql-json-baseline` | **Clean baseline before Chat UI** | 2025-09-30 | SQL + JSON tabs working, Chat backend ready |

---

## 🔄 How to Restore Archive

### Option 1: Quick Restore (Recommended)
Restore to the clean baseline instantly:

```bash
cd /Users/indiedevhipps/Documents/NeutronStar-React_Front

# Save current work (if needed)
git stash

# Restore to clean baseline
git checkout v1.0-sql-json-baseline

# Create new branch from this point
git checkout -b my-new-feature
```

### Option 2: View Archive Code
Look at the archive without changing your current state:

```bash
# View specific file from archive
git show v1.0-sql-json-baseline:api/main.py

# Browse entire archive
git checkout v1.0-sql-json-baseline --detach
# (Look around, then: git checkout main)
```

### Option 3: Copy Files from Archive
Extract specific files from the archive:

```bash
# Copy a file from archive to current directory
git show v1.0-sql-json-baseline:api/chat_service.py > api/chat_service_clean.py

# Restore specific file from archive
git checkout v1.0-sql-json-baseline -- api/chat_service.py
```

---

## 🆕 New GitHub Repo Setup

### Recommended: Create New Repo for Chat Feature

```bash
# 1. Create new repo on GitHub (neutron-star-chat)

# 2. Clone the archive as base
cd /Users/indiedevhipps/Documents
git clone NeutronStar-React_Front NeutronStar-Chat
cd NeutronStar-Chat

# 3. Reset to clean baseline
git checkout v1.0-sql-json-baseline
git checkout -b main

# 4. Point to new remote
git remote remove origin
git remote add origin https://github.com/yourusername/neutron-star-chat.git

# 5. Push clean baseline
git push -u origin main --tags
```

### Alternative: Keep Everything in One Repo with Branches

```bash
# Create chat feature branch from baseline
git checkout v1.0-sql-json-baseline
git checkout -b feature/chat-ui

# Work on chat UI...
git add .
git commit -m "Add chat UI"

# When ready, merge to main
git checkout main
git merge feature/chat-ui
```

---

## 📸 What's in the Archive

### ✅ Baseline (v1.0-sql-json-baseline)

**Working Features:**
- SQL Editor tab (DuckDB queries)
- JSON tab (Pulsar conversion)
- File upload/processing
- Results table with export
- Settings modal
- Navigation rail

**Chat Backend (API only, no UI):**
- Complete REST API (`api/chat_service.py`)
- Ollama integration
- Streaming responses
- Multi-session support
- File upload endpoint
- JSONL storage
- Test script

**Files Added:**
- `api/chat_service.py` - Chat service
- `CHAT_API.md` - API docs
- `BACKEND_COMPLETE.md` - Summary
- `test_chat_api.sh` - Test script

**Modified:**
- `api/main.py` - Includes chat router
- `backend_requirements.txt` - Added httpx
- `start_web.sh` - Python 3.12 fix
- `requirements.txt` - Updated pyarrow

---

## 🔍 Compare Changes

### See what changed since archive:
```bash
git diff v1.0-sql-json-baseline..HEAD
```

### See file list that changed:
```bash
git diff v1.0-sql-json-baseline..HEAD --name-only
```

### See only frontend changes:
```bash
git diff v1.0-sql-json-baseline..HEAD -- frontend/
```

---

## 🚨 Emergency Rollback

If something breaks and you need to go back:

```bash
# Nuclear option: Hard reset to baseline
git reset --hard v1.0-sql-json-baseline

# Safer: Create rollback branch
git branch backup-before-rollback
git reset --hard v1.0-sql-json-baseline
```

---

## 📋 Commit Message from Archive

```
Archive: Pre-Chat-UI baseline (SQL+JSON working)

✅ Working Features:
- SQL Editor with DuckDB engine
- JSON to Excel conversion (Pulsar)
- File upload and processing
- Results table with export
- Navigation rail (SQL/JSON tabs)

🆕 Chat Backend Added (Not in UI yet):
- Complete Chat API service
- Ollama integration
- Streaming SSE responses
- Multi-session support
- File attachments
- JSONL storage

📍 Archive Point: Before building Chat UI
This commit represents the last known good state before
adding Chat tab to frontend. Easy rollback point.
```

---

## 🎯 Next Steps After Restore

After restoring to baseline, you can:

1. **Start fresh with Chat UI** - Build frontend from clean state
2. **Cherry-pick specific commits** - `git cherry-pick <commit>`
3. **Create experimental branch** - `git checkout -b experiment`
4. **Compare implementations** - `git diff v1.0-sql-json-baseline feature-branch`

---

## 📞 Quick Commands Reference

| Action | Command |
|--------|---------|
| List all tags | `git tag -l` |
| View tag details | `git show v1.0-sql-json-baseline` |
| Restore to tag | `git checkout v1.0-sql-json-baseline` |
| Create branch from tag | `git checkout -b new-branch v1.0-sql-json-baseline` |
| Delete local tag | `git tag -d v1.0-sql-json-baseline` |
| Push tags to remote | `git push origin --tags` |

---

## 💡 Pro Tips

1. **Always create branch from archive** - Never work directly on detached HEAD
2. **Tag early, tag often** - Create tags before risky changes
3. **Descriptive tag names** - Use semantic versioning or dates
4. **Push tags to backup** - `git push origin --tags` (after creating new repo)

---

## 🔗 Related Files

- `BACKEND_COMPLETE.md` - Chat backend summary
- `CHAT_API.md` - API documentation
- `test_chat_api.sh` - Backend test script

---

**Archive created:** 2025-09-30
**Last updated:** 2025-09-30
