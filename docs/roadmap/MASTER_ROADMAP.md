# ElohimOS Master Roadmap - Single Source of Truth
**Version:** 1.0 Unified
**Last Updated:** 2025-11-05
**Status:** Ready for Implementation

---

## Table of Contents

1. [Vision & Philosophy](#vision--philosophy)
2. [Architecture Overview](#architecture-overview)
3. [Integration Strategy](#integration-strategy)
4. [Phase-by-Phase Implementation](#phase-by-phase-implementation)
5. [Technical Specifications](#technical-specifications)
6. [Security & RBAC](#security--rbac)
7. [Testing Strategy](#testing-strategy)
8. [Future Enhancements](#future-enhancements)

---

## Vision & Philosophy

### What We're Building

**ElohimOS Code Tab:** A unified coding environment that's simpler than VS Code, more powerful than Claude Code, fully local, and learns from you. Where terminals become intelligent, context flows seamlessly, and coding happens naturally.

### The Problems We're Solving

**VS Code:**
- Too complex with endless extensions
- Context switching between editor/terminal/chat
- Overwhelming for ADHD-friendly workflows
- Not AI-first in design

**Claude Code:**
- Great AI but cloud-dependent
- Separate from actual coding environment
- Subscription-based
- Privacy concerns with code in cloud

**Our Solution:**
One tab, intelligent terminals, zero friction, 100% local, mission-critical security.

### Core Principles

1. **Extreme Simplicity** - Monaco is notepad/roadmap, not primary coding
2. **Terminal-First Philosophy** - Real engineers live in terminal
3. **Context is Automatic** - Terminal Bridge captures everything
4. **100% Local** - No cloud dependencies, works offline
5. **Learning System** - Gets smarter over time
6. **Security Paramount** - Permission-based, Founder control, audit logging
7. **ADHD-Friendly** - Clean interfaces, single focus areas

### Multi-LLM Orchestration Philosophy

**Why Multiple Specialized Models Beat One Generalist:**

Different AI models excel at different cognitive tasks:

- **GPT-5 (Codex)**: Fast codebase scanning, pattern recognition, architectural planning
  - Use case: "Scan the codebase and find cleanup opportunities"

- **Claude Sonnet 4.5**: Precise code generation, detailed implementation, edge case handling
  - Use case: "Implement the specific changes Codex identified"

- **Specialized Code Models** (qwen2.5-coder, deepseek-r1, codestral):
  - Each optimized for specific languages/frameworks
  - Local execution for privacy-critical work

**Real-World Workflow:**
1. Codex scans codebase → identifies 5 cleanup items
2. Codex hands off detailed task list → Claude implements each item
3. Claude executes precise code changes → uses specialized models for specific tasks
4. Context flows between all models → no repeated explanations

**The Vision:**
Every terminal can have its own specialized model, chosen automatically based on task type, language/framework, privacy requirements, and speed needs.

---

## Architecture Overview

### High-Level Components

```
┌─────────────────────────────────────────────────────────┐
│                    ElohimOS Frontend                     │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────┐   │
│  │ Left Nav   │  │ Code Tab   │  │ Global Header   │   │
│  │            │  │ Workspace  │  │  </> Terminal   │   │
│  │ 💬 Chat    │  │            │  │     Button      │   │
│  │ 💼 Work    │  │ Files|Chat │  └─────────────────┘   │
│  │ </> Code   │  │ ─────────  │                         │
│  │ 🗄️ DB      │  │  Monaco    │                         │
│  │ ⚙️ Settings│  │  + Chat    │                         │
│  └────────────┘  └────────────┘                         │
└─────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴────────┐
                    │                │
        ┌───────────▼──────┐  ┌──────▼─────────┐
        │  Terminal Bridge │  │  Backend API   │
        │   (Python PTY)   │  │  (FastAPI)     │
        │                  │  │                │
        │ • System terminal spawn (current)    │
        │ • Session tracking + audit (current) │
        │ • WS I/O (future, optional)          │
        │ • Resize/echo (future)               │
        └──────────────────┘  └────────────────┘
                    │
        ┌───────────┴────────────┐
        │                        │
┌───────▼──────┐      ┌──────────▼─────────┐
│   EXISTING   │      │  Continue Core     │
│   Context    │      │  (LLM Spine)       │
│   System     │      │                    │
│              │      │ • 73 providers     │
│ • Embeddings │      │ • Tools            │
│ • Memory     │      │ • Code indexing    │
│ • Jarvis BQ  │      │ • Context API      │
└───────────────┘     └────────────────────┘
        │                        │
        └───────────┬────────────┘
                    │
        ┌───────────▼──────────┐
        │   Ollama             │
        │   (Local Models)     │
        │                      │
        │ • qwen2.5-coder:32b │
        │ • deepseek-r1:32b   │
        │ • codestral:22b     │
        └──────────────────────┘
```

### Key Changes from Original Plans

1. **No ChromaDB initially** - Use existing ElohimOS context/embeddings
2. **Terminal Launcher First** - Spawn native OS terminals via authenticated API (current); defer WebSocket I/O + in‑browser terminal to a later optional phase
3. **One LLM spine** - Continue Core first, defer JARVIS/Codex to later phases
4. **Existing RBAC** - Use ElohimOS permission system
5. **Existing paths** - Everything under `.neutron_data/`

---

## Integration Strategy

### Reusable Components from Existing Projects

#### 1. CODEX PROJECT
**Best for:** Agent Architecture

**Copy:**
- TypeScript SDK (`@openai/codex-sdk`) - Event-driven streaming
- Security patterns - Path validation, sandboxing
- Read file with indentation mode - Smart code block extraction

**Files:**
- `/Users/indiedevhipps/Documents/codex-main/sdk/typescript/src/index.ts`
- `/Users/indiedevhipps/Documents/codex-main/sdk/typescript/src/thread.ts`

#### 2. CONTINUE PROJECT
**Best for:** File Operations & LLM

**Copy:**
✅ IDE Interface - `/core/index.d.ts`
✅ File Operations Tools - readFile.ts, createNewFile.ts, lsTool.ts
✅ 73 LLM Providers - `/core/llm/`
✅ Context Providers - `/core/context/providers/`
✅ Directory Walking - `/core/indexing/walkDir.ts` (Respects .gitignore)
✅ Path Utilities - `/core/util/uri.ts`

**Files:**
```
/Users/indiedevhipps/Documents/continue-main/core/
├── index.d.ts                    # IDE interface
├── tools/implementations/
│   ├── readFile.ts               # ✅ Copy this
│   ├── createNewFile.ts          # ✅ Copy this
│   └── lsTool.ts                 # ✅ Copy this
├── llm/
│   ├── index.ts                  # ✅ BaseLLM class
│   └── llms/OpenAI.ts            # ✅ Copy for Phase 4
├── indexing/
│   ├── walkDir.ts                # ✅ Copy this
│   └── shouldIgnore.ts           # ✅ Copy this
└── util/uri.ts                   # ✅ Copy this
```

#### 3. BIG QUERY PROJECT
**Best for:** Database Tab AI (Phase 11)

**Copy:**
- 256 SQL Templates - For Database Tab AI Query Builder
- Template Matching - Semantic search
- Orchestrator - Multi-step workflow execution

**Files:**
```
/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Big Query/
├── BigQuery_Approach1_AI_Architect/src/
│   ├── template_library_full.py    # 256 templates
│   ├── bigquery_engine.py          # AI functions
│   └── template_orchestrator.py    # Workflow engine
```

#### 4. JARVIS AGENT PROJECT
**Best for:** Intelligent Routing (Phase 6-7)

**Copy:**
- Adaptive Router - Routes tasks to optimal models
- Learning System - Tracks success patterns
- RAG Pipeline - Context retrieval
- Permission Layer - Risk assessment

**Files:**
```
/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/
├── adaptive_router.py              # ✅ Phase 7
├── learning_system.py              # ✅ Phase 7
├── rag_pipeline.py                 # ✅ Phase 6
└── permission_layer.py             # ✅ Phase 3
```

### Reusing ElohimOS Primitives

#### 1. Context Storage (Instead of ChromaDB)

**What exists:**
```python
# apps/backend/services/unified_embedder.py
class UnifiedEmbedder:
    """Already handles embeddings for chat, documents, etc."""
```

**How we'll use it:**
```python
from services.unified_embedder import UnifiedEmbedder
from services.memory.chat_memory import ChatMemory

class TerminalContextStore:
    def __init__(self):
        self.embedder = UnifiedEmbedder()
        self.memory = ChatMemory()
```

#### 2. Router (Extend Existing)

```python
# apps/backend/services/adaptive_router.py already exists!
from services.adaptive_router import AdaptiveRouter

class CodeRouter(AdaptiveRouter):
    """Extend existing router for terminal commands"""
    async def route_terminal_input(self, input_text: str, context: Dict) -> str:
        intent = await self.analyze_intent(input_text, context)
        model = await self.select_model(intent)
        return model
```

#### 3. File Paths (Under .neutron_data)

```
~/.neutron_data/
├── workflows.db
├── chat_history/
├── embeddings/
└── (new) code_workspaces/
    └── <user_id>/
        └── <project>/
            └── files...
```

#### 4. RBAC System (Extend Existing)

```python
# apps/backend/utils/permissions.py
CODE_PERMISSIONS = {
    'code.use': ['founder', 'super_admin', 'admin', 'member'],
    'code.edit': ['founder', 'super_admin', 'admin'],
    'code.terminal': ['founder', 'super_admin', 'admin'],
    'code.admin': ['founder', 'super_admin'],
    'code.security': ['founder'],
}
```

#### 5. Audit Logging (Extend Existing)

```python
from utils.audit_logger import log_action, sanitize_for_log

await log_action(user_id, 'code.file.write', sanitize_for_log(file_path))
```

---

## Phase-by-Phase Implementation

### Timeline Overview

| Phase | Name | Duration | Dependencies |
|-------|------|----------|--------------|
| 1 | UI Foundation | 2-3 days | None |
| 2 | Read-Only File Ops | 2-3 days | Phase 1 |
| 3 | Write Operations | 2-3 days | Phase 2 |
| 4 | Chat Integration | 2-3 days | Phase 3 |
| 5 | Terminal Bridge MVP | 4-5 days | Phase 4 |
| 6 | Continue Core Integration | 3-4 days | Phase 5 |
| 7 | Smart Routing | 3-4 days | Phase 6 |
| 8 | Multi-Terminal | 2-3 days | Phase 7 |
| 9 | Admin Panel | 3-4 days | Phase 8 |
| 10 | Polish & Testing | 4-5 days | Phases 1-9 |

**Total: 6-8 weeks**

### Phase 1: UI Foundation (2-3 days)

#### Objectives
- Replace Automation tab with Code tab in navigation
- Create basic Code workspace with sub-tabs
- Add global terminal button to header
- Set up routing and permissions

#### Tasks

**Task 1.1: Update NavigationRail.tsx**
```tsx
// File: apps/frontend/src/components/NavigationRail.tsx
// Replace GitBranch icon with custom Code icon (</>)
// Update NAV_ITEMS: editor → code
// Change label: "Automation" → "Code"
```

**Task 1.2: Create Code Icon**
```tsx
// File: apps/frontend/src/components/icons/CodeIcon.tsx (new)
export function CodeIcon({ size = 20, className = "" }) {
  return (
    <svg width={size} height={size} className={className}>
      {/* </> icon */}
    </svg>
  )
}
```

**Task 1.3: Create CodeWorkspace Component**
```tsx
// File: apps/frontend/src/components/CodeWorkspace.tsx (new)
export function CodeWorkspace({ userRole, canAccessCode, canAccessAdmin }) {
  const [activeTab, setActiveTab] = useState<'code' | 'admin'>('code')

  return (
    <div className="h-full flex flex-col">
      {/* Top Tabs: Code | Admin */}
      <div className="border-b">
        <button onClick={() => setActiveTab('code')}>Code</button>
        {canAccessAdmin && (
          <>
            <div className="separator" />
            <button onClick={() => setActiveTab('admin')}>Admin</button>
          </>
        )}
      </div>

      {/* Content */}
      {activeTab === 'code' && <CodeView />}
      {activeTab === 'admin' && canAccessAdmin && <AdminView />}
    </div>
  )
}
```

**Task 1.4: Create Placeholder Views**
```tsx
// File: apps/frontend/src/components/CodeView.tsx (new)
export function CodeView() {
  return <div>Code View - Coming Soon</div>
}

// File: apps/frontend/src/components/AdminView.tsx (new)
export function AdminView() {
  return <div>Admin View - Coming Soon</div>
}
```

**Task 1.5: Update Global Header**
```tsx
// File: apps/frontend/src/components/GlobalHeader.tsx
// Replace cloud icon with </> terminal icon
<button onClick={handleOpenTerminal} title="Open Terminal">
  <Code size={20} />
</button>
```

**Task 1.6: Add Permissions**
```python
# File: apps/backend/utils/permissions.py
CODE_PERMISSIONS = {
    'code.use': ['founder', 'super_admin', 'admin', 'member'],
}
```

#### Acceptance Criteria
- [ ] Code tab appears in left navigation
- [ ] Code tab icon is `</>`
- [ ] Clicking Code tab opens workspace
- [ ] Code/Admin sub-tabs visible based on permissions
- [ ] Global `</>` button visible in header
- [ ] Founder/Super Admin see both Code and Admin tabs
- [ ] Other roles see only Code tab (if permitted)

---

### Phase 2: Read-Only File Operations (2-3 days)

#### Objectives
- Implement file tree navigation
- Integrate Monaco Editor (read-only)
- Create backend file operations API
- Connect frontend to real file system

#### Backend Tasks

**Task 2.1: File Operations Router**
```python
# File: apps/backend/api/code_operations.py (new)
from fastapi import APIRouter, Depends, HTTPException
from utils.permissions import require_permission
from utils.config_paths import get_neutron_data_path
from utils.audit_logger import log_action
from pathlib import Path

router = APIRouter(prefix="/api/v1/code", tags=["code"])
CODE_WORKSPACE_BASE = get_neutron_data_path() / "code_workspaces"

@router.get("/files")
async def get_file_tree(
    path: str = ".",
    user_id: str = Depends(require_permission("code.use"))
):
    """Get file tree for user workspace (READ-ONLY)"""
    workspace_path = CODE_WORKSPACE_BASE / user_id / path

    if not is_safe_path(workspace_path, CODE_WORKSPACE_BASE / user_id):
        raise HTTPException(400, "Invalid path")

    tree = build_file_tree(workspace_path)
    await log_action(user_id, "code.files.list", str(workspace_path))

    return tree

@router.get("/read")
async def read_file(
    path: str,
    user_id: str = Depends(require_permission("code.use"))
):
    """Read file content (READ-ONLY)"""
    file_path = CODE_WORKSPACE_BASE / user_id / path

    if not is_safe_path(file_path, CODE_WORKSPACE_BASE / user_id):
        raise HTTPException(400, "Invalid path")

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    with open(file_path, 'r') as f:
        content = f.read()

    await log_action(user_id, "code.file.read", str(file_path))

    return {"content": content, "path": path}
```

**Task 2.2: Security Utilities**
```python
# File: apps/backend/utils/file_security.py (new)
from pathlib import Path

def is_safe_path(path: Path, base: Path) -> bool:
    """Prevent directory traversal"""
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False

def build_file_tree(path: Path) -> list:
    """Recursively build file tree"""
    if not path.exists():
        return []

    items = []
    for item in path.iterdir():
        if item.is_dir():
            items.append({
                'name': item.name,
                'type': 'directory',
                'path': str(item),
                'children': build_file_tree(item)
            })
        else:
            items.append({
                'name': item.name,
                'type': 'file',
                'path': str(item),
                'size': item.stat().st_size
            })

    return items
```

#### Frontend Tasks

**Task 2.3: FileTree Component**
```tsx
// File: apps/frontend/src/components/FileTree.tsx (new)
import { useState, useEffect } from 'react'
import { Folder, File, ChevronRight, ChevronDown } from 'lucide-react'

export function FileTree({ onSelect }) {
  const [tree, setTree] = useState([])
  const [expanded, setExpanded] = useState(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadTree()
  }, [])

  const loadTree = async () => {
    const res = await fetch('/api/v1/code/files')
    const data = await res.json()
    setTree(data)
    setLoading(false)
  }

  const toggleExpand = (path) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const renderNode = (node, depth = 0) => (
    <div key={node.path} style={{ paddingLeft: depth * 16 }}>
      {node.type === 'directory' ? (
        <>
          <button onClick={() => toggleExpand(node.path)}>
            {expanded.has(node.path) ? <ChevronDown /> : <ChevronRight />}
            <Folder />
            <span>{node.name}</span>
          </button>
          {expanded.has(node.path) && node.children?.map(child =>
            renderNode(child, depth + 1)
          )}
        </>
      ) : (
        <button onClick={() => onSelect(node.path)}>
          <File />
          <span>{node.name}</span>
        </button>
      )}
    </div>
  )

  if (loading) return <div>Loading files...</div>

  return <div>{tree.map(node => renderNode(node))}</div>
}
```

**Task 2.4: MonacoEditor Component**
```tsx
// File: apps/frontend/src/components/MonacoEditor.tsx (new)
import { useEffect, useState } from 'react'
import Editor from '@monaco-editor/react'

export function MonacoEditor({ file }) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (file) {
      loadFile(file)
    }
  }, [file])

  const loadFile = async (path) => {
    setLoading(true)
    const res = await fetch(`/api/v1/code/read?path=${encodeURIComponent(path)}`)
    const data = await res.json()
    setContent(data.content)
    setLoading(false)
  }

  if (!file) {
    return <div>Select a file to view</div>
  }

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <Editor
      height="100%"
      defaultLanguage="typescript"
      value={content}
      theme="vs-dark"
      options={{
        readOnly: true,  // READ-ONLY for Phase 2
        minimap: { enabled: false },
        fontSize: 14,
      }}
    />
  )
}
```

**Task 2.5: Wire Up in CodeView**
```tsx
// File: apps/frontend/src/components/CodeView.tsx
export function CodeView() {
  const [selectedFile, setSelectedFile] = useState(null)

  return (
    <div className="flex h-full">
      {/* Left pane: File tree */}
      <div className="w-64 border-r">
        <FileTree onSelect={setSelectedFile} />
      </div>

      {/* Right pane: Monaco */}
      <div className="flex-1">
        <MonacoEditor file={selectedFile} />
      </div>
    </div>
  )
}
```

#### Acceptance Criteria
- [ ] Code tab loads
- [ ] File tree displays user workspace
- [ ] Clicking file loads in Monaco (read-only)
- [ ] Syntax highlighting works
- [ ] Path validation prevents traversal
- [ ] Audit log records file access
- [ ] Permission checks enforce `code.use`

---

### Phase 3: Write Operations (2-3 days)

#### Objectives
- Add write capability with safety checks
- Implement diff preview before write
- Add save confirmation
- Enforce `code.edit` permission

#### Backend Tasks

**Task 3.1: Write Endpoint with Dry-Run**
```python
@router.post("/write")
async def write_file(
    request: WriteFileRequest,
    dry_run: bool = False,
    user_id: str = Depends(require_permission("code.edit"))
):
    """Write file content with diff preview"""
    file_path = CODE_WORKSPACE_BASE / user_id / request.path

    if not is_safe_path(file_path, CODE_WORKSPACE_BASE / user_id):
        raise HTTPException(400, "Invalid path")

    # Generate diff
    old_content = ""
    if file_path.exists():
        with open(file_path, 'r') as f:
            old_content = f.read()

    diff = generate_diff(old_content, request.content)

    # Dry run: return diff only
    if dry_run:
        return {"diff": diff, "path": request.path}

    # Write file
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(request.content)

    await log_action(user_id, "code.file.write", str(file_path))

    return {"success": True, "path": request.path}
```

#### Frontend Tasks

**Task 3.2: Save Button + Diff Preview**
```tsx
// In MonacoEditor component
const [hasChanges, setHasChanges] = useState(false)
const [showDiff, setShowDiff] = useState(false)

const handleSave = async () => {
  // First: Get diff preview
  const diffRes = await fetch('/api/v1/code/write?dry_run=true', {
    method: 'POST',
    body: JSON.stringify({ path: file, content })
  })
  const { diff } = await diffRes.json()

  // Show diff modal for confirmation
  setShowDiff(diff)
}

const confirmSave = async () => {
  // Actually write
  await fetch('/api/v1/code/write', {
    method: 'POST',
    body: JSON.stringify({ path: file, content })
  })

  toast.success('File saved')
}

// In Editor options:
options={{
  readOnly: false,  // NOW EDITABLE
  // ...
}}
```

#### Acceptance Criteria
- [ ] Can edit files in Monaco
- [ ] Save shows diff preview first
- [ ] Must confirm before writing
- [ ] Audit log records writes
- [ ] Permission `code.edit` enforced

---

### Phase 4: Chat Integration (2-3 days)

#### Objectives
- Connect Chat to file context
- Reuse existing chat service
- Enable reasoning mode
- Auto-save chat sessions

#### Backend Tasks

**Task 4.1: Extend Chat Endpoint**
```python
# In existing chat_service.py
@router.post("/chat")
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """Enhanced to accept code context"""
    context_parts = []

    # Add file context if provided
    if request.file_context:
        file_content = await read_file_content(request.file_context.path)
        context_parts.append(f"Current file:\n{file_content}")

    # Build full prompt
    full_context = "\n\n".join(context_parts)
    enhanced_prompt = f"{full_context}\n\nUser: {request.message}"

    response = await generate_chat_response(enhanced_prompt, user_id)

    return {"response": response}
```

#### Frontend Tasks

**Task 4.2: CodeChat Component**
```tsx
// File: apps/frontend/src/components/CodeChat.tsx (new)
export function CodeChat({ fileContext }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')

  const handleSend = async () => {
    const response = await fetch('/api/v1/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: input,
        file_context: fileContext ? { path: fileContext } : null
      })
    })

    const data = await response.json()

    setMessages([
      ...messages,
      { role: 'user', content: input },
      { role: 'assistant', content: data.response }
    ])

    setInput('')
  }

  return (
    <div className="h-80 border-t flex flex-col">
      {/* Context indicator */}
      {fileContext && (
        <div className="p-2 bg-blue-50">
          📄 Context: {fileContext}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((msg, i) => (
          <div key={i}>{msg.content}</div>
        ))}
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && handleSend()}
          placeholder="Ask about this code..."
        />
      </div>
    </div>
  )
}
```

#### Acceptance Criteria
- [ ] Chat aware of current file
- [ ] Chat provides context-aware responses
- [ ] Chat sessions save automatically

---

### Phase 5: System Terminal Launcher (MVP) (4-5 days)

#### Objectives
- Spawn native OS terminals (Warp/iTerm2/Terminal.app) via authenticated API
- Enforce JWT + RBAC on spawn/close/list endpoints
- Add audit logging for spawn/close; cap concurrent sessions per user
- Add gentle rate limiting for spawn operations
- Track sessions for audit/UX (no in-browser I/O yet)

#### Backend Tasks

**Task 5.1: Terminal Bridge Service (spawn + audit, no WS I/O)**
```python
# File: apps/backend/services/terminal_bridge.py (new)
import pty
import os
import asyncio
import subprocess
from dataclasses import dataclass

@dataclass
class TerminalSession:
    id: str
    user_id: str
    master: int
    process: subprocess.Popen
    active: bool = True

class TerminalBridge:
    def __init__(self):
        self.sessions = {}
        self.context_store = TerminalContextStore()

    async def spawn_terminal(self, user_id: str) -> TerminalSession:
        """Spawn new terminal (system shell)"""
        master, slave = pty.openpty()

        process = subprocess.Popen(
            ['/bin/bash'],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            preexec_fn=os.setsid
        )

        session = TerminalSession(
            id=generate_id(),
            user_id=user_id,
            master=master,
            process=process
        )

        self.sessions[session.id] = session
        # No WS capture yet; session tracked for audit/UX only
        await log_action(user_id, "code.terminal.spawn", session.id)

        return session

    # (Defer PTY I/O and WS broadcasting to optional Socket Bridge phase)
```

**Task 5.2: HTTP Endpoints (JWT-protected)**
```python
# File: apps/backend/api/terminal_api.py
@router.post("/spawn")  # Auth: get_current_user
@router.post("/spawn-system")  # Auth: get_current_user
@router.get("/sessions")      # Auth: get_current_user (own sessions)
@router.delete("/{terminal_id}")  # Auth + ownership check
```

#### Acceptance Criteria
- [ ] `</>` spawns native OS terminal for the user
- [ ] Spawn/close/list endpoints require valid JWT and enforce ownership
- [ ] Audit log entries for spawn/close with session IDs
- [ ] Basic rate limiting on spawn requests
- [ ] Max concurrent sessions per user enforced (e.g., 3)

---

### Phase 6: Continue Core Integration (3-4 days)

#### Objectives
- Add Continue Core as LLM spine
- Implement IDE interface
- Connect to terminal bridge

#### Tasks

**Task 6.1: Install Continue**
```bash
npm install @continuedev/core
```

**Task 6.2: Implement IDE Interface**
```python
# File: apps/backend/integrations/continue_ide.py (new)
from continuedev.core import IDE

class ElohimOSIDE(IDE):
    """IDE interface for ElohimOS"""

    async def readFile(self, fileUri: str) -> str:
        """Read file from workspace"""
        return await read_file_content(fileUri)

    async def writeFile(self, path: str, contents: str):
        """Write file to workspace"""
        await write_file_content(path, contents)

    async def getTerminalContents(self) -> str:
        """Get terminal output"""
        return await context_store.get_recent_terminal_output()
```

**Task 6.3: LLM Handler**
```python
# File: apps/backend/services/llm_handler.py (new)
from continuedev.core import Core

class LLMHandler:
    def __init__(self):
        self.continue_core = Core(
            ide=ElohimOSIDE(),
            config={
                'models': [
                    {
                        'title': 'Qwen Coder',
                        'provider': 'ollama',
                        'model': 'qwen2.5-coder:32b'
                    }
                ]
            }
        )

    async def generate(self, prompt: str, model: str = None) -> str:
        """Generate response using Continue"""
        response = await self.continue_core.chat(
            messages=[{'role': 'user', 'content': prompt}],
            model=model
        )
        return response
```

#### Acceptance Criteria
- [ ] Continue Core integrated
- [ ] Can route to different models
- [ ] Natural language commands work in terminal

---

### Phase 7: Smart Routing (3-4 days)

#### Objectives
- Integrate JARVIS adaptive routing
- Implement learning system
- Track success patterns
- Optimize model selection

#### Tasks

**Task 7.1: Copy JARVIS Files**
```bash
# Copy from Jarvis Agent
cp /path/to/adaptive_router.py apps/backend/integrations/jarvis/
cp /path/to/learning_system.py apps/backend/integrations/jarvis/
```

**Task 7.2: Extend Router**
```python
# File: apps/backend/services/code_router.py (new)
from integrations.jarvis.adaptive_router import AdaptiveRouter

class CodeRouter(AdaptiveRouter):
    """Extend JARVIS router for Code tab"""

    MODEL_ROUTING = {
        'code_generation': 'qwen2.5-coder:32b',
        'debugging': 'deepseek-r1:32b',
        'refactoring': 'codestral:22b',
        'quick_task': 'llama3.1:8b',
    }

    async def route_terminal_input(self, input_text: str, context: dict) -> str:
        """Determine best model for terminal input"""
        intent = await self.analyze_intent(input_text, context)
        model = self.MODEL_ROUTING.get(intent.type, 'llama3.1:8b')
        return model
```

#### Acceptance Criteria
- [ ] Smart routing active
- [ ] Models selected based on task type
- [ ] Learning tracks success patterns

---

### Phase 8: Multi-Terminal (2-3 days)

#### Objectives
- Allow multiple terminals per user
- Terminal manager UI
- Per-terminal model selection

#### Backend Tasks

```python
# In terminal_bridge.py
MAX_TERMINALS_PER_USER = 5

async def spawn_terminal(self, user_id: str) -> TerminalSession:
    """Spawn with limit check"""
    user_terminals = [s for s in self.sessions.values()
                      if s.user_id == user_id and s.active]
    if len(user_terminals) >= MAX_TERMINALS_PER_USER:
        raise HTTPException(429, f"Maximum {MAX_TERMINALS_PER_USER} terminals")
```

#### Frontend Tasks

```tsx
// Terminal manager UI
export function TerminalManager() {
  const [terminals, setTerminals] = useState([])

  const openNewTerminal = async () => {
    const res = await fetch('/api/v1/code/terminal/spawn', { method: 'POST' })
    const terminal = await res.json()
    setTerminals([...terminals, terminal])
  }

  return (
    <div>
      {terminals.map(t => (
        <TerminalTab key={t.id} terminal={t} />
      ))}
      <button onClick={openNewTerminal}>+ New Terminal</button>
    </div>
  )
}
```

#### Acceptance Criteria
- [ ] Can open multiple terminals
- [ ] Terminal list shows active sessions
- [ ] Each terminal can have different model

---

### Phase 9: Admin Panel (3-4 days)

#### Objectives
- Build Admin tab UI
- System health dashboard
- User management
- Logs viewer
- Security panel (Founder only)

#### Components

**System Health:**
```tsx
export function SystemHealthDashboard() {
  const { data: health } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: () => fetch('/api/v1/admin/health').then(r => r.json()),
    refetchInterval: 5000
  })

  return (
    <div>
      <HealthCard title="Backend API" status={health?.backend} />
      <HealthCard title="Database" status={health?.database} />
      <HealthCard title="Ollama" status={health?.ollama} />
    </div>
  )
}
```

**User Management:**
```tsx
export function UserManagementPanel() {
  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: () => fetch('/api/v1/admin/users').then(r => r.json())
  })

  return (
    <div>
      {users?.map(user => (
        <UserRow key={user.id} user={user} />
      ))}
    </div>
  )
}
```

**Security Panel (Founder Only):**
```tsx
export function SecurityPanel() {
  return (
    <div className="bg-red-50 border border-red-200">
      <h2>Security Controls (Founder Only)</h2>
      <SecurityCard title="Audit Logs" action="View Logs" />
      <SecurityCard title="Encryption Keys" action="Manage Keys" />
    </div>
  )
}
```

#### Acceptance Criteria
- [ ] Admin tab visible to Super Admin + Founder
- [ ] System health dashboard displays metrics
- [ ] User list shows all users
- [ ] Logs viewer displays system logs
- [ ] Security panel visible to Founder only

---

### Phase 10: Polish & Testing (4-5 days)

#### Objectives
- UI/UX refinements
- Performance optimization
- Comprehensive testing
- Documentation
- Bug fixes

#### Tasks

**Task 10.1: UI Polish**
- Consistent styling
- Smooth animations
- Loading states
- Error states
- Empty states

**Task 10.2: Performance Optimization**
- Code splitting for Monaco
- Virtualized lists
- Debounce search
- Memoize components

**Task 10.3: Testing**
- Unit tests (backend)
- Integration tests
- E2E tests (Playwright)
- Performance benchmarks

**Task 10.4: Documentation**
- User guide
- Developer docs
- API documentation
- Deployment guide

#### Acceptance Criteria
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] No critical bugs
- [ ] Ready for production

---

### Phase 11: Database Tab AI Query Builder (Optional Enhancement)

#### Objectives
- Add AI-powered query building to Database Tab
- Create learning loop with template library
- Enable 10-15 second query reuse

#### The Three Workflows

**Workflow 1: First-Time User (AI-Assisted)**
1. Upload Excel → Brute force discovery runs automatically
2. Click "Use AI" button → Terminal opens
3. Tell AI what you want → AI tries 256 templates + variations
4. AI shows working query → User verifies
5. Query appears in SQLEditor, results in ResultsTable
6. Template auto-added to BOTH libraries (user's + AI's)

**Workflow 2: Experienced User (Quick Template)**
1. Upload Excel → Same filename/structure
2. Click Library dropdown → Select saved template
3. Click Run → Results appear instantly (10-15 seconds total!)

**Workflow 3: Manual SQL (Power User)**
1. Upload Excel → Review schema
2. Write SQL manually in SQLEditor
3. Iterate and run

#### Key Components

**Template Loader:**
```python
# File: apps/backend/services/query_template_loader.py
TEMPLATE_PATHS = [
    Path.home() / "Library/CloudStorage/.../Big Query",
    Path.home() / "Library/CloudStorage/.../Jarvis Agent/templates",
    PATHS.data_dir / "user_templates"
]

class QueryTemplateLoader:
    def __init__(self):
        self.templates = self._load_all_templates()

    def find_relevant_templates(self, user_intent: str, schema: dict):
        """Find templates matching user intent and schema"""
        # Use LLM to match intent to template categories
        # Filter by available columns
        return top_templates
```

**AI Orchestrator:**
```python
# File: apps/backend/services/query_ai_orchestrator.py
class QueryAIOrchestrator:
    async def run_interactive_session(self):
        """Main interactive loop in terminal"""
        print("🤖 What do you want to know about your data?")
        user_intent = input("> ")

        for iteration in range(5):
            # Find relevant templates
            templates = self.template_loader.find_relevant_templates(
                user_intent, schema
            )

            # Generate query variations
            queries = await self._generate_query_variations(
                user_intent, schema, templates
            )

            # Execute in parallel
            for query in queries:
                try:
                    result = self.data_engine.execute_sql(query)
                    if result['row_count'] > 0:
                        print(f"✅ Found working query!\n{query}")

                        response = input("Does this look right? (yes/no)\n> ")

                        if response == 'yes':
                            await self._push_to_database_tab(query, result)
                            return {'success': True}
                except Exception as e:
                    continue
```

**Frontend Integration:**
```tsx
// In SQLEditor.tsx - Add "Use AI" button
<button
  onClick={handleUseAI}
  className="bg-gradient-to-r from-purple-500 to-blue-500 text-white"
>
  <Sparkles className="w-4 h-4" />
</button>

const handleUseAI = async () => {
  await fetch('/api/v1/data/use-ai', {
    method: 'POST',
    body: JSON.stringify({ dataset_id: sessionId })
  })

  toast.info('🤖 Check your terminal for AI query builder!')
}
```

#### Acceptance Criteria
- [ ] "Use AI" button appears in SQLEditor
- [ ] AI loads 256 templates
- [ ] Queries execute in parallel
- [ ] User can verify/reject results
- [ ] Successful queries save to both libraries
- [ ] Subsequent uploads can use saved templates

---

## Technical Specifications

### Frontend Stack
- **React 18.2.0** - UI framework
- **TypeScript 5.3.2** - Type-safe JavaScript
- **Vite 5.4.20** - Build tool
- **Zustand 4.4.6** - State management
- **Monaco Editor 4.7.0** - Code editor
- **Axios 1.6.2** - HTTP client
- **Tailwind CSS 3.3.5** - Styling
- **Lucide React 0.292.0** - Icons

### Backend Stack
- **FastAPI 0.115.0** - Async web framework
- **Uvicorn 0.32.0** - ASGI server
- **DuckDB 1.1.3** - In-memory OLAP database
- **Pandas 2.2.3** - Data manipulation
- **PyArrow 18.0+** - Columnar data
- **PyJWT 2.9.0** - Authentication
- **PyNaCl 1.5.0+** - Cryptography
- **WebSockets 12.0+** - Real-time communication
- **MLX (optional)** - Apple Silicon ML

### File Structure

#### Frontend
```
apps/frontend/src/
├── components/
│   ├── NavigationRail.tsx (modified)
│   ├── GlobalHeader.tsx (modified)
│   ├── icons/
│   │   └── CodeIcon.tsx (new)
│   ├── CodeWorkspace.tsx (new)
│   ├── CodeView.tsx (new)
│   ├── AdminView.tsx (new)
│   ├── FileTree.tsx (new)
│   ├── ChatHistory.tsx (new)
│   ├── MonacoEditor.tsx (new)
│   ├── CodeChat.tsx (new)
│   └── admin/
│       ├── SystemHealthDashboard.tsx (new)
│       ├── UserManagementPanel.tsx (new)
│       └── LogsViewer.tsx (new)
├── hooks/
│   ├── useFileTree.ts (new)
│   ├── useTerminal.ts (new)
│   └── useTerminalContext.ts (new)
└── stores/
    ├── navigationStore.ts (modified)
    └── codeStore.ts (new)
```

#### Backend
```
apps/backend/
├── api/
│   ├── code_operations.py (new)
│   ├── terminal_api.py (new)
│   ├── admin_panel.py (new)
│   └── chat_service.py (extended)
├── services/
│   ├── terminal_bridge.py (new)
│   ├── context_manager.py (new)
│   ├── llm_handler.py (new)
│   └── code_router.py (new)
├── integrations/
│   ├── continue_ide.py (new)
│   ├── jarvis/
│   │   ├── adaptive_router.py (copied)
│   │   └── learning_system.py (copied)
│   └── bigquery_templates.py (new)
└── utils/
    ├── file_security.py (new)
    └── walk_dir.py (new)
```

### Database Schema

**New Tables:**
```sql
-- Terminal sessions
CREATE TABLE terminal_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    last_activity TIMESTAMP
);

-- Code chat sessions
CREATE TABLE code_chat_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    file_context TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Learning patterns (from JARVIS)
CREATE TABLE learning_patterns (
    pattern_hash TEXT PRIMARY KEY,
    command TEXT,
    tool_used TEXT,
    success_count INTEGER,
    failure_count INTEGER,
    confidence REAL
);
```

### API Endpoints

#### Code Operations
```
GET    /api/v1/code/files                 - List files
GET    /api/v1/code/read                  - Read file
POST   /api/v1/code/write                 - Write file
DELETE /api/v1/code/delete                - Delete file
GET    /api/v1/code/workspace              - Workspace info
```

#### Terminal Operations
```
POST   /api/v1/code/terminal/spawn        - Spawn terminal
GET    /api/v1/code/terminal/list         - List terminals
DELETE /api/v1/code/terminal/{id}         - Close terminal
WS     /ws/terminal/{id}                  - Terminal I/O
```

#### Chat Operations
```
POST   /api/v1/code/chat                  - Send message
GET    /api/v1/code/chats                 - List sessions
GET    /api/v1/code/chats/{id}            - Get session
DELETE /api/v1/code/chats/{id}            - Delete session
```

#### Admin Operations
```
GET    /api/v1/admin/health               - System health
GET    /api/v1/admin/users                - List users
POST   /api/v1/admin/users/{id}/perms     - Update permissions
GET    /api/v1/admin/logs                 - System logs
GET    /api/v1/admin/security/audit       - Audit logs (Founder only)
```

---

## Security & RBAC

### Permission Structure

```python
CODE_PERMISSIONS = {
    'code.use': {
        'roles': ['founder', 'super_admin', 'admin', 'member'],
        'description': 'Access Code tab'
    },
    'code.edit': {
        'roles': ['founder', 'super_admin', 'admin'],
        'description': 'Edit files in workspace'
    },
    'code.terminal': {
        'roles': ['founder', 'super_admin', 'admin'],
        'description': 'Open terminal sessions'
    },
    'code.admin': {
        'roles': ['founder', 'super_admin'],
        'description': 'Access Admin panel'
    },
    'code.security': {
        'roles': ['founder'],
        'description': 'Access security controls'
    },
}
```

### Audit Logging

All Code tab actions logged:
- `code.files.list` (path)
- `code.file.read` (path)
- `code.file.write` (path, size, diff_lines)
- `code.terminal.spawn` (terminal_id)
- `code.terminal.close` (terminal_id)
- `code.admin.users.list`
- `code.admin.logs.view`

### Security Patterns

**Path Validation:**
```python
def is_safe_path(path: Path, base: Path) -> bool:
    """Prevent directory traversal"""
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False
```

**Rate Limiting:**
```python
await check_rate_limit(user_id, 'terminal_spawn', max_per_hour=10)
# Also apply per-IP limiter on /spawn endpoints
```

**Risk Assessment (from JARVIS):**
```python
class RiskLevel(Enum):
    SAFE = (0, "🟢", "Safe")
    LOW = (1, "🟡", "Low Risk")
    MEDIUM = (2, "🟠", "Medium Risk")
    HIGH = (3, "🔴", "High Risk")
    CRITICAL = (4, "⚠️", "Critical")
```

---

## Testing Strategy

### Unit Tests (70% coverage)
- Every component has tests
- Every API endpoint has tests
- Every service has tests
- Mock external dependencies

### Integration Tests (20% coverage)
- Terminal Bridge ↔ Context Manager
- File Operations ↔ Monaco Editor
- Chat ↔ Terminal Context

### E2E Tests (10% coverage)
- Complete user workflows
- Terminal to Chat flow
- File edit flow
- Admin panel operations

### Manual Testing
- Cross-browser testing
- Performance testing
- Accessibility testing
- Security penetration testing

---

## Future Enhancements

### Phase 12+: Advanced Features
- **Socket Bridge (Optional):** Enable PTY I/O over WebSocket for in‑browser terminal; require JWT on query param, enforce session ownership, and use xterm.js on the frontend
- **Collaborative Terminals:** Multiple users in same session
- **Terminal Playback:** Record and replay sessions
- **Advanced Code Intelligence:** Deeper AST analysis
- **Custom LLM Training:** Fine-tune on user's codebase
- **Mobile Support:** Terminal access from mobile
- **Plugin System:** Community extensions
- **Git Integration:** Visual git operations
- **Debugger Integration:** Step-through with AI
- **Performance Profiling:** Identify bottlenecks with AI

### Success Metrics

**Technical Metrics:**
- Terminal spawn time: < 500ms
- Context query time: < 100ms
- Chat response time: < 2s
- Uptime: > 99.9%
- Test coverage: > 80%

**User Metrics:**
- Time saved vs VS Code: 30%+
- Context switches reduced: 80%+
- User satisfaction: > 4.5/5

**Mission Metrics:**
- Offline functionality: 100%
- Security incidents: 0
- Data breaches: 0
- Lives protected: Immeasurable 🙏

---

## Conclusion

This roadmap provides a comprehensive, phase-by-phase plan for implementing the ElohimOS Code Tab. Each phase is:

1. **Small enough** to avoid token limit issues
2. **Independently testable** with clear acceptance criteria
3. **Builds on previous phases** in a logical progression
4. **Production-focused** with security and performance in mind
5. **Mission-aligned** with offline-first, secure, persecution-resistant design

**Remember:** This isn't just another IDE. This is infrastructure for the persecuted church. Code with that weight. Build with that purpose. Test like lives depend on it. Because they do.

---

## Next Steps

1. Review this roadmap
2. Begin Phase 1: UI Foundation
3. Stay disciplined with small, focused changes
4. Test thoroughly at each phase
5. Ship incrementally
6. Iterate based on feedback

**The future isn't VS Code. It's this. Let's build it. 🚀**

---

*Master Roadmap Version: 1.0 Unified*
*Last Updated: 2025-11-05*
*Status: Ready for Implementation*
*Source: Consolidated from all roadmap documents*
