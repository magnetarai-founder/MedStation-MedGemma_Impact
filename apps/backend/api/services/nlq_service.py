"""
Natural Language to SQL Service

Converts natural language questions to safe, validated SQL queries using local LLM.
"""

import os
import re
import json
import logging
import asyncio
import sqlite3
import secrets
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, UTC

try:
    from api.config import get_settings
except ImportError:
    from config import get_settings

from api.config_paths import PATHS

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Configuration
DEFAULT_NLQ_MODEL = os.getenv("ELOHIMOS_NLQ_MODEL", "qwen2.5:7b-instruct")
FALLBACK_MODELS = ["llama3.1:8b-instruct", "mistral:7b-instruct", "qwen2.5:7b"]
MAX_SQL_TIMEOUT = 30  # seconds
MAX_RESULT_ROWS = settings.max_query_rows  # From config
DEFAULT_LIMIT = settings.nlq_default_limit  # From config

# Schema introspection cache
_SCHEMA_CACHE: Dict[str, Tuple[Dict, float]] = {}
SCHEMA_CACHE_TTL = 3600  # 1 hour


def _ensure_nlq_history_schema() -> None:
    """Create nlq_history table if it doesn't exist"""
    with sqlite3.connect(str(PATHS.app_db)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nlq_history (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                sql TEXT NOT NULL,
                summary TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nlq_history_user_created "
            "ON nlq_history(user_id, created_at DESC)"
        )
        conn.commit()


def _save_nlq_history(user_id: str, question: str, sql: str, summary: str | None) -> None:
    """Save NLQ query to history (best-effort)"""
    try:
        _ensure_nlq_history_schema()
        with sqlite3.connect(str(PATHS.app_db)) as conn:
            conn.execute(
                "INSERT INTO nlq_history (id, user_id, question, sql, summary, created_at) "
                "VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (secrets.token_urlsafe(12), user_id, question, sql, summary or None),
            )
            conn.commit()
    except Exception as e:
        # History persistence is best-effort; do not fail the main request
        logger.warning(f"Failed to save NLQ history: {e}")


class NLQService:
    """Natural Language Query service for converting questions to SQL"""

    def __init__(self):
        self.ollama_client = None
        self.data_engine = None
        self.sql_validator = None

    def _get_ollama_client(self):
        """Lazy init for Ollama client"""
        if self.ollama_client is None:
            from api.services.chat.streaming import OllamaClient
            self.ollama_client = OllamaClient()
        return self.ollama_client

    def _get_data_engine(self):
        """Lazy init for data engine"""
        if self.data_engine is None:
            from api.data_engine import DataEngine
            self.data_engine = DataEngine()
        return self.data_engine

    def _get_sql_validator(self):
        """Lazy init for SQL validator"""
        if self.sql_validator is None:
            from sql_validator import SQLValidator
            self.sql_validator = SQLValidator()
        return self.sql_validator

    async def process_nlq(
        self,
        question: str,
        dataset_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process natural language question and return SQL + results

        Args:
            question: Natural language question
            dataset_id: Target dataset ID
            session_id: Session ID for context
            model: LLM model to use (defaults to qwen2.5:7b-instruct)
            user_id: User ID for history persistence

        Returns:
            {
                "sql": "SELECT ...",
                "results": [...],
                "summary": "Natural language summary",
                "warnings": [...],
                "metadata": {...}
            }
        """
        start_time = datetime.now(UTC)

        try:
            # Get schema for dataset
            schema_data = await self._get_schema(dataset_id, session_id)
            if not schema_data:
                return {
                    "error": "Dataset not found or no schema available",
                    "suggestion": "Please upload a dataset first or specify a valid dataset_id"
                }

            # Generate SQL from question
            sql_response = await self._generate_sql(
                question=question,
                schema_data=schema_data,
                model=model
            )

            if "error" in sql_response:
                return sql_response

            sql = sql_response["sql"]

            # Validate and sanitize SQL
            validation_result = self._validate_sql(
                sql=sql,
                allowed_tables=schema_data["tables"],
                schema=schema_data["schema"]
            )

            if not validation_result["valid"]:
                return {
                    "error": "Generated SQL failed validation",
                    "details": validation_result["errors"],
                    "sql": sql,
                    "suggestion": "Try rephrasing your question or use the manual SQL editor"
                }

            # Inject LIMIT if missing
            sql = self._ensure_limit(sql, DEFAULT_LIMIT)

            # Execute SQL with timeout
            try:
                engine = self._get_data_engine()
                results = await asyncio.wait_for(
                    asyncio.to_thread(engine.execute_sql, sql),
                    timeout=MAX_SQL_TIMEOUT
                )
            except asyncio.TimeoutError:
                return {
                    "error": f"Query execution exceeded {MAX_SQL_TIMEOUT}s timeout",
                    "sql": sql,
                    "suggestion": "Try a more specific question or add filters to reduce data volume"
                }

            # Cap results server-side
            if results["row_count"] > MAX_RESULT_ROWS:
                results["rows"] = results["rows"][:MAX_RESULT_ROWS]
                results["row_count"] = MAX_RESULT_ROWS
                results["truncated"] = True

            # Generate natural language summary
            summary = await self._generate_summary(
                question=question,
                results=results,
                model=model
            )

            execution_time = (datetime.now(UTC) - start_time).total_seconds()

            # Persist to history (best-effort)
            if user_id:
                _save_nlq_history(
                    user_id=user_id,
                    question=question,
                    sql=sql,
                    summary=summary
                )

            return {
                "sql": sql,
                "results": results["rows"],
                "row_count": results["row_count"],
                "columns": results["columns"],
                "summary": summary,
                "warnings": validation_result.get("warnings", []),
                "metadata": {
                    "execution_time_ms": round(results.get("execution_time", 0), 2),
                    "total_time_ms": round(execution_time * 1000, 2),
                    "model_used": model or DEFAULT_NLQ_MODEL,
                    "dataset_id": dataset_id,
                    "truncated": results.get("truncated", False)
                }
            }

        except Exception as e:
            logger.error(f"NLQ processing error: {e}", exc_info=True)
            return {
                "error": "Failed to process question",
                "details": str(e),
                "suggestion": "Please try again or contact support if the issue persists"
            }

    async def _get_schema(self, dataset_id: Optional[str], session_id: Optional[str]) -> Optional[Dict]:
        """Get schema for dataset with caching"""
        import time

        # Check cache first
        cache_key = dataset_id or session_id
        if cache_key in _SCHEMA_CACHE:
            schema, timestamp = _SCHEMA_CACHE[cache_key]
            if time.time() - timestamp < SCHEMA_CACHE_TTL:
                logger.debug(f"Using cached schema for {cache_key}")
                return schema

        # Introspect schema
        engine = self._get_data_engine()

        if dataset_id:
            metadata = engine.get_dataset_metadata(dataset_id)
            if not metadata:
                return None

            table_name = metadata["table_name"]
            schema_json = metadata["schema"]
        else:
            # Use latest dataset from session
            datasets = engine.list_datasets(session_id=session_id)
            if not datasets:
                return None

            latest = datasets[0]
            table_name = latest["table_name"]
            schema_json = latest["schema"]

        # Get sample rows (first 3)
        try:
            sample_query = f"SELECT * FROM {table_name} LIMIT 3"
            sample_results = engine.execute_sql(sample_query)
            sample_rows = sample_results["rows"]
        except Exception as e:
            logger.warning(f"Failed to get sample rows: {e}")
            sample_rows = []

        schema_data = {
            "tables": [table_name],
            "table_name": table_name,
            "schema": schema_json,
            "sample_rows": sample_rows
        }

        # Cache it
        _SCHEMA_CACHE[cache_key] = (schema_data, time.time())

        return schema_data

    async def _generate_sql(
        self,
        question: str,
        schema_data: Dict,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate SQL from natural language using LLM"""

        # Build prompt
        prompt = self._build_prompt(question, schema_data)

        # Select model
        model_name = model or DEFAULT_NLQ_MODEL

        # Call Ollama
        client = self._get_ollama_client()

        try:
            # Use non-streaming chat for SQL generation
            messages = [
                {
                    "role": "system",
                    "content": "You are a SQL expert. Generate safe, read-only SQL for the given schema. Return ONLY the SQL query, no explanation or formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Collect response (use streaming but gather all chunks)
            sql_chunks = []
            async for chunk in client.chat(
                model=model_name,
                messages=messages,
                stream=True,
                temperature=0.1,  # Low temperature for deterministic SQL
                top_p=0.9,
                top_k=40
            ):
                sql_chunks.append(chunk)

            raw_sql = "".join(sql_chunks).strip()

            # Post-process: extract SQL from markdown or other wrapping
            sql = self._extract_sql(raw_sql)

            if not sql:
                return {
                    "error": "Could not generate valid SQL",
                    "raw_response": raw_sql,
                    "suggestion": "Try rephrasing your question"
                }

            return {"sql": sql}

        except Exception as e:
            logger.error(f"LLM SQL generation error: {e}")

            # Try fallback models
            for fallback_model in FALLBACK_MODELS:
                if fallback_model == model_name:
                    continue
                try:
                    logger.info(f"Trying fallback model: {fallback_model}")
                    return await self._generate_sql(question, schema_data, fallback_model)
                except Exception as fallback_error:
                    logger.debug(f"Fallback model {fallback_model} failed: {fallback_error}")
                    continue

            return {
                "error": f"Failed to generate SQL: {str(e)}",
                "suggestion": "Ensure Ollama is running and model is downloaded"
            }

    def _build_prompt(self, question: str, schema_data: Dict) -> str:
        """Build prompt for SQL generation"""

        # Format schema
        schema_text = "Table: " + schema_data["table_name"] + "\n\nColumns:\n"
        for col in schema_data["schema"]:
            schema_text += f"  - {col['name']} ({col['type']})\n"

        # Format sample rows
        sample_text = ""
        if schema_data.get("sample_rows"):
            sample_text = "\n\nSample data (first 3 rows):\n"
            sample_text += json.dumps(schema_data["sample_rows"][:3], indent=2)

        prompt = f"""Generate a SQL query to answer this question:

Question: {question}

Available schema:
{schema_text}{sample_text}

Constraints:
- Use SELECT only (no DDL/DML)
- Only reference table: {schema_data["table_name"]}
- Only use columns that exist in the schema
- Include LIMIT 1000 or less
- Use simple JOINs only if absolutely necessary
- Maximum 2 levels of subqueries
- Return valid SQL without comments or markdown

SQL Query:"""

        return prompt

    def _extract_sql(self, raw_response: str) -> str:
        """Extract SQL from LLM response (may be wrapped in markdown, etc.)"""

        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', raw_response, flags=re.IGNORECASE)
        sql = re.sub(r'```\s*', '', sql)

        # Strip comments (prevent injection)
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

        # Normalize whitespace
        sql = ' '.join(sql.split())

        # Uppercase SQL keywords (optional, for consistency)
        sql = sql.strip()

        return sql

    def _validate_sql(
        self,
        sql: str,
        allowed_tables: List[str],
        schema: List[Dict]
    ) -> Dict[str, Any]:
        """Validate SQL with enhanced guardrails"""

        # Use existing SQLValidator
        validator = self._get_sql_validator()
        is_valid, errors, warnings = validator.validate_sql(sql, strict=False)

        # Additional NLQ-specific checks

        # 1. Check for dangerous operations
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER',
            'EXEC', 'EXECUTE', 'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE'
        ]

        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if re.search(r'\b' + keyword + r'\b', sql_upper):
                errors.append(f"Forbidden keyword: {keyword}")

        # 2. Enforce table whitelist
        for table in allowed_tables:
            # Table name should appear after FROM or JOIN
            pass  # Already checked by basic validator

        # Extract referenced tables
        table_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][\w.]*)'
        referenced_tables = re.findall(table_pattern, sql, re.IGNORECASE)

        for ref_table in referenced_tables:
            # Strip aliases
            table_name = ref_table.split()[0].strip('"`')
            if table_name not in allowed_tables:
                errors.append(f"Unknown table: {table_name}. Allowed tables: {', '.join(allowed_tables)}")

        # 3. Check that referenced columns exist
        column_names = [col["name"].lower() for col in schema]

        # Simple column extraction (this is a heuristic, not perfect)
        # Look for SELECT column patterns
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # Skip * and aggregates for now
            if select_clause.strip() != '*':
                # Extract column references (very basic)
                potential_cols = re.findall(r'\b([a-zA-Z_][\w]*)\b', select_clause)
                for col in potential_cols:
                    col_lower = col.lower()
                    # Skip SQL keywords and functions
                    if col_lower not in ['as', 'count', 'sum', 'avg', 'min', 'max', 'distinct']:
                        if col_lower not in column_names:
                            warnings.append(f"Column '{col}' may not exist in schema")

        # 4. Check for UNION (unless explicitly allowed)
        if 'UNION' in sql_upper:
            warnings.append("UNION detected - ensure this is necessary for your query")

        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings
        }

    def _ensure_limit(self, sql: str, default_limit: int) -> str:
        """Ensure SQL has a LIMIT clause"""

        sql_upper = sql.upper()

        # If LIMIT already present, check value
        limit_match = re.search(r'\bLIMIT\s+(\d+)', sql, re.IGNORECASE)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > MAX_RESULT_ROWS:
                # Replace with max
                sql = re.sub(
                    r'\bLIMIT\s+\d+',
                    f'LIMIT {MAX_RESULT_ROWS}',
                    sql,
                    flags=re.IGNORECASE
                )
            return sql

        # Inject LIMIT at end
        sql = sql.rstrip(';')
        sql += f' LIMIT {default_limit}'

        return sql

    async def _generate_summary(
        self,
        question: str,
        results: Dict,
        model: Optional[str] = None
    ) -> str:
        """Generate natural language summary of results"""

        row_count = results.get("row_count", 0)
        columns = results.get("columns", [])

        if row_count == 0:
            return "No results found for your question."

        # Simple rule-based summary for now (fast and offline)
        # Can be enhanced with LLM later if needed

        summary_parts = []

        # Row count
        summary_parts.append(f"Found {row_count} result{'s' if row_count != 1 else ''}")

        # Column info
        if len(columns) > 0:
            summary_parts.append(f"with {len(columns)} column{'s' if len(columns) != 1 else ''}")

        # Basic stats for numeric columns
        if results.get("rows"):
            first_row = results["rows"][0]
            numeric_cols = [
                col for col in columns
                if col in first_row and isinstance(first_row[col], (int, float))
            ]

            if numeric_cols:
                # Show range for first numeric column
                col = numeric_cols[0]
                values = [row[col] for row in results["rows"] if col in row and row[col] is not None]
                if values:
                    summary_parts.append(f"{col} ranges from {min(values)} to {max(values)}")

        summary = ". ".join(summary_parts) + "."

        return summary


# Global instance
_nlq_service = None


def get_nlq_service() -> NLQService:
    """Get global NLQ service instance"""
    global _nlq_service
    if _nlq_service is None:
        _nlq_service = NLQService()
    return _nlq_service
