# Jarvis Agent Exploration - Complete Documentation

This directory contains comprehensive documentation about the Jarvis Agent project's intelligent task routing and learning systems.

## Files Included

### 1. JARVIS_QUICK_REFERENCE.md
**Best for**: Quick lookup, getting started, usage examples

Contains:
- File locations and purposes
- Quick usage examples for all components
- Key concepts explained simply
- Configuration guide
- Most important patterns to copy
- Integration flow diagram
- Testing instructions

**Start here if you want to**: Quickly understand the system and start using it.

### 2. jarvis_exploration_summary.md
**Best for**: Deep understanding, architecture details, complete patterns

Contains:
- Detailed overview of all 7 components
- Complete code patterns for each component
- Database schema definitions
- Data structures and classes
- Method-by-method documentation
- Configuration and environment variables
- Integration points between components
- Summary table and design patterns

**Read this for**: Complete understanding of how everything works internally.

### 3. jarvis_files_summary.txt
**Best for**: Reference guide, file locations, method inventory

Contains:
- Absolute file paths to all components
- Class and method inventories
- Parameter descriptions
- Pattern library examples
- Database table descriptions
- Integration flow diagram (ASCII)
- Key design patterns with code snippets
- Configuration reference
- Guidance on copying patterns

**Use this for**: Finding specific methods, understanding database schema, copying patterns.

## Quick Navigation

### If you want to implement...

**Adaptive Task Routing**
- Read: JARVIS_QUICK_REFERENCE.md > Adaptive Routing section
- Deep dive: jarvis_exploration_summary.md > Section 1: ADAPTIVE ROUTER
- Copy from: `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/adaptive_router.py`

**Learning System**
- Read: JARVIS_QUICK_REFERENCE.md > Learning System section
- Deep dive: jarvis_exploration_summary.md > Section 3: LEARNING SYSTEM
- Copy from: `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/learning_system.py`

**RAG/Context Retrieval**
- Read: JARVIS_QUICK_REFERENCE.md > RAG Pipeline section
- Deep dive: jarvis_exploration_summary.md > Section 4: RAG PIPELINE
- Copy from: `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/rag_pipeline.py`

**Permission/Safety System**
- Read: JARVIS_QUICK_REFERENCE.md > Permission Layer section
- Deep dive: jarvis_exploration_summary.md > Section 6: PERMISSION LAYER
- Copy from: `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/permission_layer.py`

**Multi-Tool Execution**
- Read: JARVIS_QUICK_REFERENCE.md > CLI Orchestrator section
- Deep dive: jarvis_exploration_summary.md > Section 7: CLI ORCHESTRATOR
- Copy from: `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/external/Agent/jarvis_pkg/core/cli_orchestrator.py`

## Key Patterns to Copy

### 1. Confidence Blending (Adaptive Routing)
Blend pattern-matching confidence (60%) with historical success rate (40%) for adaptive routing decisions.

### 2. Pattern Matching with Modifiers
Use keyword/regex patterns with context hints (boost) and negative patterns (reduce) for task classification.

### 3. Success Tracking (Learning)
Track execution success with hashed patterns to build confidence scores over time.

### 4. Embedding with Fallback
Try multiple embedding backends (unified, primary, secondary) with CPU hash fallback.

### 5. Retry with Exponential Backoff
Implement exponential backoff with jitter for robust command execution.

### 6. Risk Assessment (Permission)
Classify commands into 5 risk levels and handle interactive/non-interactive modes differently.

### 7. Rule Matching (Permission)
Support both temporary (session) and permanent rules with pattern matching and expiration.

## Component Overview

```
INPUT: User Command
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
OUTPUT: Execution Result
  |
  v
Learning System (feedback loop)
  (Record for next time)
```

## Implementation Order

1. **Start**: Enhanced Router (basic pattern matching)
2. **Add**: Learning System (track success patterns)
3. **Integrate**: Adaptive Router (blend confidence)
4. **Add**: RAG Pipeline (retrieve context)
5. **Add**: Task Planner (generate execution plans)
6. **Add**: Permission Layer (user safety)
7. **Finally**: CLI Orchestrator (multi-tool execution)

## Configuration

All major components use environment variables:

```bash
# Embedding
export JARVIS_EMBED_BACKEND=mlx
export JARVIS_EMBEDDING_MODEL=nomic-embed-text

# Planning
export JARVIS_PLAN_MODEL=phi3:mini

# Permission
export JARVIS_NON_INTERACTIVE=false
export JARVIS_NON_INTERACTIVE_POLICY=conservative

# CLI Orchestrator
export ORCH_RETRIES=2
export ORCH_BACKOFF_BASE=0.35
```

## Database Schema

Learning System uses SQLite with these tables:
- `success_patterns`: Command/tool success rates
- `user_preferences`: Learned user preferences
- `coding_styles`: Detected coding styles
- `project_contexts`: Project metadata
- `recommendations`: Recommendation history
- `learning_feedback`: Execution feedback

Location: `~/.ai_agent/learning.db`

## Testing

Each module includes test functions:

```bash
python adaptive_router.py
python learning_system.py
python enhanced_router.py
python permission_layer.py
python planner.py
```

## Key Insights

### Why This Architecture Works

1. **Adaptive Routing**: Combines pattern matching with learning for both accuracy and adaptability
2. **Success Tracking**: Historical data prevents routing to failing tools
3. **Preference Learning**: System learns what the user actually prefers
4. **Style Detection**: Maintains consistency with existing codebase
5. **Permission Gates**: Safety without constant user interruption (via rules)
6. **Retry Strategy**: Handles transient failures gracefully
7. **Multi-tool Support**: Parallel execution for fallback scenarios

### Most Important Innovations

1. **60/40 Confidence Blending**: Balances pattern accuracy with historical success
2. **Context-Aware Modifiers**: Hints boost and negative patterns reduce confidence
3. **Signal-Based Learning**: Positive/negative signals build confidence over time
4. **Multi-Level Fallback Embeddings**: Guarantees embeddings even without GPU/internet
5. **Non-Interactive Policies**: Safety for CI/CD without user interaction

## Further Reading

- See jarvis_exploration_summary.md for complete implementation details
- See jarvis_files_summary.txt for method inventory and database schemas
- See JARVIS_QUICK_REFERENCE.md for usage examples and patterns

---

Generated: November 5, 2025
Source: Jarvis Agent at `/Users/indiedevhipps/Library/CloudStorage/ProtonDrive-josh.hipps@pm.me-folder/Developer/Jarvis Agent/Agent/`

