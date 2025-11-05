# Jarvis Agent: Intelligent Task Routing & Learning System

## Overview
The Jarvis Agent implements an advanced system for intelligent task routing, learning from user behavior, and adaptive decision-making. It combines multiple components: adaptive routing, learning systems, RAG pipelines, and permission management.

---

## 1. ADAPTIVE ROUTER (Task Routing to Optimal Models)

### File Path
`/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/adaptive_router.py`

### Key Patterns

#### Core Architecture
```python
@dataclass
class AdaptiveRouteResult(RouteResult):
    """Extended route result with learning insights"""
    recommendations: List[Recommendation] = None
    adjusted_confidence: float = 0.0
    learning_insights: Dict[str, Any] = None

class AdaptiveRouter:
    def __init__(self, memory: JarvisBigQueryMemory = None, 
                 learning: LearningSystem = None):
        self.base_router = EnhancedRouter()
        self.memory = memory or JarvisBigQueryMemory()
        self.learning = learning or LearningSystem(memory=self.memory)
        self.routing_history = []
```

#### Confidence Adjustment Pattern
```python
def _adjust_confidence(self, command: str, task_type: TaskType, 
                      tool_type: ToolType, base_confidence: float) -> float:
    """Adjust confidence based on historical success"""
    success_rate = self.learning.get_success_rate(command, tool_type.value)
    
    if success_rate > 0 and success_rate != 0.5:
        # Blend base confidence with historical success
        adjusted = (base_confidence * 0.6) + (success_rate * 0.4)
        return min(1.0, adjusted)
    return base_confidence
```

#### Preference Override Pattern
```python
def _check_preference_override(self, command: str, 
                               base_result: RouteResult) -> Optional[RouteResult]:
    """Check if user preferences should override routing"""
    tool_prefs = self.learning.get_preferences('tool')
    
    if tool_prefs:
        top_pref = tool_prefs[0]
        
        # If user strongly prefers a tool and confidence is not too high
        if top_pref.confidence > 0.8 and base_result.confidence < 0.7:
            # Override with preferred tool
            return RouteResult(
                task_type=base_result.task_type,
                tool_type=preferred_tool,
                confidence=top_pref.confidence,
                matched_patterns=['user_preference'],
                reasoning=f"User preference override: {top_pref.preference}"
            )
    return None
```

#### Execution Feedback Loop
```python
def record_execution_result(self, command: str, tool: str, 
                           success: bool, execution_time: float):
    """Record execution result for learning"""
    self.learning.track_execution(command, tool, success, execution_time)
    
    # Store in memory for future routing decisions
    self.memory.store_command(
        command, task_type, tool, success, execution_time
    )
```

### Key Capabilities
- Routes commands to optimal tools (aider, ollama, assistant, system)
- Adjusts confidence scores based on historical success rates
- Overrides routing based on learned user preferences
- Tracks routing decisions and execution outcomes
- Provides human-readable explanations for routing decisions

---

## 2. ENHANCED ROUTER (Advanced Pattern Matching)

### File Path
`/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/enhanced_router.py`

### Key Patterns

#### Route Pattern Definition
```python
@dataclass
class RoutePattern:
    """Enhanced pattern for routing with confidence scoring"""
    pattern_type: str  # 'keyword', 'regex', 'fuzzy'
    patterns: List[str]
    task_type: TaskType
    tool_type: ToolType
    weight: float = 1.0
    min_confidence: float = 0.5
    context_hints: List[str] = None  # Boost confidence
    negative_patterns: List[str] = None  # Reduce confidence
```

#### Confidence Calculation
```python
def _calculate_pattern_confidence(self, command: str, pattern: RoutePattern) -> Tuple[float, List[str]]:
    """Calculate confidence score for a pattern match"""
    confidence = 0.0
    matched = []
    
    # Keyword matching
    if pattern.pattern_type == 'keyword':
        for keyword in pattern.patterns:
            if keyword.lower() in command_lower:
                confidence = max(confidence, 0.7)
                matched.append(keyword)
    
    # Regex matching with match ratio
    elif pattern.pattern_type == 'regex':
        for regex_str in pattern.patterns:
            if regex.search(command):
                match_length = len(match.group(0))
                match_ratio = match_length / len(command)
                confidence = max(confidence, 0.5 + (match_ratio * 0.5))
    
    # Apply context hints (boost)
    for hint in pattern.context_hints:
        if hint.lower() in command_lower:
            confidence = min(1.0, confidence + 0.1)
    
    # Apply negative patterns (reduce)
    for neg_pattern in pattern.negative_patterns:
        if neg_pattern.lower() in command_lower:
            confidence = max(0, confidence - 0.3)
    
    # Apply weight
    confidence *= pattern.weight
    return confidence, matched
```

#### Fallback Mechanism
```python
# Get fallback options (top 3 alternatives with >40% confidence)
fallbacks = []
for r in results[1:4]:
    if r[2] > 0.4:
        fallbacks.append((r[0], r[1], r[2]))

return RouteResult(
    task_type=task_type,
    tool_type=tool_type,
    confidence=confidence,
    fallback_options=fallbacks  # Multiple alternatives
)
```

### Pattern Library Examples
- **System Commands**: ls, dir, pwd, current directory
- **Git Operations**: git add, commit, push, pull, branch, checkout, merge
- **Code Writing**: write, create, implement functions and classes
- **Code Editing**: edit, modify, refactor, add type hints
- **Bug Fixing**: fix bugs, debug code, solve errors
- **Code Review**: review code, check quality, analyze
- **Testing**: write tests, test functions
- **Documentation**: document code, write docs, create README
- **Explanations**: what, why, how, when, where questions

### Key Capabilities
- Pattern-based routing with 3 types: keyword, regex, fuzzy
- Confidence scoring with weights and modifiers
- Context-aware boosting and negative patterns
- Fallback options ranked by confidence
- Suggestion system for low-confidence commands

