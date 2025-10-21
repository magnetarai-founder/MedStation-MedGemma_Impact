#!/usr/bin/env python3
"""
Jarvis Learning System
Advanced pattern learning, preference detection, and adaptive behavior
Builds on BigQuery memory for intelligent decision making
"""

import json
import time
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import hashlib
import re
import threading
import math

# Import our memory system
try:
    from jarvis_memory import JarvisMemory
except ImportError:
    from api.jarvis_memory import JarvisMemory
    from api.jarvis_memory import JarvisMemory
except ImportError:
    from api.jarvis_memory import JarvisMemory


@dataclass
class UserPreference:
    """Learned user preference"""
    category: str  # e.g., 'tool', 'style', 'workflow'
    preference: str  # e.g., 'aider', 'verbose', 'test-first'
    confidence: float  # 0.0 to 1.0
    evidence_count: int
    last_observed: str
    

@dataclass
class CodingStyle:
    """Detected coding style patterns"""
    language: str
    patterns: Dict[str, Any]  # e.g., {'indent': 4, 'quotes': 'single'}
    confidence: float
    sample_count: int
    indentation: int = 4  # Default indentation
    quote_style: str = 'single'  # Default quote style
    

@dataclass
class ProjectContext:
    """Project-specific context and settings"""
    project_path: str
    project_type: str  # e.g., 'python-web', 'node-cli', 'data-science'
    languages: List[str]
    frameworks: List[str]
    dependencies: List[str]
    typical_workflows: List[str]
    last_active: str
    activity_count: int
    

@dataclass
class Recommendation:
    """Learning-based recommendation"""
    action: str
    reason: str
    confidence: float
    based_on: List[str]  # What evidence supports this
    

