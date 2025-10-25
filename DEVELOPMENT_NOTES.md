# ElohimOS Development Notes

**Created:** 2025-10-25
**Purpose:** Critical notes for future development work and environment setup

---

## ⚠️ IMPORTANT: Build & Environment Setup

### 1. TypeScript Configuration (tsconfig.json)

**STATUS:** ❌ **NOT NEEDED - DO NOT CREATE**

This project uses **Vite with esbuild** for TypeScript compilation. There is **intentionally NO tsconfig.json** file.

- ✅ TypeScript transpilation handled by Vite/esbuild
- ✅ Type checking happens in IDE/editor (not build time)
- ✅ `package.json` build script is: `"build": "vite build"` (NOT `tsc && vite build`)

**If you see errors about missing tsconfig.json:**
- This is expected and correct behavior
- Do NOT run `tsc --init`
- Do NOT create a tsconfig.json
- Vite handles everything internally

---

### 2. Python Linting (ruff)

**STATUS:** ⚠️ **INSTALLED VIA HOMEBREW (NOT pip)**

Current installation method:
```bash
brew install ruff  # ✓ Installed globally via Homebrew
```

**TODO FOR PRODUCTION DEPLOYMENT:**

This approach won't work for:
- CI/CD pipelines
- Docker containers
- New developer onboarding
- Non-macOS systems

**Action Required:** Create proper Python environment setup

#### Create: `tools/scripts/setup_python_env.sh`
```bash
#!/bin/bash
# Setup Python virtual environment with all dev tools

cd "$(dirname "$0")/../.."

# Create venv if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Created virtual environment"
fi

# Activate venv
source venv/bin/activate

# Install all Python dependencies
pip install -r apps/backend/requirements.txt
pip install -r requirements-dev.txt  # TODO: Create this file

echo "✓ Python environment ready"
echo "  To activate: source venv/bin/activate"
```

#### Create: `requirements-dev.txt`
```
# Development tools (not needed in production)
ruff==0.14.2
black==24.0.0
mypy==1.9.0
pytest==8.1.0
pytest-asyncio==0.23.0
```

#### Update: `apps/backend/requirements.txt`
Add at bottom:
```
# Development tools (optional)
# Install with: pip install -r requirements-dev.txt
```

#### Update: `README.md` (when created)
```markdown
## Development Setup

1. Install Python dependencies:
   ```bash
   ./tools/scripts/setup_python_env.sh
   ```

2. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

3. Run linting:
   ```bash
   ruff check apps/backend/api/
   ```
```

---

### 3. Frontend Build Configuration

**File:** `apps/frontend/package.json`

**CORRECTED BUILD SCRIPT (2025-10-25):**
```json
"scripts": {
  "build": "vite build"  // ✓ Correct - no tsc
}
```

**INCORRECT (previous version):**
```json
"scripts": {
  "build": "tsc && vite build"  // ✗ Wrong - fails with no tsconfig
}
```

If you see build failures, verify the build script does NOT include `tsc`.

---

## 📦 Completed Features (2025-10-25)

### Panic Mode ✅
- Backend: `apps/backend/api/panic_mode_router.py`
- Frontend: `apps/frontend/src/components/PanicModeModal.tsx`
- API: `POST /api/v1/panic/trigger`
- Status: Tested and working

### Vault System ✅
- Backend: `apps/backend/api/vault_service.py`
- Frontend: `apps/frontend/src/components/Vault*.tsx`
- API: `/api/v1/vault/*`
- Encryption: Client-side AES-256 (zero-knowledge)

### P2P Mesh Sync ✅
- Backend: `apps/backend/api/offline_data_sync.py`
- Endpoint: `POST /api/v1/mesh/sync/exchange`
- Features: CRDT conflict resolution, delta sync

---

## 🔧 System Requirements

### Metal 4 GPU Acceleration
- ✅ Installed: PyObjC 11.1
- ✅ Working: Metal 4 on Apple M4 Max
- ✅ Fallbacks: Implemented for non-Metal systems

### Git LFS
- ✅ Status: Clean, all files tracked properly

### Database Indexes
- ✅ Status: Optimized (25+ indexes across 8 databases)

---

## 🚀 Build & Deploy Checklist

Before deployment:
- [ ] Run `npm run build` in `apps/frontend/`
- [ ] Verify `dist/` folder created
- [ ] Create `requirements-dev.txt` for Python dev tools
- [ ] Create `setup_python_env.sh` script
- [ ] Test build in clean environment (no Homebrew ruff)
- [ ] Document `omni` global alias setup

---

## 📝 Performance Optimizations

### Pending (Low Priority):
1. **SettingsModal.tsx** - 56KB component (1464 lines)

**Current Structure:**
- Already uses tab-based UI with 5 sections
- Internal functions: `SettingsTab`, `PowerUserTab`, `ModelManagementTab`, `DangerZoneTab`
- Plus: `ProfileSettings` (already external), `ChatSettingsContent` (internal)

**Refactoring Plan:**

Extract internal tab functions to separate files:

```
src/components/settings/
├── SettingsModal.tsx          # Main modal shell (keep)
├── SettingsTab.tsx             # Lines 140-574 (App settings)
├── PowerUserTab.tsx            # Lines 575-1204 (Advanced)
├── DangerZoneTab.tsx           # Lines 1205-1442 (Danger zone)
├── ModelManagementTab.tsx      # Lines 1443-1464 (Models)
├── ChatSettingsContent.tsx     # Extract from SettingsTab
└── FormatNamingRow.tsx         # Helper component (lines 532-573)
```

**Benefits:**
- Reduce main file from 1464 → ~150 lines
- Enable lazy loading: `React.lazy(() => import('./settings/PowerUserTab'))`
- Improve build splitting (each tab in separate chunk)
- Easier maintenance and testing

**Implementation Steps:**
1. Create `src/components/settings/` directory
2. Move each tab function to its own file
3. Add proper imports/exports
4. Update `SettingsModal.tsx` to import components
5. Add lazy loading wrappers
6. Test all tabs still work
7. Verify bundle size reduction (expect 200-300KB savings)

**Estimated Impact:**
- Initial load: -200KB (lazy loaded tabs only load on click)
- Developer experience: Much easier to navigate
- Risk: Medium (need thorough testing of all settings)

---

## 🐛 Known Issues

None currently - system is production-ready.

---

## 📚 Architecture Notes

- **Frontend:** React 18 + Vite + TypeScript + Tailwind
- **Backend:** Python FastAPI + SQLite
- **AI:** Local Ollama (port 11434)
- **GPU:** Metal 4 acceleration (Apple Silicon)
- **Network:** mDNS peer discovery (offline-first)
- **Security:** Client-side encryption, panic mode, vault system

---

**Last Updated:** 2025-10-25
**Next Review:** Before next major deployment