---

## 3. LEARNING SYSTEM (Pattern Learning & Adaptation)

### File Path
`/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/learning_system.py`

### Key Data Structures
```python
@dataclass
class UserPreference:
    """Learned user preference"""
    category: str  # 'tool', 'style', 'workflow'
    preference: str  # 'aider', 'verbose', 'test-first'
    confidence: float  # 0.0 to 1.0
    evidence_count: int
    last_observed: str

@dataclass
class CodingStyle:
    """Detected coding style patterns"""
    language: str
    patterns: Dict[str, Any]  # indent, quotes, type_hints, etc.
    confidence: float
    sample_count: int

@dataclass
class ProjectContext:
    """Project-specific context and settings"""
    project_path: str
    project_type: str  # 'python-web', 'node-cli', 'data-science'
    languages: List[str]
    frameworks: List[str]
    dependencies: List[str]
    typical_workflows: List[str]

@dataclass
class Recommendation:
    """Learning-based recommendation"""
    action: str
    reason: str
    confidence: float
    based_on: List[str]  # Evidence supporting recommendation
```

### Success Tracking Pattern
```python
def track_execution(self, command: str, tool: str, success: bool, 
                   execution_time: float, context: Dict = None):
    """Track command execution for learning"""
    
    # Store in learning feedback
    self.conn.execute("""
        INSERT INTO learning_feedback 
        (command, tool_used, execution_time, success, context_data)
        VALUES (?, ?, ?, ?, ?)
    """, (command, tool, execution_time, success, json.dumps(context or {})))
    
    # Update success patterns
    pattern_hash = hashlib.md5(f"{command}_{tool}".encode()).hexdigest()
    
    # Calculate running success rate
    new_success = row['success_count'] + (1 if success else 0)
    new_failure = row['failure_count'] + (0 if success else 1)
    total = new_success + new_failure
    new_avg_time = (row['avg_time'] * (total - 1) + execution_time) / total
    confidence = new_success / total if total > 0 else 0
    
    self.conn.execute("""
        UPDATE success_patterns
        SET success_count = ?, failure_count = ?, total_count = ?, 
            avg_time = ?, confidence = ?, last_seen = CURRENT_TIMESTAMP
        WHERE pattern_hash = ?
    """, (new_success, new_failure, total, new_avg_time, confidence, pattern_hash))
```

### Preference Learning Pattern
```python
def _learn_from_execution(self, command: str, tool: str, success: bool, execution_time: float):
    """Learn preferences from execution patterns"""
    
    # Learn tool preferences
    if success:
        self._update_preference('tool', tool, positive=True)
    
    # Learn timing preferences
    if execution_time < 2.0:
        self._update_preference('speed', 'fast_execution', positive=True)
    elif execution_time > 10.0:
        self._update_preference('speed', 'thorough_execution', positive=True)
    
    # Learn command type preferences
    if 'test' in command.lower():
        self._update_preference('workflow', 'testing_focused', positive=True)
    if 'document' in command.lower() or 'readme' in command.lower():
        self._update_preference('workflow', 'documentation_focused', positive=True)

def _update_preference(self, category: str, preference: str, positive: bool = True):
    """Update a user preference based on observed behavior"""
    
    # Get current signals
    cursor = self.conn.execute("""
        SELECT positive_signals, negative_signals
        FROM user_preferences
        WHERE category = ? AND preference = ?
    """, (category, preference))
    
    if row:
        pos = row['positive_signals'] + (1 if positive else 0)
        neg = row['negative_signals'] + (0 if positive else 1)
        confidence = pos / (pos + neg) if (pos + neg) > 0 else 0.5
        
        # Update with new confidence
        self.conn.execute("""
            UPDATE user_preferences
            SET positive_signals = ?, negative_signals = ?,
                confidence = ?, last_observed = CURRENT_TIMESTAMP
            WHERE category = ? AND preference = ?
        """, (pos, neg, confidence, category, preference))
```

### Coding Style Detection
```python
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
    
    # Python example
    def _detect_python_style(self, content: str) -> Dict:
        patterns = {}
        
        # Indentation detection
        indent_counts = defaultdict(int)
        for line in lines:
            if line and line[0] == ' ':
                spaces = len(line) - len(line.lstrip())
                if spaces > 0:
                    indent_counts[spaces] += 1
        
        most_common_indent = max(indent_counts, key=indent_counts.get)
        patterns['indent'] = most_common_indent
        
        # Quote style
        patterns['quotes'] = 'single' if single_quotes > double_quotes else 'double'
        
        # Type hints
        patterns['type_hints'] = '->' in content or ': str' in content
        
        # Docstring style
        patterns['docstring_style'] = 'triple_double' if '"""' in content else 'triple_single'
        
        # Naming conventions
        patterns['class_naming'] = 'PascalCase'
        patterns['function_naming'] = 'snake_case'
        
        return patterns
```

### Project Context Detection
```python
def detect_project_context(self, cwd: str = None) -> ProjectContext:
    """Detect and store project context"""
    
    # Check for existing context
    cursor = self.conn.execute("""
        SELECT project_data, activity_count
        FROM project_contexts
        WHERE project_path = ?
    """, (cwd,))
    
    if row:
        # Update activity and return cached context
        self.conn.execute("""
            UPDATE project_contexts
            SET activity_count = activity_count + 1,
                last_active = CURRENT_TIMESTAMP
            WHERE project_path = ?
        """, (cwd,))
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
    
    # Detect languages from file extensions
    for ext in ['.py', '.js', '.ts', '.java', '.go', '.rs']:
        if list(path.rglob(f'*{ext}')):
            languages.add(ext[1:])
    
    # Detect project type and frameworks
    if (path / 'package.json').exists():
        project_type = 'node'
        # Parse package.json for dependencies and frameworks
        if 'react' in dependencies:
            frameworks.append('react')
        if 'express' in dependencies:
            frameworks.append('express')
    
    elif (path / 'requirements.txt').exists() or (path / 'setup.py').exists():
        project_type = 'python'
        # Parse requirements for frameworks
        if 'django' in dependencies:
            frameworks.append('django')
        if 'flask' in dependencies:
            frameworks.append('flask')
    
    # Detect workflows
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
        dependencies=dependencies,
        typical_workflows=workflows,
        last_active=datetime.now().isoformat(),
        activity_count=1
    )
```

