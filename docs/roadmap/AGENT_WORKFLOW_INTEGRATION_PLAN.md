# Agent Orchestrator & Workflow Integration Roadmap

**Created:** 2025-11-19
**Updated:** 2025-11-19
**Status:** All Phases (A–E) implemented and tested ✅  
**Scope:** Backend services + API + minimal frontend hooks  
**Owner:** User / Claude / Codex  

---

## 0. Objectives & Constraints

### Objectives

- Turn the existing Agent Orchestrator and Workflow engine into a **cohesive, intelligent automation layer** for ElohimOS.
- Keep the system **safe, explainable, and debuggable**:
  - No silent auto‑changes without audit trails.
  - All agent actions traceable to user intents and workflows.
- Build on the newly modular architecture (services, orchestrations, learning system, core packages).

### Non‑Negotiable Constraints

- **No API breaks**:
  - Existing `/api/v1/agent/*` and `/api/v1/workflow/*` endpoints must remain compatible (request/response shapes, auth).
- **RBAC intact**:
  - All `@require_perm` and `@require_perm_team` checks must remain, especially around `code.use`, `code.edit`, `settings.update`, `workflows.*`.
- **No data corruption**:
  - Learning DB (`learning.db`), workflows DB (`workflows.db`), and code/workspace data must be preserved.
- **“Dumb core always works” principle**:
  - Core engines (`pulsar_core`, `neutron_core`, workflow orchestrator, learning system) must remain stable; we build on top via services/orchestration.
- **Observability**:
  - Every new automated behavior must leave a trail in:
    - Audit logs (where appropriate).
    - Workflow stage history.
    - Agent session records (in later phases).

---

## 1. High‑Level Phases

This roadmap continues where `MODULAR_REFACTORING_PLAN.md` ends. Phases are designed to be incremental and shippable.

1. **Phase A – Learning‑Aware Agent Routing (Backend only)**
   - Make `/agent/route` and planning/model selection aware of the learning system.
   - Output: smarter `model_hint` and engine ordering, *advisory* only.
2. **Phase B – Agent Assist Workflow Stage**
   - Introduce `StageType.AGENT_ASSIST` and have workflows invoke the agent for suggestions when work enters certain stages.
3. **Phase C – Agent Sessions (Stateful Agent Workspace)**
   - First‑class `AgentSession` entity tied to user + repo + (optional) workflow item.
4. **Phase D – Workflow Enhancements**
   - Triggers (agent events, file patterns), templates, and richer analytics.
5. **Phase E – Deep Agent ↔ Workflow Loop**
   - Tight integration: agent creates WorkItems, workflows enqueue agent tasks, closing the loop.

Phases are independent enough to be implemented gradually.

**Current implementation status (2025-11-19):**

- Phase A – Learning‑Aware Agent Routing: ✅ Implemented and covered by `test_agent_routing_learning.py`.
- Phase B – Agent Assist Workflow Stage: ✅ Implemented and covered by `test_workflow_agent_assist.py`.
- Phase C – Agent Sessions (Stateful Agent Workspace): ✅ Implemented and covered by `test_agent_sessions.py`.
- Phase D – Workflow Enhancements (Triggers, Templates, Analytics): ✅ Implemented and covered by `test_workflow_triggers.py`, `test_workflow_templates.py`, `test_workflow_analytics.py`.
- Phase E – Deep Agent ↔ Workflow Loop: ✅ Implemented and covered by `test_agent_workflow_integration.py`.

**All phases (A–E) are now complete and production-ready.**

---

## 2. Current Architecture Baseline

### Agent Orchestrator (Backend)

