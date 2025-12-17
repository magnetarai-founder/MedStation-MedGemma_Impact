"""
Chat service - Session operation handlers.

Handles session update operations:
- Update session model
- Update session title
- Archive/unarchive sessions
- Export data to chat (from Data tab)
"""

import uuid
import asyncio
import logging
import io
from typing import Dict, Any, List
from datetime import datetime, UTC

from .lazy_init import _get_memory, _get_chat_uploads_dir
from .messages import append_message

logger = logging.getLogger(__name__)


async def update_session_model(chat_id: str, model: str) -> Dict[str, Any]:
    """Update the model for a chat session"""
    memory = _get_memory()
    await asyncio.to_thread(memory.update_session_model, chat_id, model)

    # Return updated session
    session = await asyncio.to_thread(memory.get_session, chat_id)
    if not session:
        raise ValueError(f"Session {chat_id} not found")

    return session


async def update_session_title(chat_id: str, title: str) -> Dict[str, Any]:
    """Update the title of a chat session"""
    memory = _get_memory()
    await asyncio.to_thread(memory.update_session_title, chat_id, title, auto_titled=False)

    # Return updated session
    session = await asyncio.to_thread(memory.get_session, chat_id)
    if not session:
        raise ValueError(f"Session {chat_id} not found")

    return session


async def set_session_archived(chat_id: str, archived: bool) -> Dict[str, Any]:
    """Archive or unarchive a chat session"""
    memory = _get_memory()
    await asyncio.to_thread(memory.set_session_archived, chat_id, archived)

    # Return updated session
    session = await asyncio.to_thread(memory.get_session, chat_id)
    if not session:
        raise ValueError(f"Session {chat_id} not found")

    return session


async def export_data_to_chat(session_id: str, query_id: str, query: str, results: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    """Export query results from Data tab to AI Chat"""
    import pandas as pd
    import aiofiles
    from api.chat_enhancements import DocumentChunker

    # Import sessions module for creating new session
    from .. import sessions as sessions_mod

    memory = _get_memory()
    uploads_dir = _get_chat_uploads_dir()

    # Create DataFrame from results
    df = pd.DataFrame(results)

    # Create new chat session
    session = await sessions_mod.create_new_session(
        title="Query Analysis",
        model="qwen2.5-coder:7b-instruct",
        user_id=user_id,
        team_id=None
    )

    chat_id = session["id"]

    # Save CSV file
    csv_file_id = uuid.uuid4().hex[:12]
    csv_filename = f"query_results_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
    csv_stored_filename = f"{chat_id}_{csv_file_id}.csv"
    csv_file_path = uploads_dir / csv_stored_filename

    # Write CSV file
    async with aiofiles.open(csv_file_path, 'w') as f:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        await f.write(csv_buffer.getvalue())

    csv_preview = csv_buffer.getvalue()[:1000]

    # Extract CSV text for RAG
    extracted_text = f"""Query Results Dataset

SQL Query:
{query}

Dataset Information:
- Rows: {len(results)}
- Columns: {', '.join(df.columns.tolist())}

Data Preview (CSV format):
{csv_preview}

Column Statistics:
{df.describe(include='all').to_string() if len(df) > 0 else 'No data'}
"""

    # Create chunks and embeddings for RAG
    chunks = await asyncio.to_thread(
        DocumentChunker.create_chunks_with_metadata,
        extracted_text,
        {
            "original_name": csv_filename,
            "type": "text/csv",
            "query": query,
            "row_count": len(results)
        }
    )

    # Store chunks in memory
    await asyncio.to_thread(memory.store_document_chunks, chat_id, chunks)

    # Add system message
    system_content = f"""📊 **Query Results Loaded**

I've analyzed your SQL query results. Here's what I found:

**Query:**
```sql
{query}
```

**Dataset Summary:**
- Total Rows: {len(results):,}
- Columns: {len(df.columns)}
- Data File: `{csv_filename}`

**Available Columns:**
{', '.join(f'`{col}`' for col in df.columns.tolist())}

**Sample Data:**
```
{df.head(5).to_string(index=False) if len(df) > 0 else 'No data'}
```

---

I can help you:
- 🔍 Analyze patterns and trends
- 📈 Generate insights and summaries
- ⚠️ Identify anomalies or outliers
- 💡 Suggest follow-up queries
- 📊 Explain what the data means

What would you like to know about this data?"""

    timestamp = datetime.now(UTC).isoformat()
    await append_message(
        chat_id,
        "assistant",
        system_content,
        timestamp,
        files=[{
            "id": csv_file_id,
            "original_name": csv_filename,
            "stored_name": csv_stored_filename,
            "size": csv_file_path.stat().st_size,
            "type": "text/csv",
            "uploaded_at": timestamp,
            "text_preview": csv_preview,
            "text_extracted": True,
            "chunks_created": len(chunks)
        }]
    )

    logger.info(f"Exported {len(results)} rows to chat session {chat_id} with {len(chunks)} RAG chunks")

    return {
        "chat_id": chat_id,
        "file_info": {
            "id": csv_file_id,
            "original_name": csv_filename,
            "stored_name": csv_stored_filename,
            "size": csv_file_path.stat().st_size,
            "type": "text/csv",
            "row_count": len(results),
            "chunks_created": len(chunks)
        },
        "status": "success"
    }