### Recommendations Pattern
```python
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
```

### Database Schema
```python
# Success tracking
CREATE TABLE success_patterns (
    pattern_hash TEXT UNIQUE,
    pattern_type TEXT,  -- command, workflow, tool_combo
    pattern_data TEXT,  -- JSON
    success_count INTEGER,
    failure_count INTEGER,
    total_count INTEGER,
    avg_time REAL,
    confidence REAL
);

# User preferences
CREATE TABLE user_preferences (
    category TEXT,
    preference TEXT,
    positive_signals INTEGER,
    negative_signals INTEGER,
    confidence REAL,
    last_observed DATETIME,
    UNIQUE(category, preference)
);

# Coding styles
CREATE TABLE coding_styles (
    language TEXT,
    file_pattern TEXT,
    style_data TEXT,  -- JSON
    sample_count INTEGER,
    confidence REAL
);

# Project contexts
CREATE TABLE project_contexts (
    project_path TEXT UNIQUE,
    project_type TEXT,
    project_data TEXT,  -- JSON
    activity_count INTEGER,
    last_active DATETIME
);

# Recommendations log
CREATE TABLE recommendations (
    recommendation_type TEXT,
    action TEXT,
    reason TEXT,
    confidence REAL,
    was_accepted BOOLEAN,
    timestamp DATETIME
);

# Learning feedback
CREATE TABLE learning_feedback (
    command TEXT,
    tool_used TEXT,
    execution_time REAL,
    success BOOLEAN,
    user_satisfaction INTEGER,  -- 1-5 scale
    context_data TEXT,  -- JSON
    timestamp DATETIME
);
```

### Key Capabilities
- Tracks execution success rates with confidence scoring
- Learns user preferences from behavior patterns
- Detects coding styles (indentation, quotes, naming conventions)
- Detects project context (type, languages, frameworks, workflows)
- Generates recommendations based on learned patterns
- Manages multiple project contexts
- Provides historical success rates for routing decisions

---

## 4. RAG PIPELINE (Context Retrieval & Management)

### File Path
`/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/rag_pipeline.py`

### Key Patterns

#### Context Retrieval
```python
def retrieve_context_for_command(command: str, memory=None, max_snippets: int = 4) -> List[str]:
    """Retrieve context via EnhancedRAGPipeline when available."""
    
    if _enhanced_pipeline is not None:
        try:
            pipeline = get_enhanced_pipeline()
            chunks = pipeline.retrieve_context(command, max_snippets=max_snippets)
            snippets: List[str] = []
            for ch in chunks:
                bias_info = f" [{', '.join(ch.get('bias_reasons', []))}]" if ch.get('bias_reasons') else ""
                header = f"File: {ch['path']} [{ch['start_line']}-{ch['end_line']}] (sim {ch.get('similarity', 0):.2f}){bias_info}\n"
                snippets.append(header + ch['chunk'])
            return snippets
        except Exception:
            pass
    
    # Fallback to legacy retrieval
    return _retrieve_by_embedding(command, k=max_snippets * 2)
```

#### File Ingestion & Chunking
```python
def ingest_paths(paths: List[str], tags: List[str] = None, chunk_lines: int = 80):
    """Delegate to enhanced pipeline ingestion when available."""
    
    if _enhanced_pipeline is not None:
        try:
            pipeline = get_enhanced_pipeline()
            for p in paths:
                pipeline.ingest_file(p, tags=tags)
            return
        except Exception:
            pass
    
    # Fallback: legacy ingestion
    mem = JarvisBigQueryMemory()
    for p in paths:
        path = Path(p)
        if not path.exists() or not path.is_file():
            continue
        
        text = path.read_text(errors='ignore')
        lines = text.splitlines()
        
        # Chunk file into segments
        start = 1
        while start <= len(lines):
            end = min(len(lines), start + chunk_lines - 1)
            chunk = "\n".join(lines[start-1:end])
            emb = _embed_text(chunk)
            
            # Store chunk with embedding
            with mem._write_lock:
                mem.conn.execute(
                    "INSERT INTO content_chunks(path, start_line, end_line, chunk, embedding_json, tags) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(path), start, end, chunk, json.dumps(emb), tags_str)
                )
            start = end + 1
    mem.conn.commit()
```

#### Embedding & Retrieval
```python
def _retrieve_by_embedding(query: str, k: int = 4) -> List[Tuple[str,int,int,str,float,str]]:
    """Use enhanced pipeline scoring when available; keep legacy shape."""
    
    if _enhanced_pipeline is not None:
        try:
            pipeline = get_enhanced_pipeline()
            chunks = pipeline.retrieve_context(query, max_snippets=k)
            out: List[Tuple[str,int,int,str,float,str]] = []
            for ch in chunks:
                out.append((
                    ch['path'], 
                    ch['start_line'], 
                    ch['end_line'], 
                    ch['chunk'], 
                    float(ch.get('similarity', 0.0)), 
                    ch.get('tags') or ''
                ))
            return out
        except Exception:
            pass
    
    # Fallback to legacy computation
    mem = JarvisBigQueryMemory()
    q = _embed_text(query)
    rows = mem.conn.execute(
        "SELECT path, start_line, end_line, chunk, embedding_json, COALESCE(tags,'') AS tags FROM content_chunks"
    ).fetchall()
    
    scored = []
    for r in rows:
        try:
            emb = json.loads(r['embedding_json'])
        except Exception:
            continue
        
        score = _cosine(q, emb)
        scored.append((score, r['path'], r['start_line'], r['end_line'], r['chunk'], r['tags']))
    
    scored.sort(reverse=True, key=lambda x: x[0])
    out = []
    for s, path, start, end, chunk, tags in scored[:k]:
        out.append((path, start, end, chunk, s, tags))
    return out
```