- **Package:** `apps/backend/api/agent/`
  - `orchestrator.py` – FastAPI router (`/api/v1/agent`).
  - `__init__.py` – exports `router`.
  - `orchestration/` package:
    - `models.py` – Route/Plan/Context/Apply models; capabilities models.
    - `config.py` – `load_agent_config()`, `get_agent_config()`, YAML persistence.
    - `capabilities.py` – Engine detection (Aider, Continue, Codex, Ollama).
    - `model_settings.py` – orchestrator config, validation, auto‑fix.
    - `routing.py` – `route_input_logic()` (intent classifier integration).
    - `planning.py` – `generate_plan_logic()` (EnhancedPlanner).
    - `context_bundle.py` – `build_context_bundle()` (repo tree, git context, chat snippets).
    - `apply.py` – `apply_plan_logic()` (Aider/Continue/Codex + PatchBus).

### Learning System

- **Package:** `apps/backend/api/learning/`
  - `system.py` – `LearningSystem` orchestrator.
  - `models.py` – `UserPreference`, `CodingStyle`, `ProjectContext`, `Recommendation`.
  - `storage.py`, `success.py`, `preferences.py`, `style.py`, `context.py`, `recommendations.py`, `patterns.py`.
- **Shim:** `apps/backend/api/learning_system.py` – re‑exports from `api.learning`.
- Consumers:
  - `adaptive_router.py`, `jarvis_adaptive_router.py`, `agent/adaptive_router.py`.
  - `services/chat/core.py`, `services/chat/system.py`.

### Workflow Engine

- **Models:** `apps/backend/api/workflow_models.py`.
- **Orchestrator:** `apps/backend/api/services/workflow_orchestrator.py` (+ shim `workflow_orchestrator.py`).
- **Storage:** `apps/backend/api/workflow_storage.py`.
- **Service/Routes:** `apps/backend/api/workflow_service.py`.
- **P2P Sync:** `apps/backend/api/workflow_p2p_sync.py`.

The architecture is already modular and tested; extensions will plug into these seams.

---

## 3. Phase A – Learning‑Aware Agent Routing (Detailed Plan)

**Goal:** Make `/agent/route` and model selection smarter by leveraging `LearningSystem` success history and preferences, without changing HTTP contracts or adding new routes.

### A.1 Behaviors to Implement

1. **Tool/engine recommendations based on success rate**
   - For a given `command` (user input to `/agent/route`):
     - Query success rates for tools like `"aider"`, `"continue"`, `"assistant"`, `"system"`, `"p2p"`, etc.
     - Choose a recommended engine (tool) if its success rate is above a certain threshold (e.g., > 0.7).
   - Use this to:
     - Influence `model_hint` in `RouteResponse`.
     - Optionally, suggest an `engine_order` for `/agent/apply`.

2. **Model hints based on preferences**
   - Use user preferences from `LearningSystem.get_preferences('tool')` and `'workflow'`:
     - If user tends to prefer `"aider"` for code tasks, bias `model_hint` toward the Aider‑friendly model.
     - If user tends to run tests first (`'testing_focused'`), potentially nudge planning behavior later (Phase A can just surface hints).

3. **Per‑user learning**
   - When `/agent/route` and `/agent/plan` run, they should:
     - Call `LearningSystem` for the **current user**, not globally.
   - This means:
     - The orchestrator needs `user_id` from `current_user`.
     - LearningSystem DB path can remain shared per app instance; user_id is just used inside the learning queries.

### A.2 Data Flow (Conceptual)

1. User calls `/agent/route` with `input="Refactor this function"`:

   - `orchestrator.py` → `route_input_logic(text, user_id?)`.
   - `route_input_logic`:
     - Uses `IntentClassifier` to get intent + base tool suggestion.
     - Calls `LearningSystem.get_success_rate(command=text, tool=<candidate_tool>)` for each supported tool.
     - Uses success rates + preferences to pick a recommended engine and `model_hint`.
   - Returns `RouteResponse` with:
     - `intent`, `confidence` (as before).
     - `model_hint` updated based on learning.
     - Possibly a new field in the future (e.g. `engine_hint`), but for Phase A we can stay within current schema by encoding this in `model_hint` and logs.

2. Later, `/agent/apply` can (optionally) read the same learning info (out of scope for Phase A but design should allow it).

### A.3 Implementation Steps

#### Step 1: Add LearningSystem dependency in routing layer

