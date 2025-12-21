#!/usr/bin/env python3
"""
Jarvis BigQuery-Inspired Memory System
Combines all 3 competition approaches into a unified agent memory layer

Instead of ChromaDB, we use:
1. SQL CTE Templates (Approach 1) - Grounded patterns for zero hallucination
2. Semantic Embeddings (Approach 2) - Find similar commands and contexts
3. Multimodal Analysis (Approach 3) - Handle screenshots, diagrams, etc.
"""

import sqlite3
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import re
import threading


class MemoryType(Enum):
    """Types of memory patterns"""
    COMMAND_PATTERN = "command_pattern"
    CODE_TEMPLATE = "code_template"
    ERROR_SOLUTION = "error_solution"
    WORKFLOW_SEQUENCE = "workflow_sequence"
    SEMANTIC_CLUSTER = "semantic_cluster"
    

@dataclass
class MemoryTemplate:
    """SQL template for memory operations"""
    id: str
    name: str
    category: str
    pattern: str  # SQL CTE pattern
    parameters: List[str]
    confidence: float = 0.8
    

@dataclass
class SemanticMemory:
    """Semantic memory entry with embedding"""
    command: str
    embedding: List[float]  # Vector representation
    context: Dict[str, Any]
    timestamp: str
    success: bool
    tool_used: str
    execution_time: float
    

