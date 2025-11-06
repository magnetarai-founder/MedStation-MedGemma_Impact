# Phase 5: Terminal Bridge MVP - Implementation Complete

**Date:** November 5, 2025
**Status:** ✅ IMPLEMENTED

---

## What Was Built

### Backend (Python)

#### 1. Terminal Bridge Service
**File:** `apps/backend/services/terminal_bridge.py`

**Features:**
- PTY (Pseudo-Terminal) management
- Terminal session lifecycle (spawn, capture, close)
- Real-time output capture with background async tasks
- Context storage for AI/LLM integration
- Broadcast system for WebSocket clients
- Graceful terminal shutdown (SIGTERM → SIGKILL)
- Session management with user ownership
- Output buffering (last 1000 lines)

**Key Classes:**
- `TerminalSession` - Dataclass for session state
- `TerminalContextStore` - Stores terminal output for AI context
- `TerminalBridge` - Main service class (singleton: `terminal_bridge`)

**Methods:**
- `spawn_terminal(user_id, shell, cwd)` - Create new PTY session
- `write_to_terminal(terminal_id, data)` - Send user input
- `resize_terminal(terminal_id, rows, cols)` - Resize PTY
- `close_terminal(terminal_id)` - Graceful shutdown
- `get_context(terminal_id, lines)` - Get output for AI
- `list_sessions(user_id)` - List user's terminals

#### 2. Terminal API Router
**File:** `apps/backend/api/terminal_api.py`

**Endpoints:**
- `POST /api/v1/terminal/spawn` - Spawn new terminal
- `GET /api/v1/terminal/sessions` - List user's terminals
- `GET /api/v1/terminal/{id}` - Get terminal info
- `DELETE /api/v1/terminal/{id}` - Close terminal
- `GET /api/v1/terminal/{id}/context` - Get context for AI
- `WS /api/v1/terminal/ws/{id}` - WebSocket for real-time I/O
- `POST /api/v1/terminal/{id}/resize` - Resize terminal (HTTP fallback)

**WebSocket Protocol:**
```json
// Client -> Server
{"type": "input", "data": "ls -la\n"}
{"type": "resize", "rows": 24, "cols": 80}

// Server -> Client
{"type": "output", "data": "total 48\ndrwxr-xr-x..."}
{"type": "error", "message": "Terminal not found"}
```

#### 3. Permissions Integration
**File:** `apps/backend/api/permissions.py`

**New Permissions:**
- `Permission.CODE_TERMINAL` - Access to terminal feature
- `Permission.CODE_USE` - Use Code Tab
- `Permission.CODE_WRITE` - Write file operations
- `Permission.CODE_ADMIN` - Admin panel access

**Role Access:**
- **Founder/Super Admin:** Full access (all permissions)
- **Admin:** code.use, code.write, code.terminal
- **Member:** code.use, code.terminal (read-only files)
- **Viewer/Guest:** No Code Tab access

#### 4. Main App Registration
**File:** `apps/backend/api/main.py` (Line 438-444)

```python
# Terminal Bridge API (Phase 5)
try:
    from terminal_api import router as terminal_router
    app.include_router(terminal_router)
    services_loaded.append("Terminal Bridge")
except ImportError as e:
    logger.warning(f"Could not import terminal_api router: {e}")
```

---

### Frontend (React/TypeScript)

#### 1. TerminalView Component
**File:** `apps/frontend/src/components/TerminalView.tsx`

**Features:**
- xterm.js integration for full terminal emulation
- WebSocket connection to backend PTY
- Auto-resize with FitAddon
- Clickable URLs with WebLinksAddon
- Connection status indicator
- Maximize/minimize toggle
- Graceful disconnect handling
- Auto-spawn on mount (optional)
- Custom dark theme matching ElohimOS

**Props:**
```typescript
interface TerminalViewProps {
  terminalId?: string          // Existing terminal ID
  onClose?: () => void          // Close callback
  autoSpawn?: boolean           // Auto-spawn on mount (default: true)
  shell?: string                // Shell to use (/bin/zsh, /bin/bash)
  cwd?: string                  // Working directory
}
```

**Dependencies Added:**
- `xterm` - Terminal emulator
- `xterm-addon-fit` - Auto-resize addon
- `xterm-addon-web-links` - Clickable URLs

#### 2. TerminalModal Component
**File:** `apps/frontend/src/components/TerminalModal.tsx`

**Features:**
- Modal wrapper for terminal
- Opened from global </> button
- Full-screen overlay with max-width
- Close on ESC (via onClose)