#### Embedding Backend Selection
```python
def _embed_text(text: str) -> List[float]:
    """Unified embedding backend with intelligent fallback."""
    
    try:
        from unified_embedder import embed_text
        return embed_text(text)
    except Exception as e:
        backend = _read_embed_backend()
        
        # Primary backend
        if backend == 'ollama':
            emb = _ollama_embed(text)
            if emb:
                return emb
            # Fallback to MLX
            emb = _mlx_embed(text)
            if emb:
                return emb
        elif backend == 'mlx':
            emb = _mlx_embed(text)
            if emb:
                return emb
            # Fallback to ollama
            emb = _ollama_embed(text)
            if emb:
                return emb
        
        # Final fallback to CPU/hash
        return _hash_embed(text)

def _mlx_embed(text: str) -> List[float]:
    """MLX embedder using real MLX models or sentence transformers"""
    try:
        from mlx_sentence_transformer import MLXSentenceTransformer
        transformer = MLXSentenceTransformer()
        if transformer.initialize():
            embeddings = transformer.encode([text])
            if embeddings.size > 0:
                return embeddings[0].tolist()
    except ImportError:
        pass
    
    try:
        from embedding_system import EmbeddingSystem
        embedder = EmbeddingSystem()
        embedding = embedder.embed(text)
        if isinstance(embedding, (list, tuple)) and len(embedding) > 0:
            return list(embedding)
    except ImportError:
        pass
    
    return _hash_embed(text, dim=384)

def _ollama_embed(text: str) -> List[float]:
    """Use Ollama API for embeddings"""
    model = _read_embed_model()
    try:
        import json, urllib.request
        req = urllib.request.Request(
            url='http://127.0.0.1:11434/api/embeddings',
            data=json.dumps({"model": model, "prompt": text}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            emb = data.get('embedding') or data.get('data',{}).get('embedding')
            if emb:
                return emb
    except Exception:
        return []
    return []

def _hash_embed(text: str, dim: int = 128) -> List[float]:
    """CPU-based hash embedding as fallback"""
    words = text.lower().split()
    vec = [0.0]*dim
    for w in words:
        idx = abs(hash(w)) % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v/norm for v in vec]
```

#### Cosine Similarity
```python
def _cosine(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if not a or not b or len(a) != len(b):
        return 0.0
    
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a)) or 1.0
    nb = math.sqrt(sum(y*y for y in b)) or 1.0
    return dot/(na*nb)
```

### Key Capabilities
- File chunking and embedding-based retrieval
- Multiple embedding backends: Ollama, MLX, sentence-transformers
- Fallback to hash-based embeddings on CPU
- Similarity scoring with cosine similarity
- Tagged chunks for categorized retrieval
- Configurable chunk size and max snippets
- Environment-based configuration

---

## 5. TASK PLANNER (Execution Planning)

### File Path
`/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/planner.py`

### Key Patterns

#### Step and Plan Definition
```python
@dataclass
class Step:
    name: str
    engine: str  # 'aider' | 'continue' | 'codex' | 'verify'
    description: str
    files: List[str]
    model: Optional[str] = None
    timeout_s: int = 60

@dataclass
class Plan:
    steps: List[Step]
    heavy: bool
    rationale: str
    metadata: Optional[Dict[str, any]] = None
```

#### Planning Heuristics
```python
def plan(self, description: str, files: List[str] = None) -> Plan:
    files = files or []
    heavy = self._is_heavy(description, files)
    rationale = "heavy" if heavy else "light"
    
    # Detect simple codemod intent (rename X to Y)
    rn = self._detect_rename(description)
    if rn:
        old, new = rn
        steps = [
            Step(name='codemod', engine='codex', description=f"rename {old} to {new}", files=files, timeout_s=120),
            Step(name='verify', engine='verify', description='quick_checks+pytest', files=files, timeout_s=90),
        ]
        return Plan(steps=steps, heavy=heavy, rationale='codemod')
    
    # Try LLM-based micro-plan when available
    llm_steps = self._llm_plan(description, files, heavy)
    if llm_steps:
        steps = llm_steps[:3]
        if not any(s.engine == 'verify' for s in steps):
            steps.append(Step(name='verify', engine='verify', description='quick_checks+pytest', files=files, timeout_s=90))
        return Plan(steps=steps, heavy=heavy, rationale="llm_plan")
    
    # Heuristic fallback
    if heavy or self._repo_wide(description):
        proposer = 'continue'
        model = self._pick_code_model(heavy=True)
    else:
        proposer = 'aider'
        model = self._pick_code_model(heavy=False)
    
    steps = [
        Step(name='propose', engine=proposer, description=description, files=files, model=model, timeout_s=300),
        Step(name='verify', engine='verify', description='quick_checks+pytest', files=files, timeout_s=90),
    ]
    return Plan(steps=steps, heavy=heavy, rationale=rationale)
```

#### Heavy Task Detection
```python
def _is_heavy(self, text: str, files: List[str]) -> bool:
    """Determine if task is heavy (requires complex processing)"""
    t = text.lower()
    if len(files) >= 3:
        return True
    
    heavy_kw = ['refactor', 'rename package', 'across modules', 'global change', 'architecture', 'monorepo']
    return any(k in t for k in heavy_kw)

def _repo_wide(self, text: str) -> bool:
    """Determine if task affects entire repository"""
    t = text.lower()
    return any(k in t for k in ['repo-wide', 'across project', 'all files', 'every file'])
```

