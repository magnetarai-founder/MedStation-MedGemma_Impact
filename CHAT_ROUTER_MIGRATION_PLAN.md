# Chat Router Migration Plan - Final Migration (5/5)

## Status: Ready to Execute

This is the final router migration to complete the 5-part router migration project.

---

## Overview

**Current State:**
- chat_service.py: 2,231 lines, 48 endpoints
- chat_enhancements.py: 322 lines (utilities - keep as-is)
- chat_memory.py: 861 lines (storage layer - keep as-is)

**Target State:**
- api/schemas/chat_models.py: 11 Pydantic models (~150 lines)
- api/services/chat.py: Business logic (~1,800 lines)
- api/routes/chat.py: Thin router (~1,200 lines)

**Complexity:** HIGH (largest migration, streaming responses, Metal 4 integration)

---

## Pydantic Models to Extract (11 models)

Located in chat_service.py lines 137-179, 1287-1291, 1592-1594, 1715-1721, 1877-1880, 1944-1946, 2054-2057:

1. **ChatMessage** (lines 137-143)
   ```python
   role: str
   content: str
   timestamp: str
   files: List[Dict[str, Any]] = []
   model: Optional[str] = None
   tokens: Optional[int] = None
   ```

2. **ChatSession** (lines 146-152)
   ```python
   id: str
   title: str
   created_at: str
   updated_at: str
   model: str = "qwen2.5-coder:7b-instruct"
   message_count: int = 0
   ```

3. **CreateChatRequest** (lines 155-157)
   ```python
   title: Optional[str] = "New Chat"
   model: Optional[str] = "qwen2.5-coder:7b-instruct"
   ```

4. **SendMessageRequest** (lines 160-173)
   ```python
   content: str
   model: Optional[str] = None
   temperature: Optional[float] = 0.7
   top_p: Optional[float] = 0.9
   top_k: Optional[int] = 40
   repeat_penalty: Optional[float] = 1.1
   system_prompt: Optional[str] = None
   use_recursive: Optional[bool] = True
   ```

5. **OllamaModel** (lines 175-178)
   ```python
   name: str
   size: str
   modified_at: str
   ```

6. **ExportToChatRequest** (lines 1287-1291)
   ```python
   session_id: str
   query_id: str
   query: str
   results: List[Dict[str, Any]]
   ```

7. **RestartServerRequest** (lines 1592-1594)
   ```python
   reason: str = "Manual restart"
   ```

8. **RouterFeedback** (lines 1715-1721)
   ```python
   session_id: str
   model_chosen: str
   quality_score: int  # 1-5
   feedback: Optional[str] = None
   ```

9. **RecursiveQueryRequest** (lines 1877-1880)
   ```python
   query: str
   session_id: Optional[str] = None
   ```

10. **SetModeRequest** (lines 1944-1946)
    ```python
    mode: str  # "efficiency", "balanced", "performance"
    ```

11. **PanicTriggerRequest** (lines 2054-2057)
    ```python
    reason: str
    wipe_data: bool = False
    ```

---

## All 48 Endpoints by Category

### Session Management (5 endpoints)
1. `POST /sessions` - Create chat session (operation_id: `chat_sessions_create`)
2. `GET /sessions` - List sessions (operation_id: `chat_sessions_list`)
3. `GET /sessions/{chat_id}` - Get session (operation_id: `chat_sessions_get`)
4. `DELETE /sessions/{chat_id}` - Delete session (operation_id: `chat_sessions_delete`)
5. `POST /sessions/{chat_id}/messages` - Send message **[STREAMING]** (operation_id: `chat_messages_send`)

### File Management (1 endpoint)
6. `POST /sessions/{chat_id}/upload` - Upload file (operation_id: `chat_files_upload`)

### Model Management (9 endpoints)
7. `GET /models` - List models **[PUBLIC]** (operation_id: `chat_models_list`)
8. `GET /models/status` - Model status **[PUBLIC]** (operation_id: `chat_models_status`)
9. `GET /models/hot-slots` - Hot slot assignments **[PUBLIC]** (operation_id: `chat_models_hot_slots`)
10. `GET /models/orchestrator-suitable` - Orchestrator models **[PUBLIC]** (operation_id: `chat_models_orchestrator`)
11. `POST /models/preload` - Preload model (operation_id: `chat_models_preload`)
12. `POST /models/hot-slots/{slot_number}` - Assign hot slot (operation_id: `chat_models_hot_slot_assign`)
13. `DELETE /models/hot-slots/{slot_number}` - Remove hot slot (operation_id: `chat_models_hot_slot_remove`)
14. `POST /models/load-hot-slots` - Load all hot slots (operation_id: `chat_models_hot_slots_load`)
15. `POST /models/unload/{model_name}` - Unload model (operation_id: `chat_models_unload`)