- **File:** `apps/backend/api/agent/orchestration/routing.py`

1. Import LearningSystem via shim pattern:

   ```python
   try:
       from api.learning_system import LearningSystem
   except ImportError:
       from learning_system import LearningSystem
   ```

2. Decide on how to manage the LearningSystem instance:
   - Option A (simple): Create a new instance per call with default DB path.
   - Option B (better): Use a module‑level singleton (like `get_learning_system()` with lazy init).
   - Given your tests and import patterns, Option B is preferable:

   ```python
   _learning_system = None

   def get_learning_system() -> LearningSystem:
       global _learning_system
       if _learning_system is None:
           _learning_system = LearningSystem()
       return _learning_system
   ```

3. Update `route_input_logic` signature to accept `user_id: str | None = None` (internal only – HTTP signature stays unchanged at `/agent/route`):

   ```python
   def route_input_logic(text: str, user_id: Optional[str] = None) -> RouteResponse:
       ...
   ```

#### Step 2: Query learning system for tool success and preferences

1. Define candidate tools (as strings) inside `routing.py`:

   ```python
   CANDIDATE_TOOLS = ["aider", "continue", "assistant", "system"]
   ```

2. After calling `IntentClassifier` and deriving initial intent and base model_hint:

   - Get the learning system:

     ```python
     learning = get_learning_system()
     ```

   - For each tool in `CANDIDATE_TOOLS`:

     ```python
     rates = {}
     for tool in CANDIDATE_TOOLS:
         try:
             rate = learning.get_success_rate(text, tool)
         except Exception:
             rate = 0.5  # Default if unknown or error
         rates[tool] = rate
     ```

   - Choose the best tool:

     ```python
     best_tool = max(rates.items(), key=lambda kv: kv[1])[0]
     best_rate = rates[best_tool]
     ```

   - If `best_rate` exceeds a threshold (e.g. 0.7), treat this as a strong recommendation.

3. Incorporate preferences:

   - Call `learning.get_preferences("tool")` to see if user has a strong preference.
   - If a top `UserPreference` in that category has high confidence and matches a candidate tool, you can factor that into `best_tool`.

4. Use the final `best_tool` to refine `model_hint`:

   - Map tools → models based on `AGENT_CONFIG["models"]`.
   - Example mapping:
     - `"aider"` → `cfg["models"]["coder"]`
     - `"assistant"` → `cfg["models"]["planner"]` or a chat model.
   - Update `model_hint` accordingly.

#### Step 3: Pass user_id from orchestrator to routing logic

- **File:** `apps/backend/api/agent/orchestrator.py`

1. In `/route` endpoint:

   ```python
   @router.post("/route", response_model=RouteResponse)
   @require_perm("code.use")
   async def route_input(request: Request, body: RouteRequest, current_user: Dict = Depends(get_current_user)):
       ...
       user_id = current_user.get("user_id")
       resp = route_input_logic(body.input, user_id=user_id)
       ...
       return resp
   ```

2. No change to HTTP schema; just pass extra context to the internal logic.

#### Step 4: Audit & logging

1. Enhance existing audit/log entries in `/route` to include learning decisions:

   - Log:
     - `best_tool`, `best_rate`, `rates` dict (maybe truncated or rounded).
     - `model_hint` chosen.
   - This will help debug or tune thresholds later.

2. Do not change existing `AuditAction` names; just enrich `details`.

#### Step 5: Tests

1. Add/tests under `apps/backend/tests`:

   - `test_agent_routing_learning.py` (or extend existing agent tests if present).

2. Tests to cover:

   - When no history exists:
     - `route_input_logic` returns some `model_hint` but does not crash.
   - When success history favors a tool:
     - After calling `learning.track_execution` several times for a given `command` + `tool`, then calling `route_input_logic`, ensure:
       - `model_hint` reflects that tool’s model.
   - Make tests use an in‑memory or temp learning DB to avoid polluting production.

3. Run:

   ```bash
   ./tools/run_dev_checks.sh
   ```

   - Ensure import validation and tests pass.

