"""
Insights Lab Template Engine Module

Template application using Ollama LLM.
"""

import logging
from datetime import datetime, UTC
from uuid import uuid4

from api.errors import http_500

logger = logging.getLogger(__name__)


async def apply_template_with_ollama(transcript: str, system_prompt: str) -> str:
    """Apply template using local Ollama"""
    try:
        from api.services.chat import get_ollama_client
        ollama_client = get_ollama_client()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the transcript to process:\n\n{transcript}"}
        ]

        full_response = ""
        async for chunk in ollama_client.chat(
            model="qwen2.5-coder:7b-instruct",
            messages=messages,
            temperature=0.5,
            top_p=0.9
        ):
            full_response += chunk

        return full_response.strip()

    except Exception as e:
        logger.error(f"Ollama template application failed: {e}")
        raise http_500("Template application failed")


async def auto_apply_default_templates(recording_id: str, transcript: str, user_id: str) -> None:
    """Auto-apply the 3 default templates on upload (background task)"""
    # Lazy imports to avoid circular dependency
    from .database import get_db
    from .templates import DEFAULT_TEMPLATE_IDS

    conn = get_db()
    cursor = conn.cursor()

    for template_id in DEFAULT_TEMPLATE_IDS:
        try:
            cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
            template_row = cursor.fetchone()

            if template_row:
                content = await apply_template_with_ollama(transcript, template_row["system_prompt"])

                output_id = f"out_{uuid4().hex[:12]}"
                now = datetime.now(UTC).isoformat()

                cursor.execute("""
                    INSERT INTO formatted_outputs
                    (id, recording_id, template_id, template_name, content, format, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    output_id, recording_id, template_id,
                    template_row["name"], content, template_row["output_format"], now
                ))

                logger.info(f"Auto-applied template {template_id} to recording {recording_id}")

        except Exception as e:
            logger.error(f"Error auto-applying template {template_id}: {e}")

    conn.commit()
    conn.close()


__all__ = ["apply_template_with_ollama", "auto_apply_default_templates"]
