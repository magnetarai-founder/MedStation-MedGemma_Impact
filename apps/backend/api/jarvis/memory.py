#!/usr/bin/env python3
"""
Jarvis BigQuery-Inspired Memory System
Combines all 3 competition approaches into a unified agent memory layer

Instead of ChromaDB, we use:
1. SQL CTE Templates (Approach 1) - Grounded patterns for zero hallucination
2. Semantic Embeddings (Approach 2) - Find similar commands and contexts
3. Multimodal Analysis (Approach 3) - Handle screenshots, diagrams, etc.

Module structure (P2 decomposition):
- jarvis_memory_models.py: Enums, dataclasses, CTE templates
- jarvis_memory_db.py: Database schema, embedding utilities
- jarvis_memory.py: Main JarvisMemory class (this file)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

# Import from jarvis package modules
from api.jarvis.memory_models import (
    MemoryType,
    MemoryTemplate,
    SemanticMemory,
    get_default_templates,
)
from api.jarvis.memory_db import (
    get_default_db_path,
    create_connection,
    setup_schema,
    generate_embedding,
    cosine_similarity,
    command_hash,
    error_hash,
)
    

class JarvisMemory:
    """
    Advanced memory system inspired by BigQuery competition approaches
    Uses SQL patterns, semantic search, and multimodal analysis
    """

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = get_default_db_path()

        self.db_path = db_path

        # Create connection with WAL mode and optimizations
        self.conn = create_connection(db_path)

        # Thread lock for write operations
        self._write_lock = threading.Lock()

        # Initialize CTE templates from extracted module
        self.templates = get_default_templates()
        self.memory_templates = self.templates  # Alias for compatibility

        # Set up database schema
        setup_schema(self.conn)
        
    # Note: _setup_database and _initialize_templates moved to extracted modules
    # - setup_schema() in jarvis_memory_db.py
    # - get_default_templates() in jarvis_memory_models.py
        
    def store_command(self, command: str, task_type: str, tool: str,
                     success: bool, execution_time: float, output: str = "", context: Dict = None) -> None:
        """Store a command execution in memory"""

        # Handle None command values
        if command is None:
            command = ""

        # Generate embedding using extracted utility
        embedding = generate_embedding(command)
        cmd_hash = command_hash(command)
        
        # Use thread lock for write operations
        with self._write_lock:
            self.conn.execute("""
                INSERT OR REPLACE INTO command_memory
                (command, command_hash, embedding_json, task_type, tool_used,
                 success, execution_time, context_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                command,
                cmd_hash,
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
        
    # Note: _generate_embedding moved to jarvis_memory_db.py as generate_embedding()
        
    def find_similar_commands(self, query: str, limit: int = 5) -> List[Dict]:
        """Find similar commands using semantic search"""

        query_embedding = generate_embedding(query)
        
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
            similarity = cosine_similarity(query_embedding, stored_embedding)
            
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

    # Note: _cosine_similarity moved to jarvis_memory_db.py as cosine_similarity()

    def _update_pattern_stats(self, task_type: str, tool: str,
                             success: bool, execution_time: float) -> None:
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
        
    def _detect_workflow_patterns(self) -> None:
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

        err_hash = error_hash(error_message)
        
        # Use the error solution template
        template = next(t for t in self.templates if t.id == "ERR_001")

        cursor = self.conn.execute(
            template.pattern,
            (f'%{error_message[:50]}%', err_hash)
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
                    success: bool, execution_time: float, output: str = "") -> None:
        """Add a command to memory (alias for store_command)"""
        self.store_command(
            command=command,
            task_type=task_type,
            tool=tool_used,
            success=success,
            execution_time=execution_time,
            output=output
        )
    
    def log_command(self, command: str, output: str = "", success: bool = True,
                    execution_time: float = 0.0, task_type: str = "general") -> None:
        """Log a command execution (simplified interface)"""
        self.store_command(
            command=command,
            task_type=task_type,
            tool="unknown",
            success=success,
            execution_time=execution_time,
            output=output
        )
    
    def add_semantic_memory(self, command: str, context: Dict[str, Any]) -> None:
        """Add semantic memory entry"""
        # Generate embedding using extracted utility
        embedding = generate_embedding(command)
        
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


# ===== Backward Compatibility Exports =====
# Re-export from extracted modules for backward compatibility
__all__ = [
    # Main class
    "JarvisMemory",
    # Re-exported from jarvis_memory_models
    "MemoryType",
    "MemoryTemplate",
    "SemanticMemory",
    "get_default_templates",
    # Re-exported from jarvis_memory_db
    "get_default_db_path",
    "create_connection",
    "setup_schema",
    "generate_embedding",
    "cosine_similarity",
    "command_hash",
    "error_hash",
    # Test function
    "test_memory_system",
]


def test_memory_system() -> None:
    """Test the BigQuery-inspired memory system"""
    
    memory = JarvisMemory(Path("/tmp/test_jarvis_memory.db"))
    
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
