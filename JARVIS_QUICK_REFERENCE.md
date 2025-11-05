# Jarvis Agent - Quick Reference Guide

## File Locations

All files are in: `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/`

| Component | File | Purpose |
|-----------|------|---------|
| Adaptive Router | `adaptive_router.py` | Routes tasks with learning insights |
| Enhanced Router | `enhanced_router.py` | Pattern-based routing with confidence |
| Learning System | `learning_system.py` | Learns preferences, styles, contexts |
| RAG Pipeline | `rag_pipeline.py` | Retrieves relevant code context |
| Task Planner | `planner.py` | Creates execution plans |
| Permission Layer | `permission_layer.py` | User control & safety gates |
| CLI Orchestrator | `external/Agent/jarvis_pkg/core/cli_orchestrator.py` | Multi-tool execution |

## Quick Usage Examples

### 1. Adaptive Routing
```python
from adaptive_router import AdaptiveRouter
from learning_system import LearningSystem
from jarvis_bigquery_memory import JarvisBigQueryMemory

# Create router with learning
memory = JarvisBigQueryMemory()
learning = LearningSystem(memory=memory)
router = AdaptiveRouter(memory=memory, learning=learning)

# Route a command
result = router.route_task("create a new Python function")
print(f"Route: {result.tool_type}")
print(f"Confidence: {result.confidence:.0%}")
print(f"Adjusted: {result.adjusted_confidence:.0%}")

# Record feedback for learning
router.record_execution_result("create a new Python function", "aider", True, 2.5)

# Get explanation
explanation = router.explain_routing("write tests for calculator")
print(explanation)
```

### 2. Learning System
```python
from learning_system import LearningSystem

learner = LearningSystem()

# Track execution
learner.track_execution("fix bug in test.py", "aider", True, 3.0)

# Get success rate
rate = learner.get_success_rate("fix bug in test.py", "aider")

# Get learned preferences
prefs = learner.get_preferences("tool")
for pref in prefs:
    print(f"{pref.preference}: {pref.confidence:.0%}")

# Detect coding style
with open("example.py") as f:
    style = learner.detect_coding_style("example.py", f.read())
    print(f"Indent: {style.patterns.get('indent')}")
    print(f"Quotes: {style.patterns.get('quotes')}")

# Get recommendations
recs = learner.get_recommendations("create calculator.py")
for rec in recs:
    print(f"- {rec.action} ({rec.confidence:.0%})")
```

### 3. RAG Pipeline
```python
from rag_pipeline import retrieve_context_for_command, ingest_paths

# Ingest files into RAG
ingest_paths(["src/main.py", "src/utils.py"], tags=["source", "python"])

# Retrieve context for a command
snippets = retrieve_context_for_command(
    "how does the calculator function work?",
    max_snippets=4
)
for snippet in snippets:
    print(snippet)
    print("---")
```

### 4. Permission Layer
```python
from permission_layer import PermissionLayer

perms = PermissionLayer(non_interactive=False)

# Interactive permission
allowed = perms.request_permission("rm test.txt", "file_delete")

# Non-interactive mode
perms_strict = PermissionLayer(
    non_interactive=True,
    non_interactive_policy="strict"
)
allowed = perms_strict.request_permission("rm test.txt")

# Check risk level
risk_level, reason = perms.assess_risk("git push --force")
print(f"Risk: {risk_level.label} - {reason}")

# View stats
stats = perms.get_statistics()
print(f"Allowed: {stats['allowed']}/{stats['total_requests']}")
```

### 5. Task Planner
```python
from planner import Planner

planner = Planner()

# Create a plan
plan = planner.plan("refactor the authentication module", 
                   files=["src/auth.py", "src/config.py"])

print(f"Steps: {len(plan.steps)}")
for step in plan.steps:
    print(f"  - {step.name} ({step.engine}): {step.description}")
    print(f"    Timeout: {step.timeout_s}s")
```

### 6. CLI Orchestrator
```python
import asyncio
from cli_orchestrator import MetalCLIOrchestrator

async def main():
    orchestrator = MetalCLIOrchestrator(max_workers=4, default_timeout_s=120)
    
    result = await orchestrator.route_and_execute(
        task="refactor the authentication module",
        context={"tool": "codex", "files": ["src/auth.py"]}
    )
    
    print(f"Tool: {result['tool']}")
    print(f"Success: {result['ok']}")
    print(f"Duration: {result['duration_s']:.2f}s")
    print(f"Stdout: {result['stdout'][:200]}")
    if result['stderr']:
        print(f"Stderr: {result['stderr'][:200]}")

asyncio.run(main())
```