---

## 4. Phase B – Agent Assist Workflow Stage (Detailed Plan)

**Goal:** Enable workflows to delegate specific stages to the Agent Orchestrator for suggestions (plans/patches) while keeping humans in control of final actions.

### B.1 New Concepts & Models

1. **New Stage Type**
   - Extend `StageType` enum in `workflow_models.py`:
     - Add: `AGENT_ASSIST = "agent_assist"`.
   - This indicates a stage where the primary “work” is agent‑driven assistance (code suggestions, doc changes, remediation steps).

2. **Agent Stage Configuration**
   - Extend `Stage` model with optional agent configuration fields:
     - `agent_prompt: Optional[str] = None` – prompt template or description of what the agent should do at this stage.
     - `agent_target_path: Optional[str] = None` – repo path (relative to workspace_root) where the agent should focus.
     - `agent_model_hint: Optional[str] = None` – override/augment the agent’s model selection.
   - These fields should be **optional** and only meaningful when `stage_type == StageType.AGENT_ASSIST`.

3. **Work Item Data Extension**
   - Plan a reserved key in `WorkItem.data` for agent outputs:
     - e.g. `data["agent_recommendation"]`:
       - Contains:
         - `plan_summary` – text summary of agent’s plan.
         - `patch_preview` – unified diff as text.
         - `engine_used` – aider/continue/codex.
         - `model_used` – actual model string.

### B.2 Engine Behavior

1. **On Transition Into AGENT_ASSIST Stage**
   - In `WorkflowOrchestrator._transition_to_stage`:
     - After updating `work_item` fields and recording `StageTransition`:
       - If `next_stage.stage_type == StageType.AGENT_ASSIST`:
         - Schedule an asynchronous “agent assist” task:
           - Either:
             - Fire a background task via asyncio.create_task (if using FastAPI’s lifespan for tasks), or
             - Push a job into a simple internal queue (phase B can start with `asyncio.create_task`).
         - The agent assist task will:
           - Build a context request for `/api/v1/agent/context`:
             - `repo_root` obtained from WorkItem data (e.g. `data["repo_root"]`) or a default path from settings.
           - Call `/agent/context` to gather file tree and recent diffs.
           - Call `/agent/plan` with:
             - `input` built from `agent_prompt` + WorkItem metadata.
             - Optionally pass a `context_bundle` from the previous call.
           - Optionally call `/agent/apply` with `dry_run=True` to generate a patch preview (no code changes yet).
           - Store results back into `WorkItem.data["agent_recommendation"]`.
           - Persist updated WorkItem via `WorkflowStorage.save_work_item`.

2. **No Automatic Apply in Phase B**
   - Agent Assist stages in Phase B are **non‑destructive**:
     - Agent produces suggestions and patch previews.
     - Human reviewers decide whether to apply those changes (manually or in Phase E).

### B.3 Service Layer Integration

1. **New Helper Module (Optional but Recommended)**
   - Add `apps/backend/api/services/workflow_agent_integration.py` with functions:
     - `async def run_agent_assist_for_stage(work_item: WorkItem, stage: Stage, user_id: str) -> None:`
       - Encapsulates logic to:
         - Build agent context/plan requests.
         - Call agent endpoints.
         - Update WorkItem data.
     - Orchestrator simply calls this helper in a background task.

2. **Error Handling**
   - Agent failures should not break workflow transitions:
     - If agent calls fail:
       - Log an error.
       - Set `data["agent_recommendation_error"]` with a short message.
       - Keep stage as PENDING/IN_PROGRESS; humans can still proceed.

### B.4 Frontend Considerations (Thin Hooks)

1. **WorkflowDesigner**
   - Add “Agent Assist” to stage type dropdown (using `StageType.AGENT_ASSIST`).
   - Show additional fields in the stage property panel:
     - Agent prompt (textarea).
     - Target path (text input).
     - Model hint (optional).