#### LLM-Based Micro Planning
```python
def _llm_plan(self, description: str, files: List[str], heavy: bool) -> List[Step]:
    """Use phi3:mini (or configured) to propose a tiny JSON plan. Returns [] on failure."""
    
    model = self._read_config_model() or os.getenv('JARVIS_PLAN_MODEL', 'phi3:mini')
    if not shutil.which('ollama'):
        return []
    
    file_ctx = self._file_context(files)
    prompt = f"""
You are a planner. Produce a compact JSON plan with at most 3 steps to achieve the change.
Return ONLY JSON with this schema:
{{
  "steps": [
    {{"engine": "aider|continue|codex|verify", "name": "propose|codemod|verify|search", "timeout_s": 120, "files": ["..."] }}
  ]
}}
Rules:
- Use "aider" for file-scoped changes, "continue" for repo-wide/refactor, "codex" for codemod/rename, and always end with a "verify" step.
- Do NOT include prose.
- Keep steps ≤ 3 and timeouts reasonable.

Change: {description}
Files: {', '.join(files) if files else 'none'}
Heavy: {str(heavy).lower()}
FileSummaries:
{file_ctx}
"""
    
    try:
        p = subprocess.run(["ollama", "run", model, prompt], capture_output=True, text=True, timeout=20)
        if p.returncode != 0 or not p.stdout:
            return []
        
        text = p.stdout.strip()
        # Extract JSON
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1 or end <= start:
            return []
        
        data = json.loads(text[start:end+1])
        steps_raw = data.get('steps', [])[:3]
        steps: List[Step] = []
        
        for s in steps_raw:
            eng = s.get('engine', 'aider')
            nm = s.get('name', 'propose')
            to = int(s.get('timeout_s', 120))
            fl = s.get('files', files) or files
            mdl = None
            
            if eng == 'aider':
                mdl = self._pick_code_model(heavy=False)
            elif eng == 'continue':
                mdl = self._pick_code_model(heavy=True)
            
            steps.append(Step(name=nm, engine=eng, description=description, files=fl, model=mdl, timeout_s=to))
        
        return steps
    except Exception:
        return []
```

#### Model Selection
```python
def _pick_code_model(self, heavy: bool) -> Optional[str]:
    """Select appropriate model based on task heaviness"""
    
    if not self.selector:
        return None
    
    try:
        task = getattr(TaskType, 'CODE_EDIT', None) or getattr(TaskType, 'CODE_WRITE', None)
        choice = self.selector.pick_for_task(task, heavy=heavy)
        return choice.llm
    except Exception:
        return None
```

### Key Capabilities
- Generates execution plans with up to 3 steps
- Detects simple patterns (rename operations)
- Uses LLM to generate micro-plans
- Heuristic fallback for planning
- Detects heavy and repo-wide tasks
- Selects engines based on task type (aider, continue, codex, verify)
- Configurable timeouts and model selection

---

## 6. PERMISSION LAYER (User Control & Safety)

### File Path
`/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/permission_layer.py`

### Key Patterns

#### Risk Assessment
```python
class RiskLevel(Enum):
    """Risk levels for operations"""
    SAFE = (0, "🟢", "Safe")
    LOW = (1, "🟡", "Low Risk")
    MEDIUM = (2, "🟠", "Medium Risk")
    HIGH = (3, "🔴", "High Risk")
    CRITICAL = (4, "⚠️", "Critical")

def assess_risk(self, command: str, operation_type: str = "command") -> Tuple[RiskLevel, str]:
    """Assess the risk level of a command"""
    command_lower = command.lower()
    
    # Critical risk patterns
    if any(pattern in command_lower for pattern in [
        'rm -rf /', 'rm -rf ~', 'format', 'mkfs',
        '> /dev/', 'dd if=', 'fork bomb'
    ]):
        return RiskLevel.CRITICAL, "Potentially destructive operation"
    
    # High risk patterns
    if any(pattern in command_lower for pattern in [
        'sudo', 'rm -rf', 'chmod 777', 'chown',
        'kill -9', 'killall', 'systemctl stop'
    ]):
        return RiskLevel.HIGH, "System modification or termination"
    
    # Medium risk patterns
    if any(pattern in command_lower for pattern in [
        'rm ', 'delete', 'drop', 'truncate',
        'mv ', 'cp -f', 'install', 'uninstall',
        'git push --force', 'curl', 'wget'
    ]):
        return RiskLevel.MEDIUM, "File modification or network operation"
    
    # Low risk patterns
    if any(pattern in command_lower for pattern in [
        'mkdir', 'touch', 'echo >', 'cat >',
        'pip install', 'npm install', 'apt-get',
        'git commit', 'git add'
    ]):
        return RiskLevel.LOW, "Creating or modifying user files"
    
    return RiskLevel.SAFE, "Read-only or safe operation"
```

#### Permission Request Flow
```python
def request_permission(self, 
                      command: str,
                      operation_type: str = "command",
                      details: Optional[Dict] = None) -> bool:
    """Request permission from user to execute a command"""
    
    # Bypass mode for testing
    if self.bypass_mode:
        return True
    
    # Assess risk
    risk_level, risk_reason = self.assess_risk(command, operation_type)
    
    # Create request
    request = PermissionRequest(
        command=command,
        operation_type=operation_type,
        risk_level=risk_level,
        reason=risk_reason,
        details=details or {}
    )
    
    # Check existing rules
    existing_response = self.check_existing_rules(request)
    if existing_response:
        if existing_response in [PermissionResponse.YES, PermissionResponse.YES_TO_ALL]:
            self._log_decision(request, existing_response, automatic=True)
            return True
        elif existing_response in [PermissionResponse.NO, PermissionResponse.NO_TO_ALL]:
            self._log_decision(request, existing_response, automatic=True)
            return False
    
    # Ask user
    response = self._prompt_user(request)
    
    # Process response
    return self._process_response(request, response)
```

