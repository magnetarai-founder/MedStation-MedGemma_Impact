# 🚀 ElohimOS Master Implementation Plan

**Version:** 1.0
**Date:** October 26, 2025
**Goal:** Build production-ready offline-first AI workspace in 2-3 weeks

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements Summary (48 Questions)](#requirements-summary)
3. [Reusable Code Inventory](#reusable-code-inventory)
4. [Architecture Overview](#architecture-overview)
5. [Phase 1: Quick Wins (Days 1-3)](#phase-1-quick-wins)
6. [Phase 2: Medium Complexity (Days 4-8)](#phase-2-medium-complexity)
7. [Phase 3: Complex Features (Days 9-15)](#phase-3-complex-features)
8. [Phase 4: Future Roadmap](#phase-4-future-roadmap)
9. [Excel to DuckDB Formula Mapping](#excel-to-duckdb-mapping)
10. [Testing Strategy](#testing-strategy)
11. [Deployment Checklist](#deployment-checklist)

---

## Executive Summary

### Business Context
- **Company:** Magnetar AI LLC
- **ElohimOS:** Open-source, offline-first, free (solo/small teams/persecuted church)
- **MagnetarCloud:** Enterprise SaaS (launching parallel, this week)

### Target Users
1. Solo power users (developers, researchers)
2. Small teams (2-10 people, startups)
3. Persecuted churches (underground, hostile regions)
4. Missionaries/Clinics/Mission/Disaster Response (off-grid)

### Primary Use Case
Replace Claude for coding - become 100% self-sufficient for AI-powered development work using local Ollama models.

### Design Philosophy
- **Offline-first:** Everything works without internet
- **Security-first:** Zero telemetry, encrypted vault, plausible deniability
- **Clean codebase:** Integrate external code properly, maintain repo hygiene
- **Power user focused:** Terminal-first, keyboard shortcuts, fast workflows

---

## Requirements Summary

### 🔐 Vault - Encrypted Storage

**Q1-8 Summary:**
- All file types supported (no restrictions)
- 2GB file size limit per file
- Drag-and-drop upload UI
- Proton Drive-style folder hierarchy
- Proton Drive-style file preview (thumbnails, icons, metadata)
- Share to Team Chat with Touch ID + recipient-specific encryption
- Git-style version history (all file types)
- 30-day trash (ALL app deletions → Vault trash for security)

**Key Security Features:**
- Client-side AES-256-GCM encryption
- Zero-knowledge backend (server can't read contents)
- Plausible deniability (Real + Decoy vaults)
- Touch ID + Password authentication
- Vault files shared to chat use separate encryption per recipient

---

### 📄 Docs - Notion-Style Editor

**Q9-16 Summary:**
- All Notion slash commands (`/h1`, `/bullet`, `/todo`, `/code`, `/quote`, `/image`, `/table`, `/divider`, `/callout`)
- Popup menu with icons, arrow keys navigation
- Simple rich text (NO block-based dragging - keep it fast)
- Markdown auto-convert (`**bold**`, `*italic*`, `` `code` ``, `[link](url)`)
- @ mentions (like Quip)
- Comments with threads (like Google Docs/Quip)
- File locking + async sync (battery-friendly collaboration)
- Show "John is editing" status
- Conflict resolution via copies ("Doc (John's version)")

**NEW FEATURE - Threads Section:**
```
Team Chat Sidebar:
├── THREADS (new section at top)
│   ├── Chat Threads (conversations from channels)
│   └── Doc Threads (comments from collaborative docs)
├── CHANNELS
├── DIRECT MESSAGES
└── TEAM CHATS
```

---

### 📊 Sheets - SQL-Powered Spreadsheets

**Q17-20 Summary:**
- Formulas powered by existing DuckDB SQL engine (proven: 110k rows × 49 cols in 3 seconds)
- Excel → SQL translation using comprehensive mapping (see section 9)
- Support "the good 5%" of Excel formulas:
  - **Math/Agg:** SUM, AVERAGE, MIN, MAX, COUNT, COUNTA, ROUND, ROUNDUP, ROUNDDOWN
  - **Conditional:** IF, IFS, AND, OR, NOT, IFERROR
  - **Lookups:** XLOOKUP, INDEX, MATCH, VLOOKUP, HLOOKUP
  - **Text:** TRIM, LEN, LEFT, RIGHT, MID, UPPER, LOWER, PROPER, SUBSTITUTE, TEXTJOIN, CONCAT
  - **Dates:** TODAY, NOW, DATE, DATEDIF, EOMONTH, WORKDAY, NETWORKDAYS
  - **Dynamic Arrays:** UNIQUE, FILTER, SORT
  - **Helpers:** VALUE, TEXT, ISBLANK, ISNUMBER, ISTEXT
- Minimal UI + cell formatting (bold, colors, borders)
- Import: Excel (.xlsx, .xls, .xlsm), CSV
- Export: Excel, CSV

**ChatGPT Recommended Features (Ship First):**
1. Column ops: resize, freeze, hide, reorder
2. Sort & Filter (multi-column, saved views)
3. Find/Replace (regex, whole word, scoped to selection)
4. Data types & formats (text/num/date/bool, thousand sep, %)
5. Data validation (dropdowns, number ranges, regex)
6. Conditional formatting (color scales, rules)
7. Quick calc bar (sum/avg/min/max/count of selection)
8. Pivot-lite (group + aggregate + subtotals)
9. Named ranges & "Tables" (stable references)
10. Undo/redo + keyboard shortcuts (Excel-like)

**UX Sugar:**
- "Explain this cell" (show generated SQL)
- "Convert to SQL" (one-click to Database tab)
- "Join wizard" (visual XLOOKUP builder)
- Saved filters = shareable URLs
- Auto-complete for named ranges

---

### 🔬 Insights Lab - Voice Transcription + AI

**Q21-24 Summary:**
- Audio formats: m4a, mp3, wav, aiff (NO video)
- Whisper transcription (existing implementation)
- AI analysis generates:
  ```
  1. Organized Transcript (cleaned up version)
  2. Summary (TL;DR of key points)
  3. Action Items (extracted to-dos)
  ```
- **NEW:** "Continue in AI Chat" button
  - Shifts analysis into AI Chat tab
  - Auto-switches tabs
  - Preserves full context
  - 200k token window for deep work
- "Convert to Doc" button in BOTH Insights AND AI Chat
- Transcriptions are editable (user can fix errors)

---

### 📤 Team Chat - File Sharing

**Q25-28 Summary:**
- Supported types: Excel, CSV, PDF, images, audio (reuse existing infrastructure)
- 2GB file size limit (same as Vault)
- Preview: Icon + filename (simple, fast)
- Sync: Slack-style download button (on-demand, not auto)
- Files encrypted during P2P transfer (libp2p encryption)
- Vault files get extra encryption layer (recipient-specific vault keys)

**NEW FEATURE - Upload from Computer:**
```
Docs Tab → New Document dropdown:
├── 📄 Doc (blank)
├── 📊 Sheet (blank)
├── 💡 Insight (audio transcription)
├── ─────────────────
├── 📤 Upload from Computer  ← NEW!
    ├── Word (.docx, .doc) → converts to Doc
    ├── Excel (.xlsx, .csv) → converts to Sheet
    └── Choose destination:
        • Add to Docs (for collaboration)
        • Add to Vault (encrypted, private)
```

---

### 🔄 Export / Import

**Q29-32 Summary:**
- **Docs export:** Word (.docx, .doc), PDF, HTML, JSON, Markdown
- **Docs import:** Strip formatting (Quip-style clean import)
- **Sheets export:** Excel, CSV
- **Sheets import:** Excel, CSV (auto-create Sheet document)
- **Bulk operations:** Export all Docs/Sheets as zip (reuse template library zip function)
- **Share menu:** All options
  - Export → Send to Team Chat
  - Export → Add to Vault
  - Export → Save to Desktop

---

### 🌐 Collaboration & Networking

**Q33-36 Summary:**
- **Presence:** Just file lock status ("John is editing")
- **Version history:** Git-style (consistent across all file types)
- **P2P encryption:**
  - Standard files: libp2p transport encryption
  - Vault files: libp2p + recipient-specific vault encryption
- **Network status:** Show all of it
  - Connection quality (ping, bandwidth)
  - Sync status ("Syncing..." / "Synced")
  - Battery indicator when P2P active

---

### 🎨 UX & Design

**Q37-40 Summary:**
- **Design:** Keep Arc-inspired glass UI + cherry-pick best from Notion, Obsidian, Quip
- **Keyboard shortcuts:** Both modes - toggle in Settings: "Power User Mode"
- **iPad support:** Build with iPad in mind, ship Mac first, iPad companion app later
- **Offline-first:** Internet ONLY for:
  - Installing Ollama
  - Installing Python dependencies
  - App updates (optional, user-controlled)
  - MUST BE: Super limited, super protected, secure, explicit, minimal, auditable

---

### 💻 CODE Tab - Terminal + AI Coding Agent

**Q45-47 Summary:**
- **Philosophy:** Terminal-first ("if you want IDE, use VS Code")
- **Integration:** Option C - Best of Both Worlds
  - Codex CLI (terminal/execution/sandbox)
  - Continue (autocomplete, chat, edit, agent)
  - Both powered by local Ollama models
- **ALL features from both:**
  - Autocomplete (inline suggestions)
  - Chat (ask questions about code)
  - Refactoring (AI rewrites)
  - Code explanation
  - Generate tests
  - Fix bugs
  - Bash command assistance
  - Agent mode (autonomous coding)
  - Edit mode (inline modifications)
- **Vault access:** Yes, CAN save code to Vault if wanted (but not primary use case)
- **Target:** Power users who manage their own security

---

## Reusable Code Inventory

### 1. Codex (OpenAI's Agent)
**Location:** `/Users/indiedevhipps/Documents/codex-main`

**What we'll integrate:**
- Full Codex CLI (Rust + TypeScript)
- Terminal-based AI coding agent
- Sandbox & approval system
- Authentication patterns
- Custom prompts system
- Memory with AGENTS.md
- Non-interactive mode (`codex exec`)
- Model Context Protocol (MCP) support

**Integration approach:**
- Copy core functionality into `apps/backend/api/code_agent/`
- Adapt authentication to use ElohimOS auth
- Point to local Ollama instead of OpenAI API
- Maintain clean separation of concerns

---

### 2. Continue (Open-source AI Assistant)
**Location:** `/Users/indiedevhipps/Documents/continue-main`

**What we'll integrate:**
- Agent (development tasks)
- Chat (ask questions, clarify code)
- Edit (modify code inline)
- Autocomplete (inline suggestions)
- Full LLM integration layer (`core/llm/`)
- Ollama support (already built!)

**Key files to adapt:**
- `core/index.d.ts` - Full TypeScript API
- `core/llm/` - LLM abstraction layer
- `core/llm/llms/Ollama.ts` - Local model integration

**Integration approach:**
- Copy Continue's LLM layer into `apps/frontend/src/lib/continue/`
- Adapt for ElohimOS state management (Zustand)
- Create CODE tab component that wraps both Codex + Continue
- Maintain attribution and license compliance (Apache 2.0)

---

### 3. Jarvis Agent (Your Previous Project)
**Location:** `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent`

**What we'll reuse:**
- `codex_cli.py` - Codex wrapper (adapt for ElohimOS)
- `embedding_system.py` - RAG/vector embeddings (for Insights Lab)
- `rag_auto_ingest.py` - Auto-index documents (for search)
- `dev_assistant.py` - AI dev assistant patterns
- `planner.py` - Task planning logic
- `adaptive_router.py` - Smart routing

**Integration approach:**
- Port Python logic to TypeScript where needed
- Reuse RAG patterns for Insights AI analysis
- Adapt planner for CODE tab agent mode

---

### 4. Big Query (Your Data Engine)
**Location:** `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Big Query`

**What we'll reuse:**
- SQL execution patterns (proven: 110k rows × 49 cols in 3 seconds!)
- Excel/CSV import workflows (already in ElohimOS!)
- Enterprise data handling patterns
- Query optimization techniques

**Integration approach:**
- Already integrated! Just extend for Sheets formulas
- Add Excel → SQL translation layer
- Reuse existing DuckDB connection

---

## Architecture Overview

### Frontend Structure
```
apps/frontend/src/
├── components/
│   ├── CodeWorkspace.tsx         ← NEW: CODE tab
│   ├── CodeTerminal.tsx           ← NEW: Terminal UI
│   ├── CodexIntegration.tsx       ← NEW: Codex wrapper
│   ├── ContinueIntegration.tsx    ← NEW: Continue wrapper
│   ├── VaultFileBrowser.tsx       ← ENHANCED: File upload
│   ├── DocumentEditor.tsx         ← ENHANCED: Slash commands
│   ├── SpreadsheetEditor.tsx      ← ENHANCED: SQL formulas
│   ├── InsightsLab.tsx            ← ENHANCED: AI Chat button
│   ├── ThreadsSidebar.tsx         ← NEW: Chat/Doc threads
│   └── TeamChatWindow.tsx         ← ENHANCED: File wiring
├── lib/
│   ├── continue/                  ← NEW: Continue core
│   │   ├── llm/                   ← LLM abstraction
│   │   ├── agent/                 ← Agent mode
│   │   ├── autocomplete/          ← Autocomplete
│   │   └── edit/                  ← Edit mode
│   ├── codex/                     ← NEW: Codex integration
│   ├── excel-to-sql/              ← NEW: Formula translator
│   │   ├── parser.ts              ← Parse Excel formulas
│   │   ├── translator.ts          ← Convert to SQL
│   │   └── executor.ts            ← Execute via DuckDB
│   └── encryption.ts              ← ENHANCED: Recipient keys
└── stores/
    ├── codeStore.ts               ← NEW: CODE tab state
    ├── threadsStore.ts            ← NEW: Threads state
    └── docsStore.ts               ← ENHANCED: Collaboration
```

### Backend Structure
```
apps/backend/api/
├── code_agent/                    ← NEW: CODE tab backend
│   ├── codex_service.py           ← Codex integration
│   ├── continue_bridge.py         ← Continue integration
│   ├── terminal_manager.py        ← Terminal sessions
│   └── code_routes.py             ← API endpoints
├── vault_service.py               ← ENHANCED: File uploads
├── docs_routes.py                 ← ENHANCED: Collaboration
├── sheets_formula_engine.py       ← NEW: Excel → SQL
├── team_chat_files.py             ← NEW: File upload/sync
├── offline_file_share.py          ← ENHANCED: P2P sync
└── threads_service.py             ← NEW: Thread tracking
```

---

## Phase 1: Quick Wins (Days 1-3)

### Day 1: Vault File Uploads
**Goal:** Support any file type in Vault with drag-drop

**Tasks:**
1. ✅ Add file upload UI to VaultWorkspace.tsx
   - Drag-drop area (like Dropbox)
   - File picker button
   - Progress indicator
2. ✅ Create vault file storage endpoint
   ```python
   # apps/backend/api/vault_service.py

   @router.post("/vault/files/upload")
   async def upload_vault_file(
       file: UploadFile,
       vault_type: str,  # 'real' or 'decoy'
       folder_path: str = "/"
   ):
       # 1. Encrypt file client-side (Web Crypto API)
       # 2. Store encrypted blob in .neutron_data/vault_files/
       # 3. Save metadata in vault.db
       # 4. Return file_id and metadata
   ```
3. ✅ Implement folder hierarchy (Proton Drive style)
   - Create folder
   - Move files between folders
   - Breadcrumb navigation
4. ✅ Add file preview
   - Thumbnails for images
   - Icons for other types
   - Metadata display (size, date, type)

**Time estimate:** 6-8 hours

---

### Day 2: Team Chat File Wiring
**Goal:** Connect Team Chat file upload to backend, enable P2P sync

**Tasks:**
1. ✅ Create file upload API endpoint
   ```python
   # apps/backend/api/team_chat_files.py

   @router.post("/team-chat/files/upload")
   async def upload_chat_file(
       file: UploadFile,
       channel_id: str,
       mode: str  # 'solo' or 'p2p'
   ):
       # 1. Store file in .neutron_data/chat_files/
       # 2. If mode='p2p', add to offline_file_share.py
       # 3. Return file_id, file_url, metadata
   ```
2. ✅ Update TeamChatWindow.tsx to use backend
   ```typescript
   const handleSendMessage = async () => {
     if (uploadedFile) {
       const formData = new FormData()
       formData.append('file', uploadedFile)
       formData.append('channel_id', activeChannelId)
       formData.append('mode', mode)

       const response = await fetch('/api/v1/team-chat/files/upload', {
         method: 'POST',
         body: formData
       })

       const { file_id, file_url } = await response.json()

       // Create message with backend file reference
       const newMessage = {
         ...
         file: {
           file_id,  // Backend ID for syncing
           url: file_url,  // Backend URL
           name: uploadedFile.name,
           size: uploadedFile.size,
           synced: mode === 'p2p'
         }
       }
     }
   }
   ```
3. ✅ Wire to offline_file_share.py for P2P sync
4. ✅ Add download button (Slack-style)

**Time estimate:** 4-6 hours

---

### Day 3: Export/Import Basics
**Goal:** Word, Excel, CSV export/import using existing code

**Tasks:**
1. ✅ Docs export
   ```typescript
   // apps/frontend/src/components/DocumentEditor.tsx

   const exportDocument = async (format: 'docx' | 'doc' | 'pdf' | 'html' | 'md' | 'json') => {
     const response = await fetch('/api/v1/docs/export', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
         document_id: document.id,
         format,
         content: document.content
       })
     })

     const blob = await response.blob()
     downloadBlob(blob, `${document.title}.${format}`)
   }
   ```
2. ✅ Docs import (strip formatting, Quip-style)
   ```python
   # apps/backend/api/docs_routes.py

   @router.post("/docs/import")
   async def import_document(file: UploadFile):
       # 1. Detect file type (.docx, .doc, .html, .md, .txt)
       # 2. Extract text content only (strip formatting)
       # 3. Create new Doc document
       # 4. Return document_id
   ```
3. ✅ Sheets export (reuse existing Excel/CSV export from Database tab)
4. ✅ Bulk export (reuse template library zip function)
   ```python
   # Adapt from existing code:
   # apps/backend/api/automation_routes.py
   # Function: export_templates_as_zip()

   @router.post("/docs/export-bulk")
   async def export_all_docs(format: str):
       # 1. Get all Docs
       # 2. Export each to format
       # 3. Zip all files
       # 4. Return zip download
   ```
5. ✅ Add "Upload from Computer" to Docs tab
   ```typescript
   // apps/frontend/src/components/DocsWorkspace.tsx

   <DocumentTypeSelector>
     {/* Existing options */}
     <Divider />
     <MenuItem onClick={handleUploadFromComputer}>
       <Upload /> Upload from Computer
     </MenuItem>
   </DocumentTypeSelector>

   // Show modal:
   // - Choose file (Word, Excel)
   // - Choose destination: Docs (collab) or Vault (encrypted)
   // - Convert and create document
   ```

**Time estimate:** 6-8 hours

---

### Day 4: Docs Slash Commands
**Goal:** Notion-style slash commands with popup menu

**Tasks:**
1. ✅ Create SlashCommandMenu component
   ```typescript
   // apps/frontend/src/components/SlashCommandMenu.tsx

   const commands = [
     { id: 'h1', label: 'Heading 1', icon: <Heading1 />, shortcut: '/h1' },
     { id: 'h2', label: 'Heading 2', icon: <Heading2 />, shortcut: '/h2' },
     { id: 'h3', label: 'Heading 3', icon: <Heading3 />, shortcut: '/h3' },
     { id: 'bullet', label: 'Bullet List', icon: <List />, shortcut: '/bullet' },
     { id: 'numbered', label: 'Numbered List', icon: <ListOrdered />, shortcut: '/numbered' },
     { id: 'todo', label: 'To-do List', icon: <CheckSquare />, shortcut: '/todo' },
     { id: 'code', label: 'Code Block', icon: <Code />, shortcut: '/code' },
     { id: 'quote', label: 'Quote', icon: <Quote />, shortcut: '/quote' },
     { id: 'divider', label: 'Divider', icon: <Minus />, shortcut: '/divider' },
     { id: 'image', label: 'Image', icon: <Image />, shortcut: '/image' },
     { id: 'table', label: 'Table', icon: <Table />, shortcut: '/table' },
     { id: 'callout', label: 'Callout', icon: <AlertCircle />, shortcut: '/callout' },
   ]

   // Popup menu with arrow key navigation
   // Filter commands as user types
   // Insert formatting when selected
   ```
2. ✅ Integrate with RichTextEditor
   - Detect `/` typed
   - Show popup menu at cursor
   - Filter commands by typed text
   - Execute command on Enter
3. ✅ Add Markdown auto-convert
   ```typescript
   // As user types, convert:
   // **bold** → <strong>bold</strong>
   // *italic* → <em>italic</em>
   // `code` → <code>code</code>
   // [link](url) → <a href="url">link</a>
   ```
4. ✅ Keep existing format bar (bold, italic, etc.)

**Time estimate:** 6-8 hours

---

## Phase 2: Medium Complexity (Days 5-11)

### Days 5-6: Sheets Features (Sort, Filter, Formatting)
**Goal:** Implement ChatGPT's recommended "ship first" features

**Tasks:**
1. ✅ Column operations
   - Resize (drag column border)
   - Freeze (lock first N columns)
   - Hide/Show (right-click menu)
   - Reorder (drag column header)
2. ✅ Sort & Filter
   ```typescript
   // apps/frontend/src/components/SpreadsheetEditor.tsx

   const handleSort = (columnIndex: number, direction: 'asc' | 'desc') => {
     // Execute SQL query:
     // SELECT * FROM sheet ORDER BY col_${columnIndex} ${direction}
   }

   const handleFilter = (filters: Filter[]) => {
     // Build WHERE clause
     // Execute SQL query
     // Update view
   }

   // Save filter as view (persist to backend)
   ```
3. ✅ Find/Replace (regex support)
4. ✅ Data types & formats
   - Auto-detect type (text/number/date/boolean)
   - Format numbers (%, $, thousand separator)
   - Format dates (MM/DD/YYYY, etc.)
5. ✅ Data validation (dropdowns, ranges, regex)
6. ✅ Conditional formatting
   ```typescript
   const applyConditionalFormatting = (rule: FormattingRule) => {
     // rule: { range, condition, style }
     // Example: If value > 100, background = green
     // Store rules in sheet metadata
     // Apply CSS classes on render
   }
   ```
7. ✅ Quick calc bar (show sum/avg/min/max of selection)
8. ✅ Named ranges ("MyRange" = A1:B10)

**Time estimate:** 12-16 hours

---

### Days 7-8: Insights → AI Chat → Doc Workflow
**Goal:** Seamless workflow from audio to analysis to document

**Tasks:**
1. ✅ Add "Continue in AI Chat" button to Insights
   ```typescript
   // apps/frontend/src/components/InsightsLab.tsx

   const handleContinueInChat = () => {
     // 1. Get full analysis output
     const context = {
       transcript: transcription,
       summary: aiSummary,
       actionItems: actionItems
     }

     // 2. Switch to AI Chat tab
     setActiveTab('chat')

     // 3. Inject context into chat
     chatStore.startNewConversation({
       initialContext: context,
       model: selectedModel
     })

     // 4. User can now ask follow-up questions with 200k token window
   }
   ```
2. ✅ Add "Convert to Doc" button in Insights
   ```typescript
   const convertToDoc = () => {
     const docContent = `
# ${insightTitle}

## Transcript
${organizedTranscript}

## Summary
${summary}

## Action Items
${actionItems.map(item => `- [ ] ${item}`).join('\n')}
     `

     docsStore.createDocument('doc', {
       title: insightTitle,
       content: docContent
     })

     setWorkspaceView('docs')
   }
   ```
3. ✅ Add "Convert to Doc" button in AI Chat
   ```typescript
   const convertChatToDoc = () => {
     const docContent = formatChatAsDocument(chatHistory)
     docsStore.createDocument('doc', {
       title: 'Chat Export',
       content: docContent
     })
   }
   ```
4. ✅ Ensure context preservation (200k tokens)

**Time estimate:** 6-8 hours

---

### Days 9-10: Docs Comments & Threads
**Goal:** Google Docs-style comments + unified Threads sidebar

**Tasks:**
1. ✅ Add comment UI to DocumentEditor
   ```typescript
   // Select text → right-click → "Add comment"
   // Or use toolbar button

   interface Comment {
     id: string
     document_id: string
     user_id: string
     user_name: string
     content: string
     thread: Reply[]  // Nested replies
     text_range: { start: number, end: number }
     created_at: string
     resolved: boolean
   }

   // Highlight commented text
   // Show comment bubble on hover
   // Click to open thread
   ```
2. ✅ Create ThreadsSidebar component
   ```typescript
   // apps/frontend/src/components/ThreadsSidebar.tsx

   <Sidebar>
     <Section title="THREADS">
       <SubSection title="Chat Threads">
         {chatThreads.map(thread => (
           <ThreadItem
             key={thread.id}
             type="chat"
             channel={thread.channel}
             preview={thread.preview}
             unread={thread.unread}
             onClick={() => navigateToThread(thread)}
           />
         ))}
       </SubSection>

       <SubSection title="Doc Threads">
         {docThreads.map(thread => (
           <ThreadItem
             key={thread.id}
             type="doc"
             document={thread.document}
             preview={thread.comment}
             unread={thread.unread}
             onClick={() => navigateToThread(thread)}
           />
         ))}
       </SubSection>
     </Section>
   </Sidebar>
   ```
3. ✅ Backend for comment storage
   ```python
   # apps/backend/api/threads_service.py

   class ThreadsService:
       def add_comment(self, doc_id, user_id, content, text_range):
           # Store in SQLite
           # Return comment_id

       def get_doc_threads(self, doc_id):
           # Return all comments with replies

       def get_user_threads(self, user_id):
           # Return all threads user is involved in

       def mark_resolved(self, comment_id):
           # Mark comment as resolved
   ```
4. ✅ Add to TeamWorkspace header
   ```typescript
   // Show Threads section above CHANNELS in sidebar
   ```

**Time estimate:** 10-14 hours

---

### Days 11-12: Git-Style Version History
**Goal:** Consistent version history across all file types

**Tasks:**
1. ✅ Design version storage schema
   ```sql
   CREATE TABLE file_versions (
       id TEXT PRIMARY KEY,
       file_id TEXT NOT NULL,
       file_type TEXT NOT NULL, -- 'doc', 'sheet', 'vault_file', etc.
       version_number INTEGER NOT NULL,
       content_hash TEXT NOT NULL,
       content_blob TEXT, -- Encrypted for vault files
       metadata TEXT, -- JSON with author, message, timestamp
       created_at TEXT NOT NULL,
       created_by TEXT NOT NULL,
       UNIQUE(file_id, version_number)
   );

   CREATE INDEX idx_versions_file ON file_versions(file_id, version_number DESC);
   ```
2. ✅ Create VersionHistorySidebar component
   ```typescript
   // apps/frontend/src/components/VersionHistorySidebar.tsx

   <Sidebar>
     <Timeline>
       {versions.map(version => (
         <VersionItem
           key={version.id}
           number={version.version_number}
           author={version.created_by}
           timestamp={version.created_at}
           message={version.metadata.message}
           current={version.id === currentVersionId}
           onRestore={() => restoreVersion(version.id)}
           onViewDiff={() => showDiff(version.id)}
         />
       ))}
     </Timeline>
   </Sidebar>
   ```
3. ✅ Implement diff viewer
   ```typescript
   const showDiff = (versionId: string) => {
     // Fetch two versions
     // Show side-by-side diff
     // For Docs: text diff
     // For Sheets: cell-by-cell diff
     // For files: binary diff or "changed" indicator
   }
   ```
4. ✅ Auto-create versions on save
   ```typescript
   const saveDocument = async () => {
     // 1. Save current content
     // 2. Create new version entry
     // 3. Increment version number
     // 4. Store diff/snapshot
   }
   ```
5. ✅ Add version history button to all editors

**Time estimate:** 10-14 hours

---

## Phase 3: Complex Features (Days 13-21)

### Days 13-16: Sheets Formulas (SQL-Powered)
**Goal:** Excel → DuckDB translation with comprehensive formula support

**Tasks:**
1. ✅ Create Excel formula parser
   ```typescript
   // apps/frontend/src/lib/excel-to-sql/parser.ts

   class ExcelFormulaParser {
     parse(formula: string): AST {
       // Parse Excel formula into AST
       // Example: "=SUM(A1:A10)" →
       // {
       //   function: 'SUM',
       //   args: [{ range: { start: 'A1', end: 'A10' } }]
       // }
     }
   }
   ```
2. ✅ Create SQL translator using mapping
   ```typescript
   // apps/frontend/src/lib/excel-to-sql/translator.ts

   import formulaMapping from './formula-mapping.json'

   class SQLTranslator {
     translate(ast: AST, sheetContext: SheetContext): string {
       // Convert AST to SQL using mapping
       // Example: SUM(A1:A10) →
       // "SELECT SUM(col_1) FROM sheet_table WHERE row_num BETWEEN 1 AND 10"

       switch (ast.function) {
         case 'SUM':
           return this.translateAggregate(ast, 'SUM')
         case 'VLOOKUP':
           return this.translateVLookup(ast, sheetContext)
         case 'IF':
           return this.translateConditional(ast)
         // ... all other formulas
       }
     }

     translateAggregate(ast: AST, sqlFunc: string): string {
       const range = ast.args[0].range
       const column = this.rangeToColumn(range.start)
       const startRow = this.rangeToRow(range.start)
       const endRow = this.rangeToRow(range.end)

       return `SELECT ${sqlFunc}(${column}) FROM sheet_table
               WHERE row_num BETWEEN ${startRow} AND ${endRow}`
     }

     translateVLookup(ast: AST, ctx: SheetContext): string {
       // Use mapping from formula-mapping.json
       const mapping = formulaMapping.lookups_scalar_helpers
         .find(m => m.excel.startsWith('VLOOKUP'))

       // Generate SQL with LEFT JOIN pattern
       return mapping.duckdb_plan.emit
         .replace('${table}', ctx.tableName)
         .replace('${first_col}', this.getFirstColumn())
         .replace('${i_col}', this.getColumnIndex(ast.args[2]))
       // ... etc
     }
   }
   ```
3. ✅ Create SQL executor
   ```typescript
   // apps/frontend/src/lib/excel-to-sql/executor.ts

   class FormulaExecutor {
     async execute(sql: string, sessionId: string): Promise<any> {
       // Execute SQL via existing DuckDB backend
       const response = await api.executeQuery(sessionId, sql)
       return response.result
     }

     async updateCell(cellAddress: string, formula: string) {
       // 1. Parse formula
       const ast = parser.parse(formula)

       // 2. Translate to SQL
       const sql = translator.translate(ast, sheetContext)

       // 3. Execute
       const result = await this.execute(sql, sessionId)

       // 4. Update cell with result
       setCellValue(cellAddress, result)

       // 5. Mark as computed (show formula in formula bar)
       setCellFormula(cellAddress, formula)
     }
   }
   ```
4. ✅ Load formula mapping from JSON
   ```typescript
   // Save mapping to:
   // apps/frontend/src/lib/excel-to-sql/formula-mapping.json
   ```
5. ✅ Add formula bar to SpreadsheetEditor
   ```typescript
   <FormulaBar>
     <CellAddress>{selectedCell}</CellAddress>
     <FormulaInput
       value={cellFormula}
       onChange={handleFormulaChange}
       onSubmit={handleFormulaSubmit}
     />
   </FormulaBar>
   ```
6. ✅ Implement dependency graph (cell references)
   ```typescript
   class DependencyGraph {
     // Track which cells depend on which
     // Recalculate downstream cells when upstream changes
     // Detect circular references
     // Topological sort for recomputation order
   }
   ```
7. ✅ Add UX sugar:
   - "Explain this cell" (show generated SQL)
   - "Convert to SQL" (open in Database tab)
   - Auto-complete for cell references
   - Auto-complete for functions

**Time estimate:** 24-32 hours

---

### Days 17-21: P2P/LAN Networking Hardening
**Goal:** Rock-solid P2P/LAN with file sync, encryption, error handling

**Tasks:**
1. ✅ Install libp2p dependency
   ```bash
   # Already added to requirements.txt
   cd apps/backend
   pip install libp2p>=0.1.5
   ```
2. ✅ Test P2P/LAN services
   ```bash
   # Check if services load
   # Look for "✓ Services: ... P2P, LAN, P2P Mesh ..." in logs
   ```
3. ✅ Wire Team Chat file upload to offline_file_share.py
   ```python
   # apps/backend/api/team_chat_files.py

   from api.offline_file_share import offline_file_share

   @router.post("/team-chat/files/upload")
   async def upload_chat_file(file: UploadFile, channel_id: str, mode: str):
       # 1. Save file
       file_path = save_uploaded_file(file)

       # 2. If P2P mode, share file
       if mode == 'p2p':
           shared_file = await offline_file_share.share_file(
               file_path=file_path,
               shared_by_peer_id=get_peer_id(),
               shared_by_name=get_user_name(),
               description=f"Shared in #{channel_id}"
           )
           return shared_file

       return local_file_info
   ```
4. ✅ Implement Vault → Team Chat sharing with encryption
   ```python
   # apps/backend/api/vault_service.py

   @router.post("/vault/share-to-chat")
   async def share_vault_file_to_chat(
       file_id: str,
       channel_id: str,
       recipient_ids: List[str]
   ):
       # 1. Decrypt file with vault key
       vault_file = get_vault_file(file_id)
       decrypted_content = decrypt_with_vault_key(vault_file)

       # 2. Re-encrypt for each recipient
       encrypted_shares = []
       for recipient_id in recipient_ids:
           # Get recipient's public vault key
           recipient_key = get_recipient_vault_key(recipient_id)

           # Encrypt file specifically for this recipient
           encrypted_share = encrypt_for_recipient(
               content=decrypted_content,
               recipient_key=recipient_key
           )
           encrypted_shares.append(encrypted_share)

       # 3. Upload to chat with metadata
       # Each recipient can only decrypt their own copy
       return create_chat_message(channel_id, encrypted_shares)
   ```
5. ✅ Add real-time connection status
   ```typescript
   // apps/frontend/src/stores/networkStore.ts

   interface NetworkStatus {
     mode: 'solo' | 'lan' | 'p2p'
     connected: boolean
     peers: Peer[]
     quality: {
       ping: number
       bandwidth: number
       signal: 'excellent' | 'good' | 'fair' | 'poor'
     }
     battery: {
       level: number
       charging: boolean
       impact: 'low' | 'medium' | 'high'
     }
     syncStatus: 'idle' | 'syncing' | 'synced' | 'error'
   }

   // Poll status every 5 seconds
   // Update NetworkSelector display
   ```
6. ✅ Add connection quality indicators
   ```typescript
   // apps/frontend/src/components/NetworkSelector.tsx

   <NetworkStatus>
     <Badge color={getQualityColor(quality.signal)}>
       {quality.ping}ms
     </Badge>
     <Badge>
       {formatBandwidth(quality.bandwidth)}
     </Badge>
     <BatteryIcon level={battery.level} charging={battery.charging} />
   </NetworkStatus>
   ```
7. ✅ Add sync status indicators
   ```typescript
   // Show in Team Chat header
   <SyncStatus>
     {syncStatus === 'syncing' && (
       <Spinner /> Syncing files...
     )}
     {syncStatus === 'synced' && (
       <Check /> All synced
     )}
   </SyncStatus>
   ```
8. ✅ Implement auto-reconnect on network issues
   ```python
   # apps/backend/api/p2p_mesh_service.py

   class P2PReconnectManager:
       MAX_RETRIES = 5
       BACKOFF_BASE = 2  # seconds

       async def handle_disconnect(self, peer_id: str):
           for attempt in range(self.MAX_RETRIES):
               try:
                   await asyncio.sleep(self.BACKOFF_BASE ** attempt)
                   await self.reconnect(peer_id)
                   logger.info(f"Reconnected to {peer_id}")
                   return
               except Exception as e:
                   logger.warning(f"Reconnect attempt {attempt+1} failed: {e}")

           logger.error(f"Failed to reconnect to {peer_id} after {self.MAX_RETRIES} attempts")
   ```
9. ✅ Add file transfer progress tracking
   ```typescript
   interface FileTransferProgress {
     file_id: string
     filename: string
     size: number
     transferred: number
     speed: number  // bytes/sec
     eta: number    // seconds
     status: 'pending' | 'transferring' | 'completed' | 'failed'
   }

   // Show progress in Team Chat
   <FileTransferProgress transfer={transfer} />
   ```
10. ✅ Error handling and user feedback
    ```typescript
    // Toast notifications for network events
    toast.success('Connected to Brother Michael')
    toast.warning('Connection lost. Retrying in 5s...')
    toast.error('Failed to connect. Check your network.')
    toast.info('File uploaded successfully. Syncing to 2 peers...')
    ```

**Time estimate:** 32-40 hours

---

## Phase 4: Future Roadmap

### CODE Tab Implementation (Week 4)
**Goal:** Fully integrate Codex + Continue for Claude Code replacement

**Tasks:**
1. ✅ Set up CODE tab structure
   ```typescript
   // apps/frontend/src/components/CodeWorkspace.tsx

   <CodeWorkspace>
     <CodeTerminal>
       {/* Embedded terminal running Codex */}
     </CodeTerminal>

     <CodeSidebar>
       {/* File tree, search, etc. */}
     </CodeSidebar>

     <ContinueIntegration>
       {/* Autocomplete, chat, edit overlays */}
     </ContinueIntegration>
   </CodeWorkspace>
   ```

2. ✅ Integrate Codex binary
   ```typescript
   // apps/frontend/src/lib/codex/CodexRunner.ts

   import { spawn } from 'child_process'

   class CodexRunner {
     private process: ChildProcess

     start(workingDir: string) {
       this.process = spawn('codex', [], {
         cwd: workingDir,
         stdio: ['pipe', 'pipe', 'pipe'],
         env: {
           ...process.env,
           OLLAMA_API_BASE: 'http://localhost:11434'
         }
       })

       // Pipe stdout/stderr to terminal UI
       this.process.stdout.on('data', (data) => {
         this.onOutput(data.toString())
       })
     }

     sendCommand(command: string) {
       this.process.stdin.write(command + '\n')
     }
   }
   ```

3. ✅ Integrate Continue core
   ```typescript
   // Copy from /Users/indiedevhipps/Documents/continue-main/core
   // Into apps/frontend/src/lib/continue/

   // Adapt Continue's LLM layer
   import { Ollama } from '@/lib/continue/llm/llms/Ollama'

   const llm = new Ollama({
     model: "deepseek-coder:33b",
     apiBase: "http://localhost:11434"
   })

   // Set up agent, chat, edit, autocomplete
   import { Agent, Chat, Edit, Autocomplete } from '@/lib/continue'
   ```

4. ✅ Add autocomplete
   ```typescript
   // Inline suggestions as user types
   <CodeEditor
     onKeyDown={handleKeyDown}
     onAutocomplete={async (context) => {
       const suggestion = await autocomplete.getSuggestion(context)
       return suggestion
     }}
   />
   ```

5. ✅ Add chat panel
   ```typescript
   <CodeChatPanel>
     <ChatInput
       onSubmit={async (message) => {
         const response = await chat.sendMessage(message)
         addChatMessage(response)
       }}
     />
   </CodeChatPanel>
   ```

6. ✅ Add agent mode
   ```typescript
   <AgentMode>
     <AgentPrompt
       onStart={async (task) => {
         const agent = new Agent(llm)
         const result = await agent.executeTask(task)
         showResult(result)
       }}
     />
   </AgentMode>
   ```

7. ✅ Wire to Vault (optional save location)
8. ✅ Add keyboard shortcuts
   ```typescript
   // Cmd+K: Open command palette
   // Cmd+L: Focus chat
   // Cmd+.: Trigger autocomplete
   // Cmd+Shift+A: Start agent mode
   ```

**Time estimate:** 24-32 hours

---

### iPad Companion App (Month 2+)
**Goal:** Responsive UI that works on iPad, ship later with team

**Prep work now:**
- Use responsive components (Tailwind breakpoints)
- Touch-friendly hit targets (min 44px)
- Gestures instead of hover states
- Progressive Web App (PWA) support

---

### Enterprise Features (MagnetarCloud)
**Goal:** SaaS version with team management, SSO, etc.

**Deferred to separate codebase** - ElohimOS stays open-source and clean

---

## Excel to DuckDB Formula Mapping

```json
{
  "policies": {
    "blank_is_null": true,
    "lookup_on_duplicates": "first|last|error",
    "xlookup_default_on_missing": null,
    "division_by_zero_returns": null
  },

  "aggregates": [
    {"excel":"SUM",      "duckdb":"SUM(${expr})"},
    {"excel":"AVERAGE",  "duckdb":"AVG(${expr})"},
    {"excel":"MIN",      "duckdb":"MIN(${expr})"},
    {"excel":"MAX",      "duckdb":"MAX(${expr})"},
    {"excel":"COUNT",    "duckdb":"COUNT(${expr})"},
    {"excel":"COUNTA",   "duckdb":"COUNT(${expr}) FILTER (WHERE ${expr} IS NOT NULL)"}
  ],

  "math_numeric": [
    {"excel":"ROUND(x,n)",    "duckdb":"ROUND(${x}, ${n})"},
    {"excel":"ROUNDUP(x,n)",  "duckdb":"CEIL(${x} * POW(10, ${n})) / POW(10, ${n})"},
    {"excel":"ROUNDDOWN(x,n)","duckdb":"FLOOR(${x} * POW(10, ${n})) / POW(10, ${n})"}
  ],

  "conditional": [
    {"excel":"IF(cond,a,b)",     "duckdb":"CASE WHEN ${cond} THEN ${a} ELSE ${b} END"},
    {"excel":"IFS(c1,v1,...)",   "duckdb":"CASE WHEN ${c1} THEN ${v1} WHEN ${c2} THEN ${v2} ... ELSE NULL END"},
    {"excel":"IFERROR(x,alt)",   "duckdb":"COALESCE(${try_x}, ${alt})", "notes":"emit ${try_x} with TRY_* wrappers where needed"},
    {"excel":"AND(a,b,...)",     "duckdb":"(${a}) AND (${b}) AND ..."},
    {"excel":"OR(a,b,...)",      "duckdb":"(${a}) OR (${b}) OR ..."},
    {"excel":"NOT(a)",           "duckdb":"NOT (${a})"},
    {"excel":"=A/B",             "duckdb":"${A} / NULLIF(${B},0)", "notes":"pair with COALESCE(..., policies.division_by_zero_returns)"}
  ],

  "is_checks": [
    {"excel":"ISBLANK(x)",   "duckdb":"(${x} IS NULL OR ${x}='')"},
    {"excel":"ISNUMBER(x)",  "duckdb":"(TRY_CAST(${x} AS DOUBLE) IS NOT NULL)"},
    {"excel":"ISTEXT(x)",    "duckdb":"(TYPEOF(${x}) IN ('VARCHAR'))"}
  ],

  "text": [
    {"excel":"TRIM(x)",         "duckdb":"TRIM(${x})"},
    {"excel":"LEN(x)",          "duckdb":"LENGTH(${x})"},
    {"excel":"LEFT(x,n)",       "duckdb":"SUBSTR(${x}, 1, ${n})"},
    {"excel":"RIGHT(x,n)",      "duckdb":"SUBSTR(${x}, GREATEST(LENGTH(${x})-${n}+1,1))"},
    {"excel":"MID(x, start, n)","duckdb":"SUBSTR(${x}, ${start}, ${n})"},
    {"excel":"UPPER(x)",        "duckdb":"UPPER(${x})"},
    {"excel":"LOWER(x)",        "duckdb":"LOWER(${x})"},
    {"excel":"PROPER(x)",       "duckdb":"INITCAP(${x})"},
    {"excel":"SUBSTITUTE(x,old,new)","duckdb":"REPLACE(${x}, ${old}, ${new})"},
    {"excel":"CONCAT(a,b,...)", "duckdb":"CONCAT(${a}, ${b}, ...)"},
    {"excel":"TEXTJOIN(delim,ignore_blank,range)","duckdb":"STRING_AGG(${val}, ${delim}) FILTER (WHERE ${ignore_blank}? ${val} IS NOT NULL AND ${val}<>'' : TRUE)", "notes":"use GROUP BY context or window"},
    {"excel":"TEXT(x, fmt)",    "duckdb":"FORMAT(${fmt}, ${x})", "notes":"fallback to PRINTF if needed"}
  ],

  "datetime": [
    {"excel":"TODAY()",            "duckdb":"CURRENT_DATE"},
    {"excel":"NOW()",              "duckdb":"CURRENT_TIMESTAMP"},
    {"excel":"DATE(y,m,d)",        "duckdb":"MAKE_DATE(${y}, ${m}, ${d})"},
    {"excel":"DATEDIF(s,e,'d')",   "duckdb":"DATE_DIFF('day', ${s}, ${e})"},
    {"excel":"DATEDIF(s,e,'m')",   "duckdb":"DATE_DIFF('month', ${s}, ${e})"},
    {"excel":"DATEDIF(s,e,'y')",   "duckdb":"DATE_DIFF('year', ${s}, ${e})"},
    {
      "excel":"EOMONTH(d, n)",
      "duckdb":"(DATE_TRUNC('month', ${d}) + INTERVAL (${n}+1) MONTH) - INTERVAL 1 DAY"
    },
    {
      "excel":"WORKDAY(d, n, [holidays])",
      "duckdb":"-- requires calendar\nWITH cal AS (\n  SELECT day, is_workday FROM ${calendar}\n)\nSELECT t.day\nFROM (\n  SELECT day, ROW_NUMBER() OVER (ORDER BY day) AS rn\n  FROM cal\n  WHERE day >= ${d} AND is_workday\n) t\nWHERE t.rn = ${n_offset}\n",
      "notes":"precompute calendar with weekends/holidays; n_offset handles +/-"
    },
    {
      "excel":"NETWORKDAYS(s, e, [holidays])",
      "duckdb":"SELECT COUNT(*) FROM ${calendar} WHERE day BETWEEN ${s} AND ${e} AND is_workday"
    }
  ],

  "dynamic_arrays": [
    {"excel":"UNIQUE(range)",  "duckdb":"SELECT DISTINCT ${cols} FROM ${source}"},
    {"excel":"FILTER(range, cond)","duckdb":"SELECT ${cols} FROM ${source} WHERE ${cond}"},
    {"excel":"SORT(range, [bycol], [order])","duckdb":"SELECT ${cols} FROM ${source} ORDER BY ${bycol} ${order}"}
  ],

  "lookups_scalar_helpers": [
    {
      "excel":"VLOOKUP(k, table, i, FALSE)",
      "duckdb_plan": {
        "cte":"src AS (SELECT * FROM ${table})",
        "emit":"SELECT s.${i_col}\nFROM src s\nJOIN (SELECT ${k} AS __k) q ON q.__k = s.${first_col}\n${tie_break}"
      },
      "tie_break": "QUALIFY ROW_NUMBER() OVER (PARTITION BY s.${first_col} ORDER BY ${policy_order}) = 1",
      "notes":"policy_order picks first/last; for error-on-dup do HAVING COUNT(*)>1 guard"
    },
    {
      "excel":"INDEX(range, MATCH(k, key_range, 0))",
      "duckdb_plan":{
        "emit":"SELECT r.${value_col}\nFROM ${range_table} r\nJOIN (SELECT ${k} AS __k) q ON q.__k = r.${key_col}\n${tie_break}"
      }
    },
    {
      "excel":"XLOOKUP(k, key_range, val_range, [default], [match_mode], [search_mode])",
      "duckdb_plan":{
        "cte":"keys AS (SELECT ${key_col}, ${val_col}, ${order_col?} FROM ${table})",
        "emit":"SELECT COALESCE(v.${val_col}, ${default})\nFROM (\n  SELECT ${val_col}\n  FROM keys\n  WHERE ${key_col} = ${k}\n  ${order_clause}\n  ${limit_1}\n) v",
        "order_clause":"-- if search_mode = -1 (last to first): ORDER BY ${order_col} DESC",
        "limit_1":"LIMIT 1"
      },
      "notes":"match_mode: 0 exact (default); ±1 for next/prev via ORDER BY and inequality"
    }
  ],

  "coercion_helpers": [
    {"excel":"VALUE(x)",        "duckdb":"TRY_CAST(${x} AS DOUBLE)"},
    {"excel":"TEXT(x, fmt)",    "duckdb":"FORMAT(${fmt}, ${x})"},
    {"excel":"DATEVALUE(x)",    "duckdb":"TRY_CAST(${x} AS DATE)"},
    {"excel":"NUMBERVALUE(x)",  "duckdb":"TRY_CAST(${x} AS DOUBLE)"}
  ]
}
```

**Save this as:** `apps/frontend/src/lib/excel-to-sql/formula-mapping.json`

---

## Testing Strategy

### Unit Tests
- Formula parser (each Excel function)
- SQL translator (each mapping)
- Encryption/decryption
- Version history logic
- Network reconnection

### Integration Tests
- File upload → storage → retrieval
- Vault share → chat (with encryption)
- P2P file sync (2 instances)
- LAN discovery (2+ devices)
- Formula execution (Excel → SQL → result)

### E2E Tests
- Full user workflows:
  1. Upload file to Vault → share to chat
  2. Create Doc → add comments → reply in thread
  3. Create Sheet → enter formulas → export to Excel
  4. Record audio → transcribe → AI analysis → continue in chat → convert to doc
  5. CODE tab → ask question → get suggestion → accept → run code

### Manual Testing Checklist
```
Phase 1 (Days 1-3):
[ ] Upload 10 different file types to Vault
[ ] Create folder hierarchy
[ ] Delete file → verify in trash
[ ] Upload file to Team Chat
[ ] Download file from chat
[ ] Export Doc to Word
[ ] Import Word to Doc
[ ] Bulk export 5 Docs as zip

Phase 2 (Days 5-11):
[ ] Add slash commands in Doc
[ ] Sort spreadsheet by column
[ ] Filter spreadsheet rows
[ ] Apply conditional formatting
[ ] Add comment to Doc
[ ] Reply to comment (thread)
[ ] View Threads sidebar
[ ] Create version of Doc
[ ] Restore previous version

Phase 3 (Days 13-21):
[ ] Enter SUM formula in Sheet
[ ] Enter VLOOKUP formula
[ ] Enter IF formula
[ ] Complex formula (nested IFs)
[ ] Connect to 2nd Mac via LAN
[ ] Connect to peer via P2P
[ ] Upload file → verify sync
[ ] Share Vault file to chat
[ ] Check network status indicator
[ ] Disconnect → verify auto-reconnect

Phase 4 (Week 4):
[ ] Open CODE tab
[ ] Run Codex command
[ ] Ask Continue for code suggestion
[ ] Accept autocomplete suggestion
[ ] Start agent task
[ ] Save code to Vault
```

---

## Deployment Checklist

### Pre-Launch
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual testing complete
- [ ] Security audit (encryption, vault, P2P)
- [ ] Performance testing (110k row sheet)
- [ ] Documentation updated
- [ ] README with setup instructions
- [ ] License files in place (Apache 2.0, attribute Codex/Continue)

### Launch Day
- [ ] Tag v1.0.0
- [ ] Create GitHub Release
- [ ] Push to main branch
- [ ] Announce on Discord/Twitter
- [ ] Monitor for bug reports

### Post-Launch
- [ ] Gather user feedback
- [ ] Fix critical bugs within 24h
- [ ] Plan v1.1 features
- [ ] Start MagnetarCloud (enterprise)

---

## Timeline Summary

| Phase | Days | Features |
|-------|------|----------|
| Phase 1 | 1-3 | Vault uploads, Chat files, Export/Import, Slash commands |
| Phase 2 | 5-11 | Sheets features, Insights workflow, Comments/Threads, Version history |
| Phase 3 | 13-21 | Sheets formulas, P2P/LAN hardening |
| Phase 4 | 22+ | CODE tab, iPad prep, Enterprise |

**Total to MVP:** 21 days (3 weeks)

---

## Success Criteria

### Week 1
- ✅ Vault accepts all file types
- ✅ Team Chat file upload works
- ✅ Export/Import functional
- ✅ Docs slash commands working

### Week 2
- ✅ Sheets sort/filter/formatting complete
- ✅ Comments and Threads UI done
- ✅ Version history working
- ✅ Insights → AI Chat → Doc workflow seamless

### Week 3
- ✅ Sheets formulas (top 20 functions) working
- ✅ P2P file sync working with 2 devices
- ✅ LAN discovery working
- ✅ Network status indicators accurate
- ✅ Ready for production use

### Week 4+
- ✅ CODE tab fully functional
- ✅ Replace Claude for daily coding work
- ✅ Launch ElohimOS v1.0

---

## Notes

### Code Cleanliness
- Maintain clean repo structure
- Properly integrate external code (don't just copy)
- Add attribution comments for Codex/Continue code
- Keep licenses in LICENSES/ directory
- Document all architectural decisions

### Security
- All network calls must be explicit and auditable
- No telemetry, no tracking, no analytics
- Vault encryption client-side only
- P2P transfers encrypted
- Offline-first always

### Performance
- Target: 110k rows × 49 cols in <5 seconds
- Lazy load large files
- Virtual scrolling for sheets
- Web Workers for heavy computation
- IndexedDB for local caching

---

## Contact

**Project Lead:** Josh Hipps (josh.hipps@pm.me)
**Company:** Magnetar AI LLC
**License:** Apache 2.0 (Open Source)
**Enterprise:** MagnetarCloud (coming soon)

---

**END OF MASTER IMPLEMENTATION PLAN**