**Usage:**
```tsx
<TerminalModal
  isOpen={showTerminal}
  onClose={() => setShowTerminal(false)}
/>
```

---

## Installation & Setup

### Backend Dependencies
All dependencies are Python standard library:
- `pty` - PTY management
- `subprocess` - Process spawning
- `asyncio` - Async I/O
- `select` - Non-blocking reads

**No additional pip installs required**

### Frontend Dependencies
```bash
cd apps/frontend
npm install xterm xterm-addon-fit xterm-addon-web-links
```

**Installed:**
- xterm@5.3.0
- xterm-addon-fit@0.8.0
- xterm-addon-web-links@0.9.0

---

## How to Use

### Opening a Terminal

#### From Global Header Button
```tsx
// In GlobalHeader.tsx or similar
import { TerminalModal } from './TerminalModal'

const [showTerminal, setShowTerminal] = useState(false)

// Button
<button onClick={() => setShowTerminal(true)}>
  <Code size={20} /> {/* </> icon */}
</button>

// Modal
<TerminalModal
  isOpen={showTerminal}
  onClose={() => setShowTerminal(false)}
/>
```

#### Programmatically
```tsx
import { TerminalView } from './TerminalView'

// Embedded in layout
<TerminalView
  autoSpawn={true}
  shell="/bin/zsh"
  cwd="/Users/you/projects"
  onClose={handleClose}
/>
```

### Backend API Usage

#### Spawn Terminal
```bash
curl -X POST http://localhost:8000/api/v1/terminal/spawn \
  -H "Cookie: session_token=..." \
  -H "Content-Type: application/json" \
  -d '{"shell": "/bin/zsh", "cwd": "/tmp"}'

# Response:
{
  "terminal_id": "term_a1b2c3d4e5f6",
  "websocket_url": "/api/v1/terminal/ws/term_a1b2c3d4e5f6",
  "created_at": "2025-11-05T10:30:00",
  "pid": 12345
}
```

#### Connect WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/terminal/ws/term_a1b2c3d4e5f6')

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data)
  if (msg.type === 'output') {
    console.log(msg.data)
  }
}

// Send input
ws.send(JSON.stringify({
  type: 'input',
  data: 'ls -la\n'
}))
```

#### Get Terminal Context (for AI)
```bash
curl http://localhost:8000/api/v1/terminal/term_xyz/context?lines=100 \
  -H "Cookie: session_token=..."

# Response:
{
  "terminal_id": "term_xyz",
  "lines": 100,
  "context": "$ ls\nfile1.txt file2.py...\n$ pwd\n/home/user\n..."
}
```

---

## Security Features

### 1. Permission Checks
All endpoints require `code.terminal` permission via `require_permission()` decorator.

### 2. User Ownership
- Each terminal session is owned by the user who spawned it
- Only owner can access their terminals
- Prevents cross-user terminal access

### 3. Audit Logging
```python
await log_action(user_id, 'terminal.spawn', {'terminal_id': session.id})
await log_action(user_id, 'terminal.close', {'terminal_id': terminal_id})
```

### 4. Graceful Cleanup
- SIGTERM sent first (graceful)
- 0.5s wait
- SIGKILL if still running (force)
- PTY master FD closed
- Session removed from memory

### 5. Process Isolation
- Each terminal runs in its own process
- Uses `preexec_fn=os.setsid` for process group
- Environment variables isolated per session

---

## Technical Details

### PTY Management

**How it works:**
1. `pty.openpty()` creates master/slave FD pair
2. Slave FD passed to subprocess (stdin/stdout/stderr)
3. Master FD used for I/O from parent process
4. `select()` for non-blocking reads
5. Output captured and broadcast to WebSocket clients

**Key Challenge Solved:**
- Blocking reads from PTY would freeze async event loop
- Solution: Use `select()` with 0.1s timeout + `run_in_executor()` for `os.read()`

### WebSocket Lifecycle

```
Frontend                Backend                 PTY
   |                       |                      |
   |-- POST /spawn ------->|                      |
   |<-- terminal_id -------|-- pty.openpty() --->|
   |                       |<-- master, slave ----|
   |                       |-- subprocess.Popen ->|
   |                       |                      |
   |-- WS connect -------->|                      |
   |<-- accept ------------|                      |
   |                       |-- register_callback -|
   |                       |                      |
   |<-- output ------------|<-- os.read(master) --|
   |-- input ------------->|-- os.write(master) ->|
   |                       |                      |
   |-- disconnect -------->|                      |
   |                       |-- unregister --------|
   |                       |-- SIGTERM/SIGKILL -->|