#### Rule Matching
```python
def check_existing_rules(self, request: PermissionRequest) -> Optional[PermissionResponse]:
    """Check if we have an existing rule for this request"""
    
    # Check session rules first (yes-to-all, no-to-all)
    if self.yes_to_all:
        return PermissionResponse.YES
    if self.no_to_all:
        return PermissionResponse.NO
    
    # Check temporary session rules
    for rule in self.session_rules:
        if self._matches_rule(request, rule):
            return rule.response
    
    # Check permanent rules
    for rule in self.permanent_rules:
        if self._matches_rule(request, rule):
            if rule.expires and rule.expires < datetime.now():
                continue  # Expired rule
            return rule.response
    
    return None

def _matches_rule(self, request: PermissionRequest, rule: PermissionRule) -> bool:
    """Check if a request matches a rule"""
    
    # Check operation type
    if rule.operation_type != "*" and rule.operation_type != request.operation_type:
        return False
    
    # Check command pattern
    if rule.pattern == "*":
        return True
    elif rule.pattern.startswith("regex:"):
        pattern = rule.pattern[6:]
        return bool(re.match(pattern, request.command))
    else:
        return rule.pattern in request.command
```

#### Non-Interactive Mode
```python
def _non_interactive_decision(self, request: PermissionRequest) -> PermissionResponse:
    """Make decision in non-interactive mode based on policy"""
    
    risk_level = request.risk_level.level
    
    if self.non_interactive_policy == "strict":
        # Only allow SAFE operations
        if risk_level == 0:
            print(f"{GREEN}[Non-interactive] Auto-approved SAFE: {request.command[:50]}{RESET}")
            return PermissionResponse.YES
        else:
            print(f"{RED}[Non-interactive] Auto-denied (strict policy): {request.command[:50]}{RESET}")
            return PermissionResponse.NO
    
    elif self.non_interactive_policy == "permissive":
        # Allow everything except CRITICAL
        if risk_level < 4:
            print(f"{GREEN}[Non-interactive] Auto-approved (risk={risk_level}): {request.command[:50]}{RESET}")
            return PermissionResponse.YES
        else:
            print(f"{RED}[Non-interactive] Auto-denied CRITICAL: {request.command[:50]}{RESET}")
            return PermissionResponse.NO
    
    else:  # conservative (default)
        # Allow SAFE and LOW risk only
        if risk_level <= 1:
            print(f"{GREEN}[Non-interactive] Auto-approved (risk={risk_level}): {request.command[:50]}{RESET}")
            return PermissionResponse.YES
        else:
            print(f"{YELLOW}[Non-interactive] Auto-denied (risk={risk_level}): {request.command[:50]}{RESET}")
            return PermissionResponse.NO
```

#### Interactive Prompting
```python
def _prompt_user(self, request: PermissionRequest) -> PermissionResponse:
    """Prompt user for permission"""
    
    if self.non_interactive:
        return self._non_interactive_decision(request)
    
    # Display request with color highlighting
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{request.risk_level.icon} Permission Request {request.risk_level.icon}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    
    print(f"{CYAN}Command:{RESET} {self._highlight_command(request.command)}")
    print(f"{CYAN}Type:{RESET} {request.operation_type}")
    print(f"{CYAN}Risk:{RESET} {request.risk_level.icon} {request.risk_level.label}")
    print(f"{CYAN}Reason:{RESET} {request.reason}")
    
    # Show options
    print(f"\n{BOLD}Options:{RESET}")
    print(f"  {GREEN}y{RESET}  - Yes, allow this command")
    print(f"  {RED}n{RESET}  - No, block this command")
    print(f"  {GREEN}a{RESET}  - Yes to all (this session)")
    print(f"  {RED}x{RESET}  - No to all (this session)")
    print(f"  {BLUE}s{RESET}  - Yes to similar commands")
    print(f"  {YELLOW}e{RESET}  - Explain what this does")
    print(f"  {CYAN}m{RESET}  - Modify command")
    print(f"  {DIM}p{RESET}  - Save preference permanently")
    
    while True:
        try:
            response = input(f"\n{BOLD}Allow? [y/n/a/x/s/e/m/p]:{RESET} ").strip().lower()
            
            if response in ['y', 'yes']:
                return PermissionResponse.YES
            elif response in ['n', 'no']:
                return PermissionResponse.NO
            elif response in ['a', 'all', 'yes all']:
                return PermissionResponse.YES_TO_ALL
            elif response in ['x', 'none', 'no all']:
                return PermissionResponse.NO_TO_ALL
            elif response in ['s', 'similar']:
                return PermissionResponse.YES_TO_SIMILAR
            elif response in ['e', 'explain']:
                self._explain_command(request)
                continue
            elif response in ['m', 'modify']:
                return PermissionResponse.EDIT
            elif response in ['p', 'perm', 'permanent']:
                self._save_permanent_rule(request)
                continue
            else:
                print(f"{YELLOW}Invalid response. Please choose: y/n/a/x/s/e/m/p{RESET}")
        
        except KeyboardInterrupt:
            print(f"\n{RED}Cancelled by user{RESET}")
            return PermissionResponse.NO
        except EOFError:
            return PermissionResponse.NO
```