### Search & Analytics (4 endpoints)
16. `GET /search` - Semantic search (operation_id: `chat_search_semantic`)
17. `GET /analytics` - Get analytics (operation_id: `chat_analytics_get`)
18. `GET /sessions/{chat_id}/analytics` - Session analytics (operation_id: `chat_analytics_session`)
19. `POST /sessions/{chat_id}/token-count` - Token count (operation_id: `chat_tokens_count`)

### Health & Status (3 endpoints - PUBLIC)
20. `GET /health` - Check health **[PUBLIC]** (operation_id: `chat_health_check`)
21. `GET /ane/stats` - ANE stats (operation_id: `chat_ane_stats`)
22. `GET /embedding/info` - Embedding info (operation_id: `chat_embedding_info`)

### ANE Context (1 endpoint)
23. `GET /ane/search` - ANE context search (operation_id: `chat_ane_search`)

### System Management (6 endpoints)
24. `GET /system/memory` - Memory stats (operation_id: `chat_system_memory`)
25. `GET /ollama/server/status` - Server status **[PUBLIC]** (operation_id: `chat_ollama_status`)
26. `POST /ollama/server/shutdown` - Shutdown server (operation_id: `chat_ollama_shutdown`)
27. `POST /ollama/server/start` - Start server (operation_id: `chat_ollama_start`)
28. `POST /ollama/server/restart` - Restart server (operation_id: `chat_ollama_restart`)

### Data Export (1 endpoint)
29. `POST /data/export-to-chat` - Export to chat (operation_id: `chat_export_data`)

### Adaptive Router (5 endpoints)
30. `POST /adaptive-router/feedback` - Router feedback (operation_id: `chat_router_feedback`)
31. `GET /adaptive-router/stats` - Router stats (operation_id: `chat_router_stats`)
32. `GET /adaptive-router/explain` - Explain routing (operation_id: `chat_router_explain`)
33. `GET /router/mode` - Get router mode (operation_id: `chat_router_mode_get`)
34. `POST /router/mode` - Set router mode (operation_id: `chat_router_mode_set`)

### Recursive Prompting (2 endpoints)
35. `POST /recursive-prompt/execute` - Execute recursive (operation_id: `chat_recursive_execute`)
36. `GET /recursive-prompt/stats` - Recursive stats (operation_id: `chat_recursive_stats`)

### Ollama Configuration (3 endpoints)
37. `GET /ollama/config` - Get config (operation_id: `chat_ollama_config_get`)
38. `POST /ollama/config/mode` - Set mode (operation_id: `chat_ollama_config_mode`)
39. `POST /ollama/config/auto-detect` - Auto-detect (operation_id: `chat_ollama_config_detect`)

### Performance Monitoring (5 endpoints)
40. `GET /performance/current` - Current metrics (operation_id: `chat_performance_current`)
41. `GET /performance/stats` - Statistics (operation_id: `chat_performance_stats`)
42. `GET /performance/history` - History (operation_id: `chat_performance_history`)
43. `GET /performance/thermal` - Thermal check (operation_id: `chat_performance_thermal`)
44. `POST /performance/reset` - Reset metrics (operation_id: `chat_performance_reset`)

### Panic Mode (3 endpoints)
45. `POST /panic/trigger` - Trigger panic (operation_id: `chat_panic_trigger`)
46. `GET /panic/status` - Panic status (operation_id: `chat_panic_status`)
47. `POST /panic/reset` - Reset panic (operation_id: `chat_panic_reset`)

### Learning System (6 endpoints)
48. `GET /learning/patterns` - Learning patterns (operation_id: `chat_learning_patterns`)
49. `GET /learning/recommendations` - Recommendations (operation_id: `chat_learning_recommendations`)
50. `POST /learning/recommendations/{recommendation_id}/accept` - Accept (operation_id: `chat_learning_accept`)
51. `POST /learning/recommendations/{recommendation_id}/reject` - Reject (operation_id: `chat_learning_reject`)
52. `GET /learning/optimal-model/{task_type}` - Optimal model (operation_id: `chat_learning_optimal`)
53. `POST /learning/track-usage` - Track usage (operation_id: `chat_learning_track`)