2. **Work Item UI**
   - In the Workflow/Work Item detail view:
     - If `agent_recommendation` is present:
       - Show:
         - Plan summary.
         - Patch preview (with scroll).
         - Engine/model used.
       - Provide buttons for:
         - “Mark as reviewed” (no apply yet).
         - In Phase E, maybe “Apply patch” / “Open in code workspace”.

### B.5 Acceptance Criteria (Phase B)

- A new `StageType.AGENT_ASSIST` exists and is persisted correctly.
- When a WorkItem enters an Agent Assist stage:
  - An agent assist task runs (or at least is triggered) without breaking the transition.
  - WorkItem data contains agent suggestion fields when agent calls succeed.
  - Failures are logged and captured without blocking the workflow.
- No automatic patch application occurs; behavior is advisory only.
- `./tools/run_dev_checks.sh` passes and any new tests for agent assist behavior pass.

---

## 5. Phase C – Agent Sessions (Stateful Agent Workspace)

**Goal:** Introduce explicit AgentSession entities that tie together user, workspace, and agent context, enabling multi‑step workflows and UX around “active agent sessions”.

### C.1 New Models & Storage

1. **AgentSession Model**
   - Add to `apps/backend/api/agent/orchestration/models.py` (or a new `sessions.py` within that package):

     ```python
     class AgentSession(BaseModel):
         id: str
         user_id: str
         repo_root: str
         created_at: datetime
         last_activity_at: datetime
         status: str  # e.g. "active", "completed", "archived"
         current_plan: Optional[Dict[str, Any]] = None
         attached_work_item_id: Optional[str] = None
     ```

2. **Session Storage**
   - New lightweight SQLite-backed storage module:
     - `apps/backend/api/agent/orchestration/session_storage.py` with functions:
       - `create_session(session: AgentSession) -> None`
       - `get_session(session_id: str) -> Optional[AgentSession]`
       - `update_session(session_id: str, updates: Dict[str, Any]) -> None`
       - `list_sessions_for_user(user_id: str) -> List[AgentSession]`
       - `archive_session(session_id: str) -> None`
   - DB file can be under the main app data dir (e.g. `agent_sessions.db`).

### C.2 Service Layer: Session Management

1. **Session Service**
   - Add `apps/backend/api/agent/orchestration/sessions.py`:
     - Encapsulate higher‑level operations:
       - Creating a session with default status and timestamps.
       - Attaching a workflow item (optional).
       - Updating current_plan after `/plan` runs.
       - Recording last_activity_at after context/apply calls.

2. **Thread Safety & Concurrency**
   - Use simple sqlite3 connections as in other services.
   - No complex locking needed; each request can open/close its own connection.

### C.3 Router Endpoints

1. **New HTTP Endpoints (in agent/orchestrator.py)**

   - `POST /api/v1/agent/sessions`
     - Request:
       - `repo_root` (required).
       - `attached_work_item_id` (optional).
     - Behavior:
       - Create `AgentSession` with generated `id` (e.g. `session_{uuid}`).
       - Status = "active".
       - Return the AgentSession.

   - `GET /api/v1/agent/sessions/{session_id}`
     - Return stored session including current_plan.

   - `GET /api/v1/agent/sessions`
     - List sessions for current user (with basic filters: active/completed).

   - Optional: `POST /api/v1/agent/sessions/{session_id}/close`
     - Mark session as "archived" or "completed".

2. **Permissions**
   - All session endpoints should require:
     - `@require_perm("code.use")`.
   - Sessions must be scoped to the authenticated user:
     - A user may not fetch sessions for another user.

### C.4 Agent Orchestration Integration

1. **Linking Sessions to /route, /plan, /context, /apply**

   - Extend existing endpoints to accept an optional `session_id` in their request models:
     - e.g., `RouteRequest`, `PlanRequest`, `ContextRequest`, `ApplyRequest`.
   - If `session_id` is provided:
     - Use `get_session(session_id)` to:
       - Override `repo_root`.
       - Attach `current_plan` updates after `/plan`.
       - Update `last_activity_at`.
   - If no `session_id` is provided:
     - Behavior remains unchanged from today.