class JarvisBigQueryMemory:
    """
    Advanced memory system inspired by BigQuery competition approaches
    Uses SQL patterns, semantic search, and multimodal analysis
    """
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            base = Path(os.getenv('JARVIS_DB_DIR', str(Path.home() / ".ai_agent"))).expanduser()
            db_path = base / "jarvis_memory.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use WAL mode for better concurrent access and add timeout
        self.conn = sqlite3.connect(
            str(self.db_path), 
            check_same_thread=False,
            timeout=30.0,  # 30 second timeout for locks
            isolation_level='DEFERRED'  # Better concurrency
        )
        self.conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrent access
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA mmap_size=30000000000")

        # Additional performance optimizations
        self.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache in RAM
        self.conn.execute("PRAGMA page_size=4096")     # Optimize page size
        self.conn.execute("PRAGMA busy_timeout=5000")  # 5 second busy timeout
        
        # Thread lock for write operations
        self._write_lock = threading.Lock()
        
        self.templates = self._initialize_templates()
        self.memory_templates = self.templates  # Alias for compatibility
        self._setup_database()
        
    def _setup_database(self):
        """Create advanced memory tables"""
        
        # Main command memory with embeddings
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS command_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                command_hash TEXT UNIQUE,
                embedding_json TEXT,  -- JSON array of floats
                task_type TEXT,
                tool_used TEXT,
                success BOOLEAN,
                execution_time REAL,
                context_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Pattern templates (like BigQuery CTE templates)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS pattern_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT UNIQUE,
                pattern_sql TEXT,
                category TEXT,
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0,
                avg_execution_time REAL DEFAULT 0,
                last_used DATETIME
            )
        """)
        
        # Semantic clusters for similarity search
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_name TEXT,
                centroid_embedding TEXT,  -- JSON array
                member_commands TEXT,  -- JSON array of command IDs
                common_tools TEXT,  -- JSON array
                cluster_confidence REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Error patterns and solutions
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS error_solutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_pattern TEXT,
                error_hash TEXT UNIQUE,
                solution_template TEXT,
                tool_suggestion TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_seen DATETIME
            )
        """)
        
        # Workflow sequences (chains of commands)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_name TEXT,
                command_sequence TEXT,  -- JSON array
                total_time REAL,
                success_rate REAL,
                usage_count INTEGER DEFAULT 0,
                last_executed DATETIME
            )
        """)
        
        # Semantic memory table (was missing)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT,
                embedding TEXT,  -- JSON array
                context TEXT,  -- JSON object
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Content chunks for RAG
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS content_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT,
                start_line INTEGER,
                end_line INTEGER,
                chunk TEXT,
                embedding_json TEXT,
                tags TEXT,
                touched_at TIMESTAMP,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_command_hash ON command_memory(command_hash)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON command_memory(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_task_type ON command_memory(task_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_timestamp ON semantic_memory(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_path ON content_chunks(path)")
        
        self.conn.commit()
        
    def _initialize_templates(self) -> List[MemoryTemplate]:
        """Initialize SQL CTE templates for memory operations"""
        return [
            # Command Analysis Templates
            MemoryTemplate(
                id="CMD_001",
                name="Similar Command Finder",
                category="command_analysis",
                pattern="""
                WITH command_patterns AS (
                    SELECT 
                        command,
                        task_type,
                        tool_used,
                        AVG(execution_time) as avg_time,
                        COUNT(*) as usage_count,
                        AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate
                    FROM command_memory
                    WHERE command LIKE ?
                    GROUP BY command, task_type, tool_used
                ),
                ranked_patterns AS (
                    SELECT *,
                        ROW_NUMBER() OVER (ORDER BY usage_count DESC, success_rate DESC) as rank
                    FROM command_patterns
                )
                SELECT * FROM ranked_patterns WHERE rank <= 5
                """,
                parameters=["command_pattern"],
                confidence=0.85
            ),
            
            # Error Pattern Templates
            MemoryTemplate(
                id="ERR_001",
                name="Error Solution Finder",
                category="error_handling",
                pattern="""
                WITH error_matches AS (
                    SELECT 
                        error_pattern,
                        solution_template,
                        tool_suggestion,
                        (success_count * 1.0) / NULLIF(success_count + failure_count, 0) as success_rate
                    FROM error_solutions
                    WHERE error_pattern LIKE ?
                        OR error_hash = ?
                ),
                ranked_solutions AS (
                    SELECT *,
                        ROW_NUMBER() OVER (ORDER BY success_rate DESC) as rank
                    FROM error_matches
                    WHERE success_rate > 0.5
                )
                SELECT * FROM ranked_solutions WHERE rank = 1
                """,
                parameters=["error_pattern", "error_hash"],
                confidence=0.9
            ),
            
            # Workflow Discovery Templates
            MemoryTemplate(
                id="WF_001",
                name="Workflow Pattern Detector",
                category="workflow_analysis",
                pattern="""
                WITH recent_commands AS (
                    SELECT 
                        command,
                        task_type,
                        tool_used,
                        timestamp,
                        LAG(command, 1) OVER (ORDER BY timestamp) as prev_command,
                        LAG(command, 2) OVER (ORDER BY timestamp) as prev_command_2
                    FROM command_memory
                    WHERE timestamp > datetime('now', '-1 hour')
                ),
                command_sequences AS (
                    SELECT 
                        prev_command_2 || ' -> ' || prev_command || ' -> ' || command as sequence,
                        COUNT(*) as occurrence_count
                    FROM recent_commands
                    WHERE prev_command IS NOT NULL
                    GROUP BY sequence
                    HAVING occurrence_count > 1
                )
                SELECT * FROM command_sequences
                ORDER BY occurrence_count DESC
                LIMIT 5
                """,
                parameters=[],
                confidence=0.75
            ),
        ]
        
    def store_command(self, command: str, task_type: str, tool: str, 
                     success: bool, execution_time: float, output: str = "", context: Dict = None):
        """Store a command execution in memory"""
        
        # Handle None command values
        if command is None:
            command = ""
        
        # Generate embedding (simplified - in real version would use actual embedding model)
        embedding = self._generate_embedding(command)
        command_hash = hashlib.sha256(command.encode()).hexdigest()
        
        # Use thread lock for write operations
        with self._write_lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO command_memory 
                (command, command_hash, embedding_json, task_type, tool_used, 
                 success, execution_time, context_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                command,
                command_hash,
                json.dumps(embedding),
                task_type,
                tool,
                success,
                execution_time,
                json.dumps(context or {})
            ))
            
            self.conn.commit()
            
            # Update pattern statistics
            self._update_pattern_stats(task_type, tool, success, execution_time)
            
            # Check for workflow patterns
            self._detect_workflow_patterns()
        
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding using the unified embedder with safe fallback.

        Prefers the unified embedding provider (MLX → ollama → hash) to keep
        memory, RAG, and retrieval dimensions consistent across the system.
        Falls back to the legacy hash embedding if anything fails.
        """
        try:
            from unified_embedder import embed_text
            vec = embed_text(text or "")
            # Ensure we have a non-empty float vector
            if isinstance(vec, list) and vec and isinstance(vec[0], (int, float)):
                return [float(x) for x in vec]
        except Exception:
            pass

        # Legacy fallback: simple 128-d hash embedding
        words = (text or "").lower().split()
        vector = [0.0] * 128
        for word in words:
            idx = abs(hash(word)) % 128
            vector[idx] += 1.0
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]
        
    def find_similar_commands(self, query: str, limit: int = 5) -> List[Dict]:
        """Find similar commands using semantic search"""
        
        query_embedding = self._generate_embedding(query)
        
        # Get all commands with embeddings
        cursor = self.conn.execute("""
            SELECT command, embedding_json, task_type, tool_used, 
                   success, execution_time, context_json
            FROM command_memory
            WHERE embedding_json IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        
        results = []
        for row in cursor:
            stored_embedding = json.loads(row['embedding_json'])
            similarity = self._cosine_similarity(query_embedding, stored_embedding)
            
            results.append({
                'command': row['command'],
                'similarity': similarity,
                'task_type': row['task_type'],
                'tool_used': row['tool_used'],
                'success': row['success'],
                'execution_time': row['execution_time'],
                'context': json.loads(row['context_json'] or '{}')
            })
            
        # Sort by similarity and return top matches
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]
        
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a**2 for a in vec1) ** 0.5
        norm2 = sum(b**2 for b in vec2) ** 0.5
        
        if norm1 * norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
        
    def _update_pattern_stats(self, task_type: str, tool: str, 
                             success: bool, execution_time: float):
        """Update pattern statistics"""
        pattern_key = f"{task_type}_{tool}"
        
        # Get current stats
        cursor = self.conn.execute("""
            SELECT usage_count, success_rate, avg_execution_time
            FROM pattern_templates
            WHERE pattern_name = ?
        """, (pattern_key,))
        
        row = cursor.fetchone()
        
        if row:
            # Update existing pattern
            new_count = row['usage_count'] + 1
            new_success_rate = ((row['success_rate'] * row['usage_count']) + 
                               (1.0 if success else 0.0)) / new_count
            new_avg_time = ((row['avg_execution_time'] * row['usage_count']) + 
                           execution_time) / new_count
            
            self.conn.execute("""
                UPDATE pattern_templates
                SET usage_count = ?, success_rate = ?, avg_execution_time = ?, 
                    last_used = CURRENT_TIMESTAMP
                WHERE pattern_name = ?
            """, (new_count, new_success_rate, new_avg_time, pattern_key))
        else:
            # Create new pattern
            self.conn.execute("""
                INSERT INTO pattern_templates 
                (pattern_name, category, usage_count, success_rate, 
                 avg_execution_time, last_used)
                VALUES (?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
            """, (pattern_key, task_type, 1.0 if success else 0.0, execution_time))
            
        self.conn.commit()
        
    def _detect_workflow_patterns(self):
        """Detect and store workflow patterns from recent commands"""
        
        # Get recent command sequences
        cursor = self.conn.execute("""
            SELECT command, task_type, timestamp
            FROM command_memory
            WHERE timestamp > datetime('now', '-30 minutes')
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        
        commands = list(cursor)
        
        if len(commands) >= 3:
            # Look for patterns in sequences of 3 commands
            for i in range(len(commands) - 2):
                sequence = [
                    commands[i+2]['command'],
                    commands[i+1]['command'], 
                    commands[i]['command']
                ]
                
                # Check if this sequence exists
                sequence_json = json.dumps(sequence)
                cursor = self.conn.execute("""
                    SELECT id, usage_count
                    FROM workflow_sequences
                    WHERE command_sequence = ?
                """, (sequence_json,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing workflow
                    self.conn.execute("""
                        UPDATE workflow_sequences
                        SET usage_count = usage_count + 1,
                            last_executed = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (existing['id'],))
                else:
                    # Create new workflow if it seems intentional
                    # (e.g., different task types suggesting a workflow)
                    if len(set(c['task_type'] for c in commands[i:i+3])) > 1:
                        self.conn.execute("""
                            INSERT INTO workflow_sequences
                            (workflow_name, command_sequence, usage_count)
                            VALUES (?, ?, 1)
                        """, (f"workflow_{datetime.now().timestamp()}", sequence_json))
                        
            self.conn.commit()
            
    def suggest_next_command(self, current_command: str) -> Optional[Dict]:
        """Suggest the next command based on workflow patterns"""
        
        # Look for workflows containing this command
        cursor = self.conn.execute("""
            SELECT command_sequence, success_rate, usage_count
            FROM workflow_sequences
            WHERE command_sequence LIKE ?
            ORDER BY usage_count DESC, success_rate DESC
            LIMIT 1
        """, (f'%"{current_command}"%',))
        
        row = cursor.fetchone()
        
        if row:
            sequence = json.loads(row['command_sequence'])
            # Find current command in sequence and return next
            try:
                idx = sequence.index(current_command)
                if idx < len(sequence) - 1:
                    return {
                        'suggested_command': sequence[idx + 1],
                        'confidence': row['success_rate'] or 0.5,
                        'based_on_uses': row['usage_count']
                    }
            except (ValueError, IndexError):
                pass
                
        return None
        
    def get_error_solution(self, error_message: str) -> Optional[Dict]:
        """Find solution for an error"""
        
        error_hash = hashlib.sha256(error_message.encode()).hexdigest()
        
        # Use the error solution template
        template = next(t for t in self.templates if t.id == "ERR_001")
        
        cursor = self.conn.execute(
            template.pattern,
            (f'%{error_message[:50]}%', error_hash)
        )
        
        row = cursor.fetchone()
        
        if row:
            return {
                'solution': row['solution_template'],
                'tool': row['tool_suggestion'],
                'confidence': row['success_rate']
            }
            
        return None
        
    def get_statistics(self) -> Dict:
        """Get memory system statistics"""
        
        stats = {}
        
        # Total commands
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM command_memory")
        stats['total_commands'] = cursor.fetchone()['count']
        
        # Success rate
        cursor = self.conn.execute("""
            SELECT AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as rate
            FROM command_memory
        """)
        stats['overall_success_rate'] = cursor.fetchone()['rate'] or 0
        
        # Most used tools
        cursor = self.conn.execute("""
            SELECT tool_used, COUNT(*) as count
            FROM command_memory
            GROUP BY tool_used
            ORDER BY count DESC
            LIMIT 5
        """)
        stats['top_tools'] = [dict(row) for row in cursor]
        
        # Workflow patterns
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM workflow_sequences")
        stats['workflow_patterns'] = cursor.fetchone()['count']
        
        # Error solutions
        cursor = self.conn.execute("SELECT COUNT(*) as count FROM error_solutions")
        stats['known_error_solutions'] = cursor.fetchone()['count']
        
        return stats
    
    def search_semantic(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for semantically similar commands/memories"""
        return self.find_similar_commands(query, limit)
    
    def add_command(self, command: str, task_type: str, tool_used: str,
                    success: bool, execution_time: float, output: str = ""):
        """Add a command to memory (alias for store_command)"""
        return self.store_command(
            command=command,
            task_type=task_type,
            tool=tool_used,
            success=success,
            execution_time=execution_time,
            output=output
        )
    
    def log_command(self, command: str, output: str = "", success: bool = True, 
                    execution_time: float = 0.0, task_type: str = "general"):
        """Log a command execution (simplified interface)"""
        return self.store_command(
            command=command,
            task_type=task_type,
            tool="unknown",
            success=success,
            execution_time=execution_time,
            output=output
        )
    
    def add_semantic_memory(self, command: str, context: Dict[str, Any]):
        """Add semantic memory entry"""
        # Generate embedding
        embedding = self._generate_embedding(command)
        
        # Store in semantic memory with thread lock
        with self._write_lock:
            self.conn.execute("""
                INSERT INTO semantic_memory (command, embedding, context, timestamp)
                VALUES (?, ?, ?, ?)
            """, (command, json.dumps(embedding), json.dumps(context), 
                  datetime.now().isoformat()))
            
            self.conn.commit()
    
    # Alias for compatibility
    def search_similar_commands(self, query: str, limit: int = 5) -> List[Dict]:
        """Alias for find_similar_commands for compatibility"""
        return self.find_similar_commands(query, limit)
    
    def get_command_history(self, limit: int = 50) -> List[Dict]:
        """Get recent command history"""
        with self._write_lock:
            results = self.conn.execute("""
                SELECT command, task_type, tool_used as tool, success, execution_time, 
                       timestamp as created_at, '' as output
                FROM command_memory
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
        return [dict(row) for row in results]


def test_memory_system():
    """Test the BigQuery-inspired memory system"""
    
    memory = JarvisBigQueryMemory(Path("/tmp/test_jarvis_memory.db"))
    
    # Store some commands
    test_commands = [
        ("create test.py with fibonacci function", "code_write", "aider", True, 2.5),
        ("fix bug in calculator.py", "bug_fix", "aider", True, 3.2),
        ("review the code", "code_review", "assistant", True, 1.8),
        ("create test.py with factorial function", "code_write", "aider", True, 2.3),
        ("git commit -m 'Added features'", "git_operation", "system", True, 0.5),
    ]
    
    print("Storing test commands...")
    for cmd, task_type, tool, success, exec_time in test_commands:
        memory.store_command(cmd, task_type, tool, success, exec_time)
        
    # Test similarity search
    print("\n" + "="*50)
    print("Testing similarity search for: 'create a Python file'")
    similar = memory.find_similar_commands("create a Python file", limit=3)
    for i, result in enumerate(similar, 1):
        print(f"{i}. {result['command'][:50]}... (similarity: {result['similarity']:.2f})")
        
    # Test workflow detection
    print("\n" + "="*50)
    print("Testing workflow suggestion after: 'create test.py'")
    suggestion = memory.suggest_next_command("create test.py with fibonacci function")
    if suggestion:
        print(f"Suggested next: {suggestion['suggested_command']}")
        print(f"Confidence: {suggestion['confidence']:.2%}")
        
    # Get statistics
    print("\n" + "="*50)
    print("Memory System Statistics:")
    stats = memory.get_statistics()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    test_memory_system()