#### Command Explanation
```python
def _explain_command(self, request: PermissionRequest):
    """Explain what a command does"""
    
    print(f"\n{BOLD}Command Explanation:{RESET}")
    
    cmd_parts = request.command.split()
    if not cmd_parts:
        print("Empty command")
        return
    
    base_cmd = cmd_parts[0]
    
    # Common command explanations
    explanations = {
        'rm': "Remove/delete files or directories",
        'ls': "List directory contents",
        'cd': "Change directory",
        'cp': "Copy files or directories",
        'mv': "Move/rename files or directories",
        'mkdir': "Create directories",
        'sudo': "Run command with administrator privileges",
        'kill': "Terminate a process",
        'curl': "Transfer data from/to a server",
        'wget': "Download files from the internet",
        'git': "Version control operations",
        'pip': "Python package management",
        'npm': "Node.js package management",
        'docker': "Container management",
    }
    
    if base_cmd in explanations:
        print(f"  {CYAN}{base_cmd}:{RESET} {explanations[base_cmd]}")
    
    # Explain flags
    flags = [p for p in cmd_parts[1:] if p.startswith('-')]
    if flags:
        print(f"\n  {CYAN}Flags:{RESET}")
        flag_explanations = {
            '-r': "Recursive (include subdirectories)",
            '-f': "Force (no confirmation)",
            '-rf': "Recursive + Force (DANGEROUS!)",
            '-la': "List all files with details",
            '-i': "Interactive (ask before each action)",
            '-v': "Verbose (show details)",
        }
        for flag in flags:
            if flag in flag_explanations:
                print(f"    {flag}: {flag_explanations[flag]}")
```

#### Rule Persistence
```python
def _save_rules(self):
    """Save permission rules"""
    try:
        data = {
            'rules': [
                {
                    'pattern': rule.pattern,
                    'response': rule.response.value,
                    'operation_type': rule.operation_type,
                    'expires': rule.expires.isoformat() if rule.expires else None,
                    'created': rule.created.isoformat()
                }
                for rule in self.permanent_rules
                if not rule.expires or rule.expires > datetime.now()
            ]
        }
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"{YELLOW}Could not save permission rules: {e}{RESET}")

def _save_permanent_rule(self, request: PermissionRequest):
    """Save a permanent permission rule"""
    
    print(f"\n{BOLD}Save Permission Rule:{RESET}")
    print(f"1. Always allow this exact command")
    print(f"2. Always allow similar commands ({self._create_similar_pattern(request.command)}*)")
    print(f"3. Always block this exact command")
    print(f"4. Always block similar commands")
    print(f"5. Cancel")
    
    choice = input(f"\n{BOLD}Choice [1-5]:{RESET} ").strip()
    
    if choice == '1':
        rule = PermissionRule(
            pattern=request.command,
            response=PermissionResponse.YES,
            operation_type=request.operation_type
        )
        self.permanent_rules.append(rule)
        self._save_rules()
        print(f"{GREEN}✓ Saved: Always allow '{request.command}'{RESET}")
```

### Key Capabilities
- Risk assessment with 5 levels (Safe, Low, Medium, High, Critical)
- Interactive permission prompts with color highlighting
- Non-interactive mode with 3 policies (strict, conservative, permissive)
- Session rules (yes-to-all, no-to-all, similar commands)
- Permanent rules with pattern matching and expiration
- Rule persistence to JSON files
- Command explanation and modification
- Statistics tracking and reporting

---

## 7. CLI ORCHESTRATOR (Multi-Tool Execution)

### File Path
`/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/external/Agent/jarvis_pkg/core/cli_orchestrator.py`

### Key Patterns

#### Route Definition
```python
@dataclass
class CLIRoute:
    tool: str  # 'codex', 'claude_code', 'warp' (generic external)
    command: str
    context: Dict[str, Any]
    priority: int = 1
```

#### Heuristic Routing
```python
async def _get_routing_decision(self, task: str, context: Dict[str, Any]) -> CLIRoute:
    """Very simple heuristic router.
    - Prefer 'codex' when task mentions refactor/move/rename/import/diff
    - Fallback to generic 'claude_code' for broader coding queries
    - If explicit tool provided in context, honor it
    """
    cache_key = f"{task}|{json.dumps(context, sort_keys=True)}"
    if cache_key in self.routing_cache:
        return self.routing_cache[cache_key]
    
    explicit = (context or {}).get("tool")
    if explicit in {"codex", "claude_code", "warp"}:
        cmd = self._resolve_command(explicit, task, context)
        route = CLIRoute(tool=explicit, command=cmd, context=context, priority=1)
        self.routing_cache[cache_key] = route
        return route
    
    t = task.lower()
    codemod_triggers = ("refactor", "rename", "imports", "move", "diff", "organize imports")
    if any(k in t for k in codemod_triggers):
        cmd = self._resolve_command("codex", task, context)
        route = CLIRoute(tool="codex", command=cmd, context=context, priority=1)
        self.routing_cache[cache_key] = route
        return route
    
    # Default to 'claude_code'
    cmd = self._resolve_command("claude_code", task, context)
    route = CLIRoute(tool="claude_code", command=cmd, context=context, priority=1)
    self.routing_cache[cache_key] = route
    return route
```

#### Command Execution with Timeout & Retry
```python
async def _run_command(
    self, cmd: str, *, timeout_s: Optional[int] = None, cwd: Optional[str | Path] = None
) -> Tuple[int, str, str, float]:
    """Run a shell command asynchronously and capture output."""
    
    # Safety gate
    ok, reason = self._is_command_allowed(cmd)
    if not ok:
        return (126, "", f"blocked by policy: {reason}", 0.0)
    
    # Optional sandbox wrapper
    sandbox = os.environ.get("ORCH_SANDBOX_CMD")
    if sandbox:
        cmd = f"{sandbox} {cmd}"
    
    start = time.monotonic()
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    try:
        to = timeout_s if timeout_s is not None else self.default_timeout_s
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=to)
    except asyncio.TimeoutError:
        with contextlib.suppress(Exception):
            proc.kill()
        return (124, "", f"timeout after {to}s", time.monotonic() - start)
    
    rc = proc.returncode
    dur = time.monotonic() - start
    return (rc, out_b.decode(errors="ignore"), err_b.decode(errors="ignore"), dur)
```