**Note:** Actually 53 endpoints total (analysis found 5 more than initially counted)

---

## Service Layer Functions to Create

### Session Management Service (5 functions)
- `create_session(title, model, user_id, team_id)`
- `list_sessions(user_id, role, team_id)`
- `get_session(chat_id, user_id, role, team_id)`
- `delete_session(chat_id, user_id, role, team_id)`
- `get_session_analytics(chat_id, user_id, role, team_id)`

### Message Service (3 functions)
- `send_message(chat_id, content, model, params, user_id, team_id)` **[RETURNS STREAM]**
- `get_token_count(chat_id, content)`
- `add_system_message(chat_id, content)`

### File Service (1 function)
- `upload_file(chat_id, file, user_id, team_id)`

### Model Service (9 functions)
- `list_models()`
- `get_model_status()`
- `get_hot_slots()`
- `get_orchestrator_models()`
- `preload_model(model_name)`
- `assign_hot_slot(slot_number, model_name)`
- `remove_hot_slot(slot_number)`
- `load_hot_slots()`
- `unload_model(model_name)`

### Search Service (3 functions)
- `semantic_search(query, limit, user_id, team_id)`
- `get_analytics(user_id, team_id)`
- `search_ane_context(query, limit)`

### System Service (2 functions)
- `get_system_memory()`
- `get_embedding_info()`

### Ollama Service (6 functions)
- `check_health()`
- `get_server_status()`
- `shutdown_server()`
- `start_server()`
- `restart_server(reason)`
- `get_ollama_config()`

### Router Service (5 functions)
- `submit_feedback(feedback)`
- `get_router_stats()`
- `explain_routing(query, context)`
- `get_router_mode()`
- `set_router_mode(mode)`

### Recursive Service (2 functions)
- `execute_recursive(query, session_id)`
- `get_recursive_stats()`

### Config Service (2 functions)
- `set_ollama_mode(mode)`
- `auto_detect_config()`

### Performance Service (5 functions)
- `get_current_performance()`
- `get_performance_stats()`
- `get_performance_history(days)`
- `check_thermal_throttling()`
- `reset_performance_metrics()`

### Panic Service (3 functions)
- `trigger_panic(reason, wipe_data, user_id)`
- `get_panic_status()`
- `reset_panic()`

### Learning Service (6 functions)
- `get_learning_patterns(limit)`
- `get_recommendations()`
- `accept_recommendation(recommendation_id)`
- `reject_recommendation(recommendation_id)`
- `get_optimal_model(task_type)`
- `track_usage(model, task_type, quality)`

### Export Service (1 function)
- `export_data_to_chat(session_id, query_id, query, results, user_id, team_id)`

**Total Service Functions:** 57 functions

---

## Migration Strategy

### Phase 1: Extract Models (30 min)
1. Create `api/schemas/chat_models.py`
2. Extract all 11 Pydantic models
3. Add proper imports and docstrings

### Phase 2: Create Service Layer (2-3 hours)
1. Create `api/services/chat.py`
2. Extract business logic from all 48 endpoints
3. Keep ChatStorage and OllamaClient helper classes
4. Use lazy imports for:
   - chat_memory (get_memory)
   - chat_enhancements (all utility classes)
   - ane_context_engine, token_counter, model_manager
   - metal4_engine, adaptive_router, learning_system
   - permission_engine, auth_middleware
5. Preserve streaming logic in send_message
6. Preserve Metal 4 parallel GPU operations

### Phase 3: Create Thin Router (2-3 hours)
1. Create `api/routes/chat.py`
2. Create 48 thin endpoint wrappers
3. Delegate all logic to service layer
4. Lazy import service and models
5. Preserve StreamingResponse for send_message
6. Add consistent operation IDs (chat_* pattern)
7. Use tags: ["chat"] for authenticated, ["chat-public"] for public

### Phase 4: Update Main Registration (10 min)
1. Update main.py router registration
2. Change from `chat_service.router` to `api.routes.chat.router`
3. Add error logging with exc_info=True

### Phase 5: Testing (30-60 min)
1. Test session CRUD operations
2. Test message sending with streaming
3. Test file upload
4. Test model management
5. Test semantic search
6. Test public endpoints (health, models)
7. Verify team filtering works correctly