2. **Audit & Learning**
   - Optionally record `session_id` in audit logs.
   - Over time, LearningSystem could factor session context into recommendations (future enhancement).

### C.5 Frontend Hooks

1. **Agent UI**
   - Session list/dropdown:
     - "New Session" button that calls `POST /agent/sessions`.
     - "Active Sessions" panel showing repo_root + status.
   - When an agent session is active:
     - All `/agent/...` calls include `session_id` in payload.

### C.6 Acceptance Criteria (Phase C)

- AgentSession model and storage implemented.
- `/api/v1/agent/sessions` endpoints exist and enforce per‑user isolation.
- `/agent/route|plan|context|apply` accept optional `session_id` and update session accordingly.
- Legacy behavior (no session_id) remains unchanged.
- Dev checks pass with any new tests for sessions.

---

## 6. Phase D – Workflow Enhancements (Triggers, Templates, Analytics)

**Goal:** Make workflows more powerful and user‑friendly with event‑based triggers, reusable templates, and richer analytics—all without breaking existing workflows.

### D.1 Triggers

1. **Extend WorkflowTriggerType**
   - In `workflow_models.py`, extend `WorkflowTriggerType` enum:
     - Existing types (e.g. `MANUAL`, `SCHEDULED`).
     - New types:
       - `ON_AGENT_EVENT` – triggered when an agent event occurs (e.g. plan/apply completes).
       - `ON_FILE_PATTERN` – triggered when files matching patterns appear in certain directories.
       - `ON_WEBHOOK` – optional, for external systems (future).

2. **Trigger Configuration**
   - Extend `WorkflowTrigger` model with fields:
     - `event_type: WorkflowTriggerType`.
     - `pattern: Optional[str]` – e.g. glob or regex for file paths.
     - `agent_event_type: Optional[str]` – e.g. "agent.apply.success".

3. **Trigger Evaluation Service**
   - Add `apps/backend/api/services/workflow_triggers.py`:
     - Functions:
       - `handle_agent_event(event: Dict[str, Any])`:
         - Called by agent orchestrator when certain actions complete.
         - Finds workflows with `ON_AGENT_EVENT` triggers matching event type.
         - Creates WorkItems accordingly.
       - `handle_file_event(event: Dict[str, Any])`:
         - Called by file watcher or other systems in Phase D+.

4. **Agent Integration for Triggers**
   - In `agent/orchestration/apply.py`, after a successful apply:
     - Build a small event payload:
       - `{ "type": "agent.apply.success", "user_id": ..., "repo_root": ..., "files": [...] }`.
     - Call `workflow_triggers.handle_agent_event(event)` internally.

### D.2 Workflow Templates

1. **Template Flag**
   - Add field to `Workflow` model and DB schema:
     - `is_template: bool = False`.
   - In `workflow_storage.py`, ensure this field is persisted:
     - Add `is_template` column to `workflows` table (if not present).

2. **Template Endpoints**
   - In `workflow_service.py`:
     - `GET /workflow/templates` – list templates (non‑deleted, `is_template=True`).
     - `GET /workflow/templates/{id}` – get template definition.
     - `POST /workflow/templates/{id}/instantiate` – create a new, editable workflow from a template.

3. **Predefined Templates**
   - Seed a few base templates (via a migration script or manual import):
     - "Code Review Workflow"
     - "Bug Triage Workflow"
     - "Incident Response Workflow"
   - Include Agent Assist stages where appropriate.

### D.3 Analytics

1. **Enhanced Statistics**
   - Extend `WorkflowOrchestrator.get_workflow_statistics` to compute:
     - Per-stage counts (entered/completed).
     - Average time spent per stage.
     - SLA breach counts per stage.
   - Consider a separate `services/workflow_analytics.py` for more complex aggregations.

2. **New Endpoint (optional)**
   - `GET /workflow/analytics/{workflow_id}`:
     - Returns richer analytics separate from basic stats.

### D.4 Frontend Hooks