#### Retry with Exponential Backoff
```python
async def _run_with_retry(
    self,
    cmd: str,
    *,
    timeout_s: Optional[int],
    cwd: Optional[str | Path],
    retries: Optional[int] = None,
    backoff_base: Optional[float] = None,
) -> Tuple[int, str, str, float]:
    """Run command with bounded retries and jitter backoff."""
    
    attempts = int(os.environ.get("ORCH_RETRIES", "2")) if retries is None else int(retries)
    base = (
        float(os.environ.get("ORCH_BACKOFF_BASE", "0.35"))
        if backoff_base is None
        else float(backoff_base)
    )
    
    total_dur = 0.0
    last_rc, last_out, last_err = 0, "", ""
    
    for i in range(max(1, attempts + 1)):
        rc, out, err, dur = await self._run_command(cmd, timeout_s=timeout_s, cwd=cwd)
        total_dur += dur
        last_rc, last_out, last_err = rc, out, err
        
        # Don't retry non-retryable conditions
        if rc == 0 or rc in (124, 126, 127):
            break
        
        # Backoff before next try
        if i < attempts:
            delay = base * (2**i) + random.uniform(0, base)
            try:
                await asyncio.sleep(delay)
            except Exception:
                pass
    
    return last_rc, last_out, last_err, total_dur
```

#### Parallel Execution
```python
async def _execute_parallel(self, route: CLIRoute) -> Dict[str, Any]:
    """Run a parallel sweep across known tools using the same command."""
    
    # Build candidate routes
    candidates: List[CLIRoute] = []
    for tool in ("codex", "claude_code", "warp"):
        cmd = self._resolve_command(tool, route.context.get("task", ""), route.context)
        candidates.append(CLIRoute(tool=tool, command=cmd, context=route.context, priority=1))
    
    async def run_one(r: CLIRoute) -> Dict[str, Any]:
        if r.tool == "codex":
            return await self._execute_codex(r)
        if r.tool == "claude_code":
            return await self._execute_claude_code(r)
        return await self._execute_warp(r)
    
    results = await asyncio.gather(*(run_one(r) for r in candidates))
    
    # First success wins
    for res in results:
        if res.get("ok"):
            return res
    
    # Otherwise pick the one with smallest return code (or shortest duration)
    results.sort(key=lambda x: (x.get("returncode", 9999), x.get("duration_s", 9999.0)))
    return results[0]
```

#### Policy-Based Command Filtering
```python
def _is_command_allowed(self, cmd: str) -> Tuple[bool, str]:
    """Simple allow/deny policy using regex env vars."""
    
    # Hard-deny dangerous patterns
    hard_deny = [r"\brm\s+-rf\b", r"\bshutdown\b", r"\breboot\b", r":\(\)\{:\|:&\};:"]
    for pat in hard_deny:
        if re.search(pat, cmd):
            return False, f"matches hard deny: {pat}"
    
    # Environment-based deny list
    deny_rx = os.environ.get("ORCH_DENY_CMDS_REGEX")
    if deny_rx:
        try:
            if re.search(deny_rx, cmd):
                return False, f"matches deny regex"
        except re.error:
            pass
    
    # Environment-based allow list
    allow_rx = os.environ.get("ORCH_ALLOW_CMDS_REGEX")
    if allow_rx:
        try:
            if not re.search(allow_rx, cmd):
                return False, "does not match allow regex"
        except re.error:
            return False, "invalid allow regex"
    
    return True, "ok"
```

### Key Capabilities
- Routes tasks to multiple CLI tools (codex, claude_code, warp)
- Caches routing decisions
- Executes commands asynchronously with configurable timeouts
- Implements exponential backoff retry strategy
- Runs tools in parallel and selects best result
- Hard-deny dangerous patterns
- Environment-based allow/deny regex policies
- Captures stdout/stderr and execution time

---

## Summary Table

| Component | Purpose | Key Innovation |
|-----------|---------|-----------------|
| **Adaptive Router** | Routes tasks to optimal tools | Blends base confidence with historical success rates |
| **Enhanced Router** | Pattern-based routing | Multi-type patterns with context hints & negative patterns |
| **Learning System** | Learns from execution | Tracks success patterns, preferences, styles, project context |
| **RAG Pipeline** | Retrieves relevant context | Multiple embedding backends with fallback strategy |
| **Planner** | Creates execution plans | Heuristic + LLM-based planning with step orchestration |
| **Permission Layer** | User control & safety | Risk assessment with interactive & non-interactive modes |
| **CLI Orchestrator** | Multi-tool execution | Parallel execution with retry, timeout, and policy-based filtering |

---

## Integration Points

1. **Adaptive Router** uses Learning System for success rates and preferences
2. **Learning System** stores data used by Adaptive Router for future decisions
3. **RAG Pipeline** provides context that informs task routing and planning
4. **Planner** receives routing decisions and creates execution steps
5. **Permission Layer** gates execution based on risk assessment
6. **CLI Orchestrator** executes plans with safety controls and retry logic

---

## Configuration & Environment Variables

```bash
# Learning system
JARVIS_LEARNING_DB=~/.ai_agent/learning.db

# Embedding backend
JARVIS_EMBED_BACKEND=mlx  # or ollama
JARVIS_EMBEDDING_MODEL=nomic-embed-text

# Planner
JARVIS_PLAN_MODEL=phi3:mini

# CLI Orchestrator
ORCH_SANDBOX_CMD=none
ORCH_RETRIES=2
ORCH_BACKOFF_BASE=0.35
ORCH_DENY_CMDS_REGEX=None
ORCH_ALLOW_CMDS_REGEX=None
ORCH_CMD_CLAUDE_CODE=None
ORCH_CMD_WARP=None

# Permission Layer
JARVIS_NON_INTERACTIVE=false
JARVIS_BYPASS_PERMISSIONS=false
JARVIS_PERMISSIONS_CONFIG=~/.jarvis_permissions.json
```

---