---

## Critical Considerations

### 1. Streaming Response
The `send_message` endpoint uses `StreamingResponse` with SSE format:
```python
return StreamingResponse(
    _generate_sse(chunks),
    media_type="text/event-stream"
)
```
**Must preserve this in the service layer and router!**

### 2. Public Endpoints
Some endpoints have no auth dependency (public routers):
- `/health`
- `/models`
- `/models/status`
- `/models/hot-slots`
- `/models/orchestrator-suitable`
- `/ollama/server/status`

**Create separate router without auth dependency for these!**

### 3. Team Filtering
All session/message operations filter by:
- `user_id` (from auth)
- `team_id` (from auth)
- `role` (for Founder Rights override)

**Must pass these through service layer!**

### 4. Lazy Imports Required
Heavy dependencies that cause circular imports:
- `chat_memory` (get_memory)
- `chat_enhancements` (all classes)
- `ane_context_engine`
- `metal4_engine`
- `adaptive_router`
- `learning_system`
- `permission_engine`

### 5. Thread Safety
The memory layer uses thread-local connections and write locks.
**Do not modify chat_memory.py - it's already optimized!**

### 6. Metal 4 GPU Operations
The send_message function uses parallel GPU operations for RAG:
```python
results_tensor = await asyncio.gather(
    metal4_engine.parallel_search(...),
    metal4_engine.batch_embed(...)
)
```
**Preserve all asyncio.gather and Metal 4 calls!**

---

## File Structure After Migration

```
apps/backend/api/
├── schemas/
│   ├── chat_models.py          # 11 models (~150 lines)
│   ├── permission_models.py    # Existing
│   ├── team_models.py          # Existing
│   └── user_models.py          # Existing
├── services/
│   ├── chat.py                 # Business logic (~1,800 lines)
│   ├── permissions.py          # Existing
│   ├── team.py                 # Existing
│   └── users.py                # Existing
├── routes/
│   ├── chat.py                 # Thin router (~1,200 lines)
│   ├── permissions.py          # Existing
│   ├── team.py                 # Existing
│   └── users.py                # Existing
├── chat_memory.py              # KEEP AS-IS (storage layer)
├── chat_enhancements.py        # KEEP AS-IS (utilities)
└── main.py                     # Update router registration
```

---

## Estimated Effort

| Phase | Estimated Time | Complexity |
|-------|---------------|------------|
| Extract Models | 30 min | LOW |
| Create Service Layer | 2-3 hours | HIGH |
| Create Thin Router | 2-3 hours | HIGH |
| Update Registration | 10 min | LOW |
| Testing | 30-60 min | MEDIUM |
| **Total** | **6-8 hours** | **HIGH** |

---

## Success Criteria

- ✅ All 11 models extracted to schemas
- ✅ All 57 service functions created with lazy imports
- ✅ All 48 endpoints migrated to thin router
- ✅ Streaming response works for send_message
- ✅ Public endpoints accessible without auth
- ✅ Team filtering preserved throughout
- ✅ Server starts without errors
- ✅ All endpoints respond correctly
- ✅ Operation IDs follow chat_* pattern
- ✅ Tags use "chat" and "chat-public"

---

## Benefits of Migration

1. **Circular Dependencies Broken:** Lazy imports eliminate import cycles
2. **Code Organization:** Clear separation of concerns
3. **Testability:** Service functions easier to unit test
4. **Maintainability:** Thin routers easier to understand
5. **Consistency:** Follows same pattern as other 4 routers
6. **Documentation:** Better OpenAPI docs with consistent naming

---

## Next Session Checklist

1. [ ] Read this migration plan
2. [ ] Create api/schemas/chat_models.py (11 models)
3. [ ] Create api/services/chat.py (57 functions, ~1,800 lines)
4. [ ] Create api/routes/chat.py (48 endpoints, ~1,200 lines)
5. [ ] Update main.py router registration
6. [ ] Test streaming endpoint
7. [ ] Test public endpoints
8. [ ] Test team filtering
9. [ ] Commit and push
10. [ ] Update ROUTER_MIGRATION_STATUS.md to 5/5 complete! 🎉

---

*Last Updated: 2025-11-12*
*Status: Ready to Execute*
*Router Migration Progress: 4/5 (80%) → Final migration remaining*