## Key Concepts

### Confidence Adjustment
The adaptive router blends two sources of confidence:
- **Base Confidence (60%)**: From pattern matching in Enhanced Router
- **Success Rate (40%)**: From historical Learning System data

```
Adjusted Confidence = (Base * 0.6) + (Success Rate * 0.4)
```

### Pattern Types
Enhanced Router supports 3 pattern types:
1. **Keyword**: Simple substring matching (high precision)
2. **Regex**: Regular expression matching (flexible)
3. **Fuzzy**: Fuzzy string matching (forgiving)

### Risk Levels
Permission Layer has 5 risk categories:
- **SAFE** (0): Read-only operations
- **LOW** (1): File creation, git add/commit
- **MEDIUM** (2): File deletion, network ops
- **HIGH** (3): System modification, kill processes
- **CRITICAL** (4): Destructive operations (rm -rf /, format)

### Learning Categories
Learning System tracks:
- **Tool Preferences**: Which tools succeed most
- **Workflow Preferences**: Test-first, docs-focused, etc.
- **Style Patterns**: Indentation, quotes, naming conventions
- **Project Context**: Type, languages, frameworks, workflows

### Execution Engines
Planner routes to 4 engines:
- **aider**: File-scoped code changes
- **continue**: Repo-wide refactoring
- **codex**: Codemod and rename operations
- **verify**: Testing and verification

## Configuration

### Environment Variables
```bash
# Embedding backend
export JARVIS_EMBED_BACKEND=mlx  # or ollama
export JARVIS_EMBEDDING_MODEL=nomic-embed-text

# Planning
export JARVIS_PLAN_MODEL=phi3:mini

# Non-interactive mode
export JARVIS_NON_INTERACTIVE=true
export JARVIS_NON_INTERACTIVE_POLICY=conservative  # strict, conservative, permissive

# CLI Orchestrator
export ORCH_RETRIES=2
export ORCH_BACKOFF_BASE=0.35
export ORCH_DENY_CMDS_REGEX=''
export ORCH_ALLOW_CMDS_REGEX=''
```

### Database Locations
- Learning System: `~/.ai_agent/learning.db`
- Permissions: `~/.jarvis_permissions.json`
- Config: `~/.ai_agent/config.json`

## Integration Pattern

The full pipeline works like this:

```
User Command
    |
    v
Adaptive Router + Learning System
    (Route with historical context)
    |
    v
Task Planner
    (Create execution steps)
    |
    v
Permission Layer
    (Ask user or apply policy)
    |
    v
CLI Orchestrator
    (Execute with retries)
    |
    v
Learning System
    (Record outcome for next time)
```

## Most Important Patterns to Copy

### 1. Confidence Blending (for adaptive routing)
```python
def adjust_confidence(base_conf, success_rate):
    return (base_conf * 0.6) + (success_rate * 0.4)
```

### 2. Pattern Matching with Modifiers (for task classification)
```python
# Base confidence from pattern
confidence = match_score

# Apply context hints (boost)
if context_hint in command:
    confidence += 0.1

# Apply negative patterns (reduce)
if negative_pattern in command:
    confidence -= 0.3

# Apply weight
confidence *= pattern_weight
```

### 3. Success Tracking (for learning)
```python
# Track execution
pattern_hash = md5(f"{command}_{tool}")
success_count += 1 if success else 0
failure_count += 0 if success else 1
confidence = success_count / (success_count + failure_count)
```

### 4. Embedding with Fallback (for robust RAG)
```python
def embed(text):
    try: return unified_embedder(text)
    except: pass
    
    try: return primary_backend(text)
    except: pass
    
    try: return fallback_backend(text)
    except: pass
    
    return hash_embed(text)
```

### 5. Retry with Exponential Backoff
```python
base = 0.35
for attempt in range(max_attempts):
    result = execute(command)
    if success or non_retryable_error:
        return result
    
    delay = base * (2 ** attempt) + random(0, base)
    sleep(delay)
```

## Testing

Each module includes a test function at the bottom:
```bash
# Test adaptive router
python adaptive_router.py

# Test learning system
python learning_system.py

# Test enhanced router
python enhanced_router.py

# Test permission layer
python permission_layer.py
```

## Next Steps

1. Copy the required files to your project
2. Configure environment variables
3. Initialize Learning System (creates DB)
4. Start with Enhanced Router for basic routing
5. Add Learning System for adaptation
6. Add Permission Layer for safety
7. Integrate CLI Orchestrator for execution