```

### Context Capture for AI

Terminal output is stored in `TerminalContextStore`:
- Last 1000 lines buffered per terminal
- Timestamped for replay/analysis
- Accessible via `/context` endpoint
- Used for AI to understand recent commands

**Future Integration:**
- Continue.dev `getTerminalContents()` will use this
- Smart routing can analyze command patterns
- Learning system can improve suggestions

---

## Testing

### Manual Testing

1. **Start Backend:**
```bash
cd apps/backend/api
python main.py
```

2. **Start Frontend:**
```bash
cd apps/frontend
npm run dev
```

3. **Open Browser:**
- Navigate to http://localhost:5173
- Click Code tab
- Click </> button in header
- Terminal should appear

4. **Test Commands:**
```bash
ls -la
pwd
echo "Hello from ElohimOS Terminal"
python3 --version
```

### Automated Testing (TODO)

Create test file: `apps/backend/api/test_terminal_bridge.py`

```python
import pytest
from services.terminal_bridge import TerminalBridge

@pytest.mark.asyncio
async def test_spawn_terminal():
    bridge = TerminalBridge()
    session = await bridge.spawn_terminal(user_id="test_user")
    assert session.id.startswith("term_")
    assert session.active == True
    await bridge.close_terminal(session.id)

@pytest.mark.asyncio
async def test_write_to_terminal():
    bridge = TerminalBridge()
    session = await bridge.spawn_terminal(user_id="test_user")
    await bridge.write_to_terminal(session.id, "echo test\n")
    # TODO: Capture and verify output
    await bridge.close_terminal(session.id)
```

---

## Acceptance Criteria (From Roadmap)

- ✅ Click `</>` spawns terminal
- ✅ Can type commands
- ✅ See output in real-time
- ✅ Terminal I/O captured to context
- ✅ Can close terminal

**All Phase 5 acceptance criteria met!**

---

## Next Steps (Phase 6)

With Terminal Bridge complete, we can now proceed to:

### Phase 6: Continue Core Integration (3-4 days)
- Implement IDE interface
- Connect to terminal bridge via `getTerminalContents()`
- Tool system for file operations
- MCP (Model Context Protocol) integration

### Phase 7: Smart Routing (3-4 days)
- Route tasks between Continue, Terminal, and File operations
- Learning system for operation routing
- Context analysis

### Phase 8: Multi-Terminal (2-3 days)
- Terminal tab management
- Multiple PTY instances
- Session persistence

---

## Known Limitations

1. **WebSocket Authentication:**
   - Currently relies on session ownership validation
   - TODO: Add proper WebSocket token-based auth

2. **Session Persistence:**
   - Terminals close when WebSocket disconnects
   - TODO: Keep terminals alive for reconnection
   - TODO: Store sessions in database

3. **Resource Limits:**
   - No max terminal count per user
   - TODO: Add configurable limits

4. **Terminal Features:**
   - No copy/paste support yet
   - No search functionality
   - TODO: Add xterm.js search addon
   - TODO: Add clipboard integration

---

## File Summary

### Backend Files Created
- `apps/backend/services/terminal_bridge.py` (366 lines)
- `apps/backend/api/terminal_api.py` (264 lines)

### Backend Files Modified
- `apps/backend/api/main.py` (added terminal router registration)
- `apps/backend/api/permissions.py` (added CODE_TERMINAL, CODE_USE, CODE_WRITE, CODE_ADMIN permissions)

### Frontend Files Created
- `apps/frontend/src/components/TerminalView.tsx` (308 lines)
- `apps/frontend/src/components/TerminalModal.tsx` (24 lines)

### Frontend Dependencies Added
- xterm@5.3.0
- xterm-addon-fit@0.8.0
- xterm-addon-web-links@0.9.0

---

## Deployment Notes

### Production Considerations

1. **WebSocket Proxy:**
   Ensure nginx/reverse proxy supports WebSocket upgrade:
   ```nginx
   location /api/v1/terminal/ws/ {
       proxy_pass http://backend;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```

2. **Resource Limits:**
   - Set `ulimit` for max open files
   - Configure max terminals per user
   - Monitor PTY file descriptors

3. **Security:**
   - Run backend with restricted user
   - Disable dangerous commands (if needed)
   - Audit all terminal commands

---

**Phase 5 Status:** ✅ COMPLETE

Next: Begin Phase 6 (Continue Core Integration)