class LearningSystem:
    """
    Intelligent learning system that:
    - Tracks success patterns
    - Learns user preferences
    - Detects coding styles
    - Provides smart recommendations
    - Manages project contexts
    """
    
    def __init__(self, memory: JarvisMemory = None, db_path: Path = None):
        if db_path is None:
            db_path = Path.home() / ".omnistudio" / "learning.db"
            
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.memory = memory or JarvisMemory()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        
        self._setup_database()
        self._initialize_patterns()
        
    def _setup_database(self):
        """Create learning system tables"""
        
        # Success tracking
        # Create or update success_patterns table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS success_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_hash TEXT UNIQUE,
                pattern_type TEXT,  -- command, workflow, tool_combo
                pattern_data TEXT,  -- JSON
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                avg_time REAL,
                last_seen DATETIME,
                confidence REAL
            )
        """)
        
        # Add total_count column if it doesn't exist (migration)
        try:
            self.conn.execute("ALTER TABLE success_patterns ADD COLUMN total_count INTEGER DEFAULT 0")
            self.conn.execute("UPDATE success_patterns SET total_count = success_count + failure_count")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # User preferences
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                preference TEXT,
                positive_signals INTEGER DEFAULT 0,
                negative_signals INTEGER DEFAULT 0,
                confidence REAL,
                last_observed DATETIME,
                UNIQUE(category, preference)
            )
        """)
        
        # Coding style patterns
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS coding_styles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language TEXT,
                file_pattern TEXT,
                style_data TEXT,  -- JSON with style rules
                sample_count INTEGER DEFAULT 0,
                confidence REAL,
                last_updated DATETIME
            )
        """)
        
        # Project contexts
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS project_contexts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT UNIQUE,
                project_type TEXT,
                project_data TEXT,  -- JSON with full context
                activity_count INTEGER DEFAULT 0,
                last_active DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Recommendations log
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_type TEXT,
                action TEXT,
                reason TEXT,
                confidence REAL,
                was_accepted BOOLEAN,
                feedback TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Learning feedback
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT,
                tool_used TEXT,
                execution_time REAL,
                success BOOLEAN,
                user_satisfaction INTEGER,  -- 1-5 scale, NULL if not provided
                context_data TEXT,  -- JSON
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
        
    def _initialize_patterns(self):
        """Initialize pattern detection rules"""
        
        self.pattern_rules = {
            'tool_preference': {
                'aider_preferred': lambda history: self._count_tool_usage(history, 'aider') > 5,
                'ollama_preferred': lambda history: self._count_tool_usage(history, 'ollama') > 5,
                'assistant_preferred': lambda history: self._count_tool_usage(history, 'assistant') > 3,
            },
            'workflow_preference': {
                'test_first': lambda history: self._detect_test_first_pattern(history),
                'documentation_focus': lambda history: self._detect_doc_pattern(history),
                'iterative_development': lambda history: self._detect_iterative_pattern(history),
            },
            'style_preference': {
                'verbose_output': lambda history: self._detect_verbosity_preference(history),
                'minimal_output': lambda history: not self._detect_verbosity_preference(history),
                'parallel_execution': lambda history: self._detect_parallel_preference(history),
            }
        }
        
    # ============= SUCCESS TRACKING =============
    
    def track_execution(self, command: str, tool: str, success: bool, 
                       execution_time: float, context: Dict = None):
        """Track command execution for learning"""
        with self._lock:
        
            # Store in learning feedback
            self.conn.execute("""
                INSERT INTO learning_feedback 
                (command, tool_used, execution_time, success, context_data)
                VALUES (?, ?, ?, ?, ?)
            """, (command, tool, execution_time, success, json.dumps(context or {})))
        
            # Update success patterns
            pattern_hash = hashlib.md5(f"{command}_{tool}".encode()).hexdigest()
        
            cursor = self.conn.execute("""
                SELECT success_count, failure_count, avg_time
                FROM success_patterns
                WHERE pattern_hash = ?
            """, (pattern_hash,))
        
            row = cursor.fetchone()
        
            if row:
                # Update existing pattern
                new_success = row['success_count'] + (1 if success else 0)
                new_failure = row['failure_count'] + (0 if success else 1)
                total = new_success + new_failure
                new_avg_time = (row['avg_time'] * (total - 1) + execution_time) / total
                confidence = new_success / total if total > 0 else 0
            
                self.conn.execute("""
                    UPDATE success_patterns
                    SET success_count = ?, failure_count = ?, total_count = ?, avg_time = ?,
                        confidence = ?, last_seen = CURRENT_TIMESTAMP
                    WHERE pattern_hash = ?
                """, (new_success, new_failure, total, new_avg_time, confidence, pattern_hash))
            else:
                # Create new pattern
                self.conn.execute("""
                    INSERT INTO success_patterns
                    (pattern_hash, pattern_type, pattern_data, success_count, 
                     failure_count, total_count, avg_time, confidence, last_seen)
                    VALUES (?, 'command', ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    pattern_hash,
                    json.dumps({'command': command, 'tool': tool}),
                    1 if success else 0,
                    0 if success else 1,
                    1,
                    execution_time,
                    1.0 if success else 0.0
                ))
            
            self.conn.commit()
        
            # Learn from this execution
            self._learn_from_execution(command, tool, success, execution_time)
        
    def get_success_rate(self, command: str, tool: str) -> float:
        """Get success rate for a command/tool combination"""
        
        pattern_hash = hashlib.md5(f"{command}_{tool}".encode()).hexdigest()
        
        cursor = self.conn.execute("""
            SELECT confidence FROM success_patterns
            WHERE pattern_hash = ?
        """, (pattern_hash,))
        
        row = cursor.fetchone()
        return row['confidence'] if row else 0.5  # Default 50% if unknown
        
    # ============= PREFERENCE LEARNING =============
    
    def _learn_from_execution(self, command: str, tool: str, success: bool, execution_time: float):
        """Learn preferences from execution patterns"""
        
        # Learn tool preferences
        if success:
            self._update_preference('tool', tool, positive=True)
            
        # Learn timing preferences
        if execution_time is not None and execution_time < 2.0:
            self._update_preference('speed', 'fast_execution', positive=True)
        elif execution_time is not None and execution_time > 10.0:
            self._update_preference('speed', 'thorough_execution', positive=True)
            
        # Learn command type preferences
        if 'test' in command.lower():
            self._update_preference('workflow', 'testing_focused', positive=True)
        if 'document' in command.lower() or 'readme' in command.lower():
            self._update_preference('workflow', 'documentation_focused', positive=True)
            
    def _update_preference(self, category: str, preference: str, positive: bool = True):
        """Update a user preference based on observed behavior"""
        
        cursor = self.conn.execute("""
            SELECT positive_signals, negative_signals
            FROM user_preferences
            WHERE category = ? AND preference = ?
        """, (category, preference))
        
        row = cursor.fetchone()
        
        if row:
            pos = row['positive_signals'] + (1 if positive else 0)
            neg = row['negative_signals'] + (0 if positive else 1)
            confidence = pos / (pos + neg) if (pos + neg) > 0 else 0.5
            
            self.conn.execute("""
                UPDATE user_preferences
                SET positive_signals = ?, negative_signals = ?,
                    confidence = ?, last_observed = CURRENT_TIMESTAMP
                WHERE category = ? AND preference = ?
            """, (pos, neg, confidence, category, preference))
        else:
            self.conn.execute("""
                INSERT INTO user_preferences
                (category, preference, positive_signals, negative_signals, 
                 confidence, last_observed)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                category, preference,
                1 if positive else 0,
                0 if positive else 1,
                1.0 if positive else 0.0
            ))
            
        self.conn.commit()
        
    def get_preferences(self, category: Optional[str] = None) -> List[UserPreference]:
        """Get learned user preferences"""
        
        if category:
            cursor = self.conn.execute("""
                SELECT * FROM user_preferences
                WHERE category = ? AND confidence > 0.6
                ORDER BY confidence DESC
            """, (category,))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM user_preferences
                WHERE confidence > 0.6
                ORDER BY category, confidence DESC
            """)
            
        preferences = []
        for row in cursor:
            preferences.append(UserPreference(
                category=row['category'],
                preference=row['preference'],
                confidence=row['confidence'],
                evidence_count=row['positive_signals'] + row['negative_signals'],
                last_observed=row['last_observed']
            ))
            
        return preferences
        
    # ============= STYLE DETECTION =============
    
    def detect_coding_style(self, file_path: str, content: str) -> CodingStyle:
        """Detect coding style from file content"""
        
        language = self._detect_language(file_path)
        patterns = {}
        
        if language == 'python':
            patterns = self._detect_python_style(content)
        elif language in ['javascript', 'typescript']:
            patterns = self._detect_js_style(content)
        elif language == 'java':
            patterns = self._detect_java_style(content)
            
        # Store detected style
        self._store_coding_style(language, file_path, patterns)
        
        return CodingStyle(
            language=language,
            patterns=patterns,
            confidence=0.8,  # Would calculate based on sample size
            sample_count=1
        )
        
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'unknown')
        
    def _detect_python_style(self, content: str) -> Dict:
        """Detect Python coding style patterns"""
        
        lines = content.split('\n')
        patterns = {}
        
        # Indentation
        indent_counts = defaultdict(int)
        for line in lines:
            if line and line[0] == ' ':
                spaces = len(line) - len(line.lstrip())
                if spaces > 0:
                    indent_counts[spaces] += 1
                    
        if indent_counts:
            most_common_indent = max(indent_counts, key=indent_counts.get)
            patterns['indent'] = most_common_indent
            
        # Quotes
        single_quotes = content.count("'")
        double_quotes = content.count('"')
        patterns['quotes'] = 'single' if single_quotes > double_quotes else 'double'
        
        # Type hints
        patterns['type_hints'] = '->' in content or ': str' in content or ': int' in content
        
        # Docstrings
        patterns['docstring_style'] = 'triple_double' if '"""' in content else 'triple_single' if "'''" in content else None
        
        # Class naming
        class_pattern = re.compile(r'class\s+([A-Z][a-zA-Z0-9]*)')
        classes = class_pattern.findall(content)
        patterns['class_naming'] = 'PascalCase' if classes else None
        
        # Function naming
        func_pattern = re.compile(r'def\s+([a-z_][a-z0-9_]*)')
        functions = func_pattern.findall(content)
        patterns['function_naming'] = 'snake_case' if functions else None
        
        return patterns
        
    def _detect_js_style(self, content: str) -> Dict:
        """Detect JavaScript/TypeScript style patterns"""
        
        patterns = {}
        
        # Semicolons
        patterns['semicolons'] = content.count(';') > content.count('\n') * 0.5
        
        # Quotes
        single_quotes = content.count("'")
        double_quotes = content.count('"')
        patterns['quotes'] = 'single' if single_quotes > double_quotes else 'double'
        
        # Const vs let
        const_count = content.count('const ')
        let_count = content.count('let ')
        patterns['variable_declaration'] = 'const' if const_count > let_count else 'let'
        
        # Arrow functions
        patterns['arrow_functions'] = '=>' in content
        
        return patterns
        
    def _detect_java_style(self, content: str) -> Dict:
        """Detect Java style patterns"""
        
        patterns = {}
        
        # Brace style
        patterns['brace_style'] = 'same_line' if '{\n' in content else 'new_line'
        
        # Access modifiers
        patterns['explicit_access'] = 'private' in content or 'public' in content
        
        return patterns
        
    def _store_coding_style(self, language: str, file_path: str, patterns: Dict):
        """Store detected coding style in database"""
        
        file_pattern = str(Path(file_path).parent / f"*.{Path(file_path).suffix}")
        
        cursor = self.conn.execute("""
            SELECT sample_count FROM coding_styles
            WHERE language = ? AND file_pattern = ?
        """, (language, file_pattern))
        
        row = cursor.fetchone()
        
        if row:
            # Update existing style data
            self.conn.execute("""
                UPDATE coding_styles
                SET style_data = ?, sample_count = sample_count + 1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE language = ? AND file_pattern = ?
            """, (json.dumps(patterns), language, file_pattern))
        else:
            # Insert new style data
            self.conn.execute("""
                INSERT INTO coding_styles
                (language, file_pattern, style_data, sample_count, confidence)
                VALUES (?, ?, ?, 1, 0.5)
            """, (language, file_pattern, json.dumps(patterns)))
            
        self.conn.commit()
        
    # ============= RECOMMENDATIONS =============
    
    def get_recommendations(self, command: str, context: Dict = None) -> List[Recommendation]:
        """Get learning-based recommendations for a command"""
        
        recommendations = []
        
        # Tool recommendations based on success patterns
        tool_rec = self._recommend_tool(command)
        if tool_rec:
            recommendations.append(tool_rec)
            
        # Workflow recommendations based on patterns
        workflow_rec = self._recommend_workflow(command, context)
        if workflow_rec:
            recommendations.append(workflow_rec)
            
        # Style recommendations based on detected patterns
        if context and 'file_path' in context:
            style_rec = self._recommend_style(context['file_path'])
            if style_rec:
                recommendations.append(style_rec)
                
        return recommendations
        
    def _recommend_tool(self, command: str) -> Optional[Recommendation]:
        """Recommend best tool based on success patterns"""
        
        # Check success rates for different tools
        tools = ['aider', 'ollama', 'assistant', 'system']
        best_tool = None
        best_rate = 0.0
        
        for tool in tools:
            rate = self.get_success_rate(command, tool)
            if rate > best_rate:
                best_rate = rate
                best_tool = tool
                
        if best_tool and best_rate > 0.7:
            return Recommendation(
                action=f"Use {best_tool} for this command",
                reason=f"Historical success rate: {best_rate:.0%}",
                confidence=best_rate,
                based_on=['success_patterns']
            )
            
        return None
        
    def _recommend_workflow(self, command: str, context: Dict = None) -> Optional[Recommendation]:
        """Recommend workflow based on user preferences"""
        
        preferences = self.get_preferences('workflow')
        
        if preferences:
            top_pref = preferences[0]
            
            if top_pref.preference == 'testing_focused' and 'test' not in command.lower():
                return Recommendation(
                    action="Consider adding tests",
                    reason=f"You typically prefer test-driven development (confidence: {top_pref.confidence:.0%})",
                    confidence=top_pref.confidence,
                    based_on=['workflow_preferences']
                )
            elif top_pref.preference == 'documentation_focused' and 'doc' not in command.lower():
                return Recommendation(
                    action="Remember to update documentation",
                    reason=f"You typically prioritize documentation (confidence: {top_pref.confidence:.0%})",
                    confidence=top_pref.confidence,
                    based_on=['workflow_preferences']
                )
                
        return None
        
    def _recommend_style(self, file_path: str) -> Optional[Recommendation]:
        """Recommend coding style based on detected patterns"""
        
        language = self._detect_language(file_path)
        
        cursor = self.conn.execute("""
            SELECT style_data, confidence
            FROM coding_styles
            WHERE language = ?
            ORDER BY sample_count DESC
            LIMIT 1
        """, (language,))
        
        row = cursor.fetchone()
        
        if row and row['confidence'] > 0.7:
            style_data = json.loads(row['style_data'])
            
            if language == 'python' and 'indent' in style_data:
                return Recommendation(
                    action=f"Use {style_data['indent']} spaces for indentation",
                    reason=f"Project standard detected from existing code",
                    confidence=row['confidence'],
                    based_on=['coding_style']
                )
                
        return None
        
    # ============= CONTEXT AWARENESS =============
    
    def detect_project_context(self, cwd: str = None) -> ProjectContext:
        """Detect and store project context"""
        
        if cwd is None:
            cwd = str(Path.cwd())
            
        # Check for existing context
        cursor = self.conn.execute("""
            SELECT project_data, activity_count
            FROM project_contexts
            WHERE project_path = ?
        """, (cwd,))
        
        row = cursor.fetchone()
        
        if row:
            # Update activity
            self.conn.execute("""
                UPDATE project_contexts
                SET activity_count = activity_count + 1,
                    last_active = CURRENT_TIMESTAMP
                WHERE project_path = ?
            """, (cwd,))
            self.conn.commit()
            
            data = json.loads(row['project_data'])
            return ProjectContext(
                project_path=cwd,
                project_type=data['project_type'],
                languages=data['languages'],
                frameworks=data['frameworks'],
                dependencies=data['dependencies'],
                typical_workflows=data.get('typical_workflows', []),
                last_active=datetime.now().isoformat(),
                activity_count=row['activity_count'] + 1
            )
        else:
            # Detect new project context
            context = self._analyze_project(cwd)
            self._store_project_context(context)
            return context
            
    def _analyze_project(self, project_path: str) -> ProjectContext:
        """Analyze project structure and detect context"""
        
        path = Path(project_path)
        languages = set()
        frameworks = []
        dependencies = []
        project_type = 'unknown'
        
        # Detect languages
        for ext in ['.py', '.js', '.ts', '.java', '.go', '.rs']:
            if list(path.rglob(f'*{ext}')):
                languages.add(ext[1:])
                
        # Detect project type and frameworks
        if (path / 'package.json').exists():
            project_type = 'node'
            try:
                with open(path / 'package.json') as f:
                    pkg = json.load(f)
                    dependencies = list(pkg.get('dependencies', {}).keys())
                    
                    # Detect frameworks
                    if 'react' in dependencies:
                        frameworks.append('react')
                    if 'express' in dependencies:
                        frameworks.append('express')
                    if 'vue' in dependencies:
                        frameworks.append('vue')
            except:
                pass
                
        elif (path / 'requirements.txt').exists() or (path / 'setup.py').exists():
            project_type = 'python'
            if (path / 'requirements.txt').exists():
                try:
                    with open(path / 'requirements.txt') as f:
                        dependencies = [line.split('==')[0].strip() 
                                      for line in f if line.strip() and not line.startswith('#')]
                        
                    # Detect frameworks
                    if 'django' in dependencies:
                        frameworks.append('django')
                    if 'flask' in dependencies:
                        frameworks.append('flask')
                    if 'fastapi' in dependencies:
                        frameworks.append('fastapi')
                except:
                    pass
                    
        elif (path / 'Cargo.toml').exists():
            project_type = 'rust'
            
        elif (path / 'go.mod').exists():
            project_type = 'go'
            
        # Detect typical workflows based on files
        workflows = []
        if (path / 'Makefile').exists():
            workflows.append('make')
        if (path / '.github' / 'workflows').exists():
            workflows.append('github-actions')
        if (path / 'Dockerfile').exists():
            workflows.append('docker')
            
        return ProjectContext(
            project_path=project_path,
            project_type=project_type,
            languages=list(languages),
            frameworks=frameworks,
            dependencies=dependencies[:20],  # Limit stored deps
            typical_workflows=workflows,
            last_active=datetime.now().isoformat(),
            activity_count=1
        )
        
    def _store_project_context(self, context: ProjectContext):
        """Store project context in database"""
        
        project_data = {
            'project_type': context.project_type,
            'languages': context.languages,
            'frameworks': context.frameworks,
            'dependencies': context.dependencies,
            'typical_workflows': context.typical_workflows
        }
        
        self.conn.execute("""
            INSERT OR REPLACE INTO project_contexts
            (project_path, project_type, project_data, activity_count, last_active)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            context.project_path,
            context.project_type,
            json.dumps(project_data),
            context.activity_count
        ))
        
        self.conn.commit()
        
    def switch_context(self, project_path: str) -> ProjectContext:
        """Switch to a different project context"""
        
        return self.detect_project_context(project_path)
        
    def get_active_projects(self, limit: int = 5) -> List[ProjectContext]:
        """Get recently active projects"""
        
        cursor = self.conn.execute("""
            SELECT project_path, project_type, project_data, activity_count, last_active
            FROM project_contexts
            ORDER BY last_active DESC
            LIMIT ?
        """, (limit,))
        
        projects = []
        for row in cursor:
            data = json.loads(row['project_data'])
            projects.append(ProjectContext(
                project_path=row['project_path'],
                project_type=row['project_type'],
                languages=data['languages'],
                frameworks=data['frameworks'],
                dependencies=data['dependencies'],
                typical_workflows=data.get('typical_workflows', []),
                last_active=row['last_active'],
                activity_count=row['activity_count']
            ))
            
        return projects
    
    def record_command(self, command: str, success: bool = True):
        """Record a command execution (simple interface)"""
        self.track_execution(command, tool="unknown", success=success, execution_time=0.0)
    
    def record_preference(self, category: str, preference: str):
        """Record a user preference"""
        self._update_preference(category, preference, positive=True)
    
    def record_model_performance(self, model: str, response_time: float, quality_score: float):
        """Record model performance metrics"""
        # Store in success patterns table as model performance data
        pattern_data = {
            'model': model,
            'response_time': response_time,
            'quality_score': quality_score,
            'timestamp': datetime.now().isoformat()
        }
        
        pattern_hash = hashlib.md5(f"model_perf_{model}_{datetime.now().date()}".encode()).hexdigest()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO success_patterns 
            (pattern_hash, pattern_type, pattern_data, success_count, failure_count, total_count, avg_time, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (pattern_hash, 'model_performance', json.dumps(pattern_data), 
              1, 0, 1, response_time, ))
        self.conn.commit()
    
    def get_learned_patterns(self) -> List[Dict]:
        """Get all learned patterns"""
        patterns = self.conn.execute("""
            SELECT pattern_type, pattern_data, success_count, total_count,
                   success_count * 1.0 / total_count as success_rate
            FROM success_patterns
            WHERE total_count > 5
            ORDER BY success_rate DESC
            LIMIT 20
        """).fetchall()
        
        return [dict(p) for p in patterns]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get learning system statistics"""
        stats = {}
        
        # Success rate
        total = self.conn.execute("SELECT SUM(total_count), SUM(success_count) FROM success_patterns").fetchone()
        if total and total[0]:
            stats['success_rate'] = total[1] / total[0]
        else:
            stats['success_rate'] = 0.0
            
        # Pattern count
        stats['pattern_count'] = self.conn.execute("SELECT COUNT(*) FROM success_patterns").fetchone()[0]
        
        # Preference count
        stats['preference_count'] = self.conn.execute("SELECT COUNT(*) FROM user_preferences").fetchone()[0]
        
        return stats
    
    def get_best_model_for_task(self, task_type: str) -> Optional[str]:
        """Get the best performing model for a task type"""
        # For now, return a default model based on task type
        model_map = {
            'code_generation': 'qwen2.5-coder:32b',
            'chat': 'phi3:mini',
            'analysis': 'llama3.1:8b'
        }
        return model_map.get(task_type, 'qwen2.5-coder:1.5b-instruct')
        
    # ============= HELPER METHODS =============
    
    def _count_tool_usage(self, history: List, tool: str) -> int:
        """Count how many times a tool was used"""
        return sum(1 for h in history if h.get('tool') == tool)
        
    def _detect_test_first_pattern(self, history: List) -> bool:
        """Detect if user follows test-first development"""
        # Look for patterns where test files are created before implementation
        return False  # Simplified for now
        
    def _detect_doc_pattern(self, history: List) -> bool:
        """Detect if user prioritizes documentation"""
        doc_commands = sum(1 for h in history if 'doc' in h.get('command', '').lower())
        return doc_commands > len(history) * 0.2
        
    def _detect_iterative_pattern(self, history: List) -> bool:
        """Detect iterative development style"""
        # Look for repeated edit-test cycles
        return False  # Simplified for now
        
    def _detect_verbosity_preference(self, history: List) -> bool:
        """Detect if user prefers verbose output"""
        # Would analyze command flags and patterns
        return True  # Default to verbose for now
        
    def _detect_parallel_preference(self, history: List) -> bool:
        """Detect if user prefers parallel execution"""
        # Check for parallel flags in commands
        return False  # Simplified for now


def test_learning_system():
    """Test the learning system"""
    print("Testing Learning System...")
    
    # Create learning system
    memory = JarvisMemory(Path("/tmp/test_learning_memory.db"))
    learner = LearningSystem(memory=memory, db_path=Path("/tmp/test_learning.db"))
    
    print("\n1. Testing Success Tracking")
    # Track some executions
    learner.track_execution("create test.py", "aider", True, 2.5)
    learner.track_execution("create test.py", "aider", True, 2.3)
    learner.track_execution("create test.py", "ollama", False, 5.0)
    
    success_rate = learner.get_success_rate("create test.py", "aider")
    print(f"   Aider success rate: {success_rate:.0%}")
    
    print("\n2. Testing Preference Learning")
    # Simulate multiple executions to learn preferences
    for _ in range(5):
        learner.track_execution("write tests for calculator", "assistant", True, 1.5)
    for _ in range(3):
        learner.track_execution("document the API", "assistant", True, 2.0)
        
    preferences = learner.get_preferences()
    print(f"   Learned {len(preferences)} preferences:")
    for pref in preferences[:3]:
        print(f"     - {pref.category}/{pref.preference}: {pref.confidence:.0%}")
        
    print("\n3. Testing Style Detection")
    sample_python = '''
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)
    
class Calculator:
    def add(self, a: float, b: float) -> float:
        return a + b
'''
    
    style = learner.detect_coding_style("test.py", sample_python)
    print(f"   Detected {style.language} style:")
    for key, value in list(style.patterns.items())[:3]:
        print(f"     - {key}: {value}")
        
    print("\n4. Testing Recommendations")
    recommendations = learner.get_recommendations("create calculator.py")
    print(f"   Generated {len(recommendations)} recommendations:")
    for rec in recommendations:
        print(f"     - {rec.action} ({rec.confidence:.0%})")
        print(f"       Reason: {rec.reason}")
        
    print("\n5. Testing Project Context")
    context = learner.detect_project_context()
    print(f"   Detected project type: {context.project_type}")
    print(f"   Languages: {', '.join(context.languages[:3]) if context.languages else 'none'}")
    print(f"   Frameworks: {', '.join(context.frameworks[:3]) if context.frameworks else 'none'}")
    
    print("\n6. Testing Context Switching")
    projects = learner.get_active_projects(limit=3)
    print(f"   Found {len(projects)} active projects")
    for proj in projects:
        print(f"     - {Path(proj.project_path).name}: {proj.project_type} ({proj.activity_count} activities)")
        
    print("\n✅ Learning System Test Complete!")


if __name__ == "__main__":
    test_learning_system()