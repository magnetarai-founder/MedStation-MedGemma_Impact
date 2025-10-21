# Neutron Star Chat API Documentation

## Overview
Local AI chat service with Ollama integration, supporting multi-session conversations, file attachments, and streaming responses.

## Base URL
```
http://localhost:8000/api/v1/chat
```

---

## Endpoints

### 1. List Available Models
**GET** `/models`

Returns all available Ollama models on the system.

**Response:**
```json
[
  {
    "name": "qwen2.5-coder:7b-instruct",
    "size": "4.7GB",
    "modified_at": "2025-01-15T10:30:00"
  }
]
```

---

### 2. Create Chat Session
**POST** `/sessions`

Create a new chat session.

**Request:**
```json
{
  "title": "My Chat",
  "model": "qwen2.5-coder:7b-instruct"
}
```

**Response:**
```json
{
  "id": "chat_abc123def456",
  "title": "My Chat",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00",
  "model": "qwen2.5-coder:7b-instruct",
  "message_count": 0
}
```

---

### 3. List All Chat Sessions
**GET** `/sessions`

Returns all chat sessions, sorted by most recent first.

**Response:**
```json
[
  {
    "id": "chat_abc123def456",
    "title": "My Chat",
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:35:00",
    "model": "qwen2.5-coder:7b-instruct",
    "message_count": 4
  }
]
```

---

### 4. Get Chat Session Details
**GET** `/sessions/{chat_id}`

Get a specific chat session with full message history.

**Query Parameters:**
- `limit` (optional): Limit number of messages returned (default: all)

**Response:**
```json
{
  "session": {
    "id": "chat_abc123def456",
    "title": "My Chat",
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T10:35:00",
    "model": "qwen2.5-coder:7b-instruct",
    "message_count": 2
  },
  "messages": [
    {
      "role": "user",
      "content": "Hello!",
      "timestamp": "2025-01-15T10:31:00",
      "files": []
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you?",
      "timestamp": "2025-01-15T10:31:05",
      "model": "qwen2.5-coder:7b-instruct",
      "tokens": 6
    }
  ]
}
```

---

### 5. Send Message (Streaming)
**POST** `/sessions/{chat_id}/messages`

Send a message and receive a streaming response via Server-Sent Events (SSE).

**Request:**
```json
{
  "content": "Write a hello world function in Python",
  "model": "qwen2.5-coder:7b-instruct"  // Optional, uses session default if not provided
}
```

**Response:** (Server-Sent Events stream)
```
data: [START]

data: {"content": "def "}

data: {"content": "hello"}

data: {"content": "_world"}

data: {"content": "():\n"}

data: {"content": "    print"}

data: {"content": '("Hello, '}

data: {"content": 'World!")'}

data: {"done": true, "message_id": "msg_xyz789"}
```

**Client Example (JavaScript):**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/chat/sessions/chat_abc123/messages'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.content) {
    // Append streaming content
    appendToMessage(data.content);
  }

  if (data.done) {
    // Stream complete
    eventSource.close();
  }

  if (data.error) {
    console.error('Error:', data.error);
    eventSource.close();
  }
};
```

---

### 6. Upload File to Chat
**POST** `/sessions/{chat_id}/upload`

Upload a file attachment to a chat session. File content will be extracted (if possible) and added to context.

**Request:** (multipart/form-data)
```
file: <binary file data>
```

**Response:**
```json
{
  "id": "file_abc123",
  "original_name": "document.pdf",
  "stored_name": "chat_abc123_file_abc123.pdf",
  "size": 102400,
  "type": "application/pdf",
  "uploaded_at": "2025-01-15T10:32:00",
  "text_preview": "[PDF content - extraction pending]"
}
```

**Client Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch(
  `http://localhost:8000/api/v1/chat/sessions/${chatId}/upload`,
  {
    method: 'POST',
    body: formData
  }
);

const fileInfo = await response.json();
```

---

### 7. Delete Chat Session
**DELETE** `/sessions/{chat_id}`

Delete a chat session and all its messages.

**Response:**
```json
{
  "status": "deleted",
  "chat_id": "chat_abc123def456"
}
```

---

## Storage

### Directory Structure
```
.neutron_data/
├── chats/
│   ├── sessions.json           # All session metadata
│   ├── chat_abc123.jsonl       # Messages for chat_abc123
│   └── chat_def456.jsonl       # Messages for chat_def456
└── uploads/
    ├── chat_abc123_file1.pdf
    └── chat_abc123_file2.txt
```

### Message Format (JSONL)
Each line in a chat file is a complete JSON message:
```json
{"role":"user","content":"Hello","timestamp":"2025-01-15T10:30:00","files":[]}
{"role":"assistant","content":"Hi there!","timestamp":"2025-01-15T10:30:05","model":"qwen2.5-coder:7b","tokens":3}
```

---

## Context Window Management

- **200k token limit** per chat session
- Automatically preserves:
  - Recent messages (last 50 for API calls)
  - File attachments metadata
  - System prompts
- Older messages still stored in JSONL but not sent to model

---

## Model Switching

You can switch models mid-conversation:

```json
POST /sessions/{chat_id}/messages
{
  "content": "Now explain it simply",
  "model": "llama3.1:8b"  // Different from session default
}
```

Context is preserved across model switches.

---

## Error Handling

All endpoints return standard HTTP status codes:

- `200` - Success
- `404` - Chat session not found
- `500` - Server error (Ollama not running, etc.)

Error response format:
```json
{
  "detail": "Chat session not found"
}
```

---

## Testing

Run the included test script:
```bash
./test_chat_api.sh
```

Or test manually with curl:
```bash
# Create session
curl -X POST http://localhost:8000/api/v1/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "Test"}' | jq

# Send message (streaming)
curl -X POST http://localhost:8000/api/v1/chat/sessions/chat_abc123/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello!"}' \
  --no-buffer
```

---

## Requirements

- **Ollama** must be running locally (`ollama serve`)
- **Python 3.11+** with dependencies:
  - fastapi
  - httpx
  - aiofiles
  - pydantic

Install dependencies:
```bash
pip install -r backend_requirements.txt
```

---

## Frontend Integration

See `frontend/src/components/ChatWindow.tsx` for React implementation example.

Key features:
- EventSource for SSE streaming
- File upload with drag-and-drop
- Model selector dropdown
- Message history with auto-scroll
- Code syntax highlighting