1. **Workflow Dashboard**
   - Provide:
     - Template selector when creating new workflows.
     - Simple charts/tables showing per-stage metrics.

2. **Trigger UI**
   - In WorkflowDesigner:
     - Allow users to select trigger types and configure patterns/events.

### D.5 Acceptance Criteria (Phase D)

- Trigger definitions implemented and integrated with agent events (at least `ON_AGENT_EVENT`).
- Template support present and at least one template usable end‑to‑end.
- Enhanced analytics available via API (even if frontend UI is minimal initially).
- Dev checks and new tests for triggers/templates/analytics pass.

---

## 7. Phase E – Deep Agent ↔ Workflow Loop

**Goal:** Close the loop between the Agent Orchestrator and Workflow engine so that:
- Agent outputs create and update WorkItems.
- Workflows can launch and guide agent actions.

### E.1 Agent → Workflow (Creating WorkItems from Agent Actions)

1. **Event Hook in Apply Logic**
   - In `agent/orchestration/apply.py`, after a successful patch application:
     - Build an event payload:

       ```python
       event = {
           "type": "agent.apply.success",
           "user_id": current_user["user_id"],
           "repo_root": body.repo_root,
           "files": apply_result.get("files", []),
           "patch_id": patch_id,
           "summary": proposal.description,
       }
       ```

   - Call a helper in `services/workflow_agent_integration.py`:
     - `create_work_item_for_agent_patch(event)`:
       - Find a configured "Code Review" or "Agent Patch Review" workflow:
         - Could be linked via settings or workflow trigger configuration.
       - Create a WorkItem with:
         - `data["agent_patch"] = event`.
         - Appropriate initial stage (e.g., "Review agent patch").

2. **Configuration**
   - Store configuration in app settings or workflow triggers:
     - e.g. `AGENT_PATCH_REVIEW_WORKFLOW_ID` in settings table.

### E.2 Workflow → Agent (Work Stages Launch Agent Tasks)

1. **Beyond Phase B Agent Assist**
   - Extend `StageType.AGENT_ASSIST` behavior to optionally auto‑apply patches:
     - Stage config can include:
       - `auto_apply: bool = False`.
   - If `auto_apply=True`:
     - After generating an agent plan/patch preview:
       - Optionally call `/agent/apply` with `dry_run=False` but still under appropriate `code.edit` permission checks and rate limits.

2. **Guardrails**
   - Auto‑apply must:
     - Respect existing `require_perm("code.edit")`.
     - Be opt‑in per stage.
     - Log all actions with full details (patch_id, files changed).

### E.3 Unified “Task View”

1. **Concept**
   - A conceptual "task" that may include:
     - A WorkItem (workflow context).
     - An AgentSession (agent context).
     - One or more patches (code context).

2. **Implementation (Later Phase)**
   - For now, keep the link via:
     - WorkItem.data["agent_session_id"] and AgentSession.attached_work_item_id.
   - Later, a dedicated "Task" entity could be introduced if needed.

### E.4 Acceptance Criteria (Phase E)

- Agent apply events create or update WorkItems in at least one configured workflow.
- Agent Assist stages can (optionally) auto‑apply patches safely when configured to do so.
- All actions are auditable:
  - Workflow history reflects agent‑driven transitions.
  - Audit logs capture who triggered what and via which stage/session.
- Dev checks and end‑to‑end tests (agent → workflow → agent) pass.

---

## 5. Acceptance Criteria for Phase A

- **Functional:**
  - `/api/v1/agent/route` returns the same schema as before.
  - `model_hint` is influenced by learning history when available.
  - The system behaves sensibly when there is no history (falls back to current behavior).
- **Technical:**
  - No new circular imports.
  - LearningSystem instance management does not introduce deadlocks (reuse the patterns you just fixed in `success.py`).
  - `./tools/run_dev_checks.sh` passes.
- **Operational:**
  - Logs clearly indicate how tool/model choices were made.
  - Behavior is safe: learning influence is advisory (no automatic destructive actions).
