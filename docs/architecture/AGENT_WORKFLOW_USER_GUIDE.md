# Agent & Workflow System – Product Guide

**Audience:** Power users, team leads, and developers using or extending ElohimOS.  
**Scope:** How the Agent Orchestrator, Workflows, Agent Sessions, Templates, Analytics, and multi‑tenant visibility fit together in practice.

---

## 1. What This System Does

ElohimOS combines an AI Agent Orchestrator with a flexible Workflow engine so you can:

- Turn messy, multi‑step development tasks into repeatable workflows.
- Let the agent propose plans and patches at specific workflow stages.
- Keep agent context alive across multiple steps via sessions.
- Run everything in a multi‑user, team‑aware environment with clear boundaries.

The goal is **assistive automation**:

- The agent suggests; humans remain in control.
- Automation is explicit, observable, and reversible.
- Permissions and tenant boundaries are enforced at every layer.

---

## 2. Key Concepts & Glossary

### 2.1 Agent Orchestrator

The Agent Orchestrator is the backend layer that:

- Chooses engines/models based on intent and learning history.
- Builds context bundles (file tree slices, git diffs, chat snippets).
- Generates plans (`/api/v1/agent/plan`) and applies patches (`/api/v1/agent/apply`).
- Tracks what works for each user via the Learning System.

Main endpoints:

- `POST /api/v1/agent/route` – classify intent & suggest model.
- `POST /api/v1/agent/plan` – generate a multi‑step plan.
- `POST /api/v1/agent/context` – build a context bundle for a repo.
- `POST /api/v1/agent/apply` – apply a plan/patch via tools like Aider/Continue/Codex.
- `POST /api/v1/agent/sessions` – create a persistent session (see below).

### 2.2 Agent Session

An **AgentSession** is a stateful context for the agent, tied to:

- A user (`user_id`)
- A repository root (`repo_root`)
- An optional work item (`attached_work_item_id`)
- The latest plan (`current_plan`)

Sessions let the agent remember:

- What repo you’re working in.
- The current plan across multiple route/plan/apply calls.

Properties:

- **Strictly per‑user**: sessions cannot be shared across users.
- **Optional**: agent endpoints still work without a session; they just become stateless.

### 2.3 Workflow

Workflows model multi‑step business processes around development work. A workflow:

- Has stages (e.g. “Triage”, “Implement”, “Review”, “Deploy”).
- Owns multiple work items (tasks/tickets).
- Can include **Agent Assist stages** where the agent proposes work.

Visibility:

- `personal` – only the owner user can see.
- `team` – visible to all members of the owner team.
- `global` – visible to everyone (usually system templates).

### 2.4 Work Item

A **WorkItem** is an instance of work flowing through a workflow:

- Belongs to exactly one workflow.
- Moves between stages over time.
- Can carry arbitrary metadata in `data`, including:
  - `agent_recommendation` (Agent Assist output).
  - `agent_recommendation_error`.
  - `agent_auto_apply_result`.
  - `agent_event` (events from agent.apply).

Work item visibility is inherited from its workflow:

- If you can’t see the workflow, you can’t see its items.

### 2.5 Stage Types (Including AGENT_ASSIST)

Stages define what’s expected at each step. Important stage types:

- `HUMAN` – manual work by a person.
- `AUTOMATION` – automatic actions by the system.
- `AGENT_ASSIST` – a special stage where the agent proposes a plan or patch.

For `AGENT_ASSIST` stages, additional fields on the stage:

- `agent_prompt` – prompt/description sent to the agent.
- `agent_target_path` – repo path the agent should focus on.
- `agent_model_hint` – optional preferred model.
- `agent_auto_apply` – if `true`, stage is allowed to auto‑apply agent changes (opt‑in, guarded).

### 2.6 Workflow Templates

Templates are reusable workflow blueprints:

- Marked with `is_template = true`.
- Can be:
  - `personal` – only you see and instantiate.
  - `team` – shared within your team.
  - `global` – shipped as system templates for everyone.

Instantiating a template:

- Creates a new workflow with `is_template = false`.
- Copies stages, triggers, and configuration.
- Sets ownership and visibility for the new workflow (typically to the current user/team).

### 2.7 Workflow Analytics

Analytics summarize how work flows through a workflow:

- Overall:
  - Total items.
  - Completed vs in‑progress.
  - Average cycle time.
- Per stage:
  - How many items enter/exit.
  - Average time spent in each stage.

Analytics respect visibility:

- You can only see analytics for workflows you’re allowed to see.

### 2.8 Visibility: Personal, Team, Global

Visibility applies to workflows and templates:

- **Personal**
  - Only the owner user can see and use it.
  - Ideal for experiments or private automation.
- **Team**
  - Visible to all members of the owner team.
  - Default for most collaborative workflows.
- **Global**
  - Visible to everyone with workflows permissions.
  - Usually reserved for system templates maintained by admins.

Agent sessions are **always personal**.

---

## 3. How It Fits Together (High‑Level Flow)

At a high level:

1. A user or team defines a **workflow** (often from a **template**).
2. Work arrives as **work items** that move through stages.
3. At an `AGENT_ASSIST` stage:
   - The **Agent Orchestrator** fetches repo context.
   - The agent generates a plan and recommended steps.
   - Recommendations are stored on the work item.
   - Optionally, auto‑apply runs (if configured and allowed).
4. Users review and act on agent suggestions:
   - Accept/reject/modify patches.
   - Move items to next stages.
5. Over time, **Analytics** track how the workflow performs.
6. Separately, **Agent Sessions** keep the agent “in context” when you interact via the agent UI (chat/code assist), so multiple `/route|plan|apply` operations share state.

Everything is wrapped in:

- RBAC (permissions).
- Multi‑tenant scoping (personal/team/global).
- Audit logs and metrics.

---

## 4. Typical User Flows

### 4.1 Create an Agent‑Enabled Team Workflow from a Template

**Goal:** Quickly stand up a team workflow that uses Agent Assist.

Steps (frontend):

1. Open the automation/workflow area.
2. Go to the **Templates** view.
3. Browse templates:
   - Look for templates with:
     - An `AGENT_ASSIST` stage (often marked in the UI).
     - `visibility = team` or `global` (you must be allowed to see them).
4. Click **Instantiate** on a template:
   - Choose a name for your new workflow.
   - Optionally edit the description.
5. Navigate to the new workflow’s **Designer**:
   - Confirm:
     - Stages imported correctly.
     - There is an `AGENT_ASSIST` stage where you want the agent involved.
   - Adjust stage order or labels as needed.
6. Save and start using the workflow:
   - New work items will now flow through it.
   - When items reach the Agent Assist stage, the agent will run.

Multi‑tenant behavior:

- If you create the workflow as a team workflow (`visibility=team`), your team can see and use it.
- Users outside the team cannot see or instantiate it.

### 4.2 Use Agent Assist on a Work Item

**Goal:** Let the agent propose changes, but keep human review in the loop.

Steps:

1. Open a **work item** that has reached an `AGENT_ASSIST` stage.
2. In the Work Item view:
   - Look for the **Agent Assist panel**.
   - If the agent has already run:
     - You’ll see:
       - A plan summary.
       - Steps with descriptions, risk levels, and time estimates.
       - Any identified risks.
     - If there was an error, you’ll see an error message instead.
3. Review the recommendation:
   - Check risk badges (low/medium/high).
   - Read the plan summary.
   - Decide whether it aligns with your goals.
4. Take action:
   - If stage is advisory‑only:
     - Use the suggested plan as guidance.
     - Manually apply changes in your editor or via agent tools.
   - If `agent_auto_apply` is enabled:
     - The system may already have applied a patch.
     - Check the **Auto‑Apply Result** section for:
       - Success/failure.
       - Files changed.
       - Any errors.
5. Move the work item forward:
   - After review, transition to the next stage per your workflow rules.

Safety:

- Auto‑apply is **opt‑in** per stage and typically guarded via permissions.
- All recommendations and auto‑apply actions are recorded on the work item.

### 4.3 Work with Agent Sessions in the Agent UI

**Goal:** Keep the agent “in context” as you iterate on code or workflows.

Steps:

1. Open the **Agent** tab/panel in the frontend (e.g. in the code sidebar).
2. In the **Agent Sessions** panel:
   - Create a new session:
     - Choose `repo_root` (the project you’re working on).
     - Optionally link a `work_item_id`.
   - The new session becomes active.
3. Use the agent:
   - When you run `/agent/route`, `/plan`, `/context`, `/apply` via the UI:
     - The active `session_id` is passed to the backend.
     - The backend:
       - Verifies the session belongs to you.
       - Updates `last_activity_at` and `current_plan`.
4. Manage sessions:
   - View a list of active and closed sessions.
   - Select which session is active.
   - Close sessions you no longer need.

Security:

- Sessions are strictly per‑user.
- The backend rejects any attempt to use another user’s session, even if a malicious client passes a foreign `session_id`.

### 4.4 Review Workflow Analytics

**Goal:** Understand how a workflow performs over time.

Steps:

1. Open a workflow’s **Designer** or detail view.
2. Switch to the **Analytics** tab.
3. Review:
   - Overall metrics:
     - Total items, completed, in progress.
     - Average cycle time.
   - Per‑stage metrics:
     - How many items enter each stage.
     - How many complete each stage.
     - Average time spent in each stage.
4. Use insights to:
   - Identify bottlenecks (stages with long times or many stuck items).
   - Adjust stages, SLAs, or automation hooks.

Visibility:

- Only available if you can see the workflow itself.
- No cross‑tenant analytics leakage.

---

## 5. Multi‑Tenant Behavior in Plain English

### 5.1 Workflows & Templates

- **Personal workflows**:
  - Only visible to the creator.
  - Best for personal automation and experiments.
- **Team workflows**:
  - Visible to everyone on the same team.
  - Ideal for shared processes, e.g. “Team Code Review Workflow”.
- **Global workflows/templates**:
  - Visible to everyone with workflow permissions.
  - Typically created and maintained by admins.

Templates follow the same rules:

- Personal templates → only you see them.
- Team templates → team‑wide.
- Global templates → everyone can use them as starting points.

### 5.2 Work Items

- Work items inherit visibility from their workflow:
  - If you can see the workflow, you can see its items.
  - If not, you get a 404.

### 5.3 Agent Sessions

- Always **personal**:
  - Tied to `user_id`.
  - Only the owner can list, fetch, or close them.
  - Agent endpoints validate that `session_id` belongs to the current user; otherwise they return an error.

### 5.4 Admin / Support Behavior

Admins and support roles:

- Use special admin/support endpoints (e.g. `/api/v1/admin/*`, `admin_support` services).
- Can view more global metadata (users, workflows, device metrics).
- Do **not** get unrestricted access to encrypted or sensitive data:
  - Founder Rights model ensures they can help without seeing private content.

All admin/support actions are:

- Authenticated.
- Protected by permissions.
- Logged via `audit_logger`.

---

## 6. Safety, Permissions, and Auditability

### 6.1 Permissions Model (High‑Level)

The system uses a centralized RBAC layer with:

- Permission levels (NONE, READ, WRITE, ADMIN).
- Decorators like `@require_perm("code.use")`, `@require_perm("code.edit")`, `@require_perm("workflows.manage")`, etc.
- Team‑aware checks via `@require_perm_team` where needed.

Key points:

- You need `code.use` to call most agent routes.
- You need `code.edit` or equivalent to allow the agent to apply changes.
- You need workflow‑related permissions to create/manage workflows and templates.

### 6.2 Auto‑Apply Guardrails

Auto‑apply (agent automatically applying patches):

- Is **off** by default.
- Must be explicitly enabled on a stage (`agent_auto_apply = true`).
- Is typically restricted to users with stronger permissions (e.g. `code.edit`).
- Logs all actions:
  - Which user/workflow/stage triggered it.
  - Files changed.
  - Success/failure and error details.

### 6.3 Audit Logs

Key events are recorded via `audit_logger`, including:

- Agent sessions created/closed.
- Agent route/plan/context/apply calls.
- Agent Assist started/completed/failed.
- Workflow triggers firing on agent events.
- Admin/support operations.

Audit logs let you:

- Reconstruct who did what and when.
- Investigate issues or unexpected changes.

### 6.4 Metrics

Metrics provide high‑level health signals:

- Counts and latencies for:
  - Agent route/plan/context/apply.
  - Agent Assist runs and auto‑apply attempts.
  - Workflow trigger firings.
  - Session creation/closure.

They’re mainly for ops and performance tuning, not end‑user features.

---

## 7. Architecture Overview for Developers

### 7.1 Key Backend Modules

- **Agent Orchestrator (`apps/backend/api/agent/`)**
  - `orchestrator.py` – FastAPI router for `/api/v1/agent/*`.
  - `orchestration/models.py` – Pydantic models (Route/Plan/Context/Apply, AgentSession).
  - `orchestration/routing.py` – intent routing + learning‑aware model hints.
  - `orchestration/planning.py` – plan generation logic.
  - `orchestration/context_bundle.py` – builds context bundles.
  - `orchestration/apply.py` – applies plans via external tools.
  - `orchestration/sessions.py` – AgentSession service.
  - `orchestration/session_storage.py` – SQLite storage for sessions.

- **Learning System (`apps/backend/api/learning/`)**
  - Tracks successes/failures, preferences, styles, and project context.
  - Feeds into routing/model selection.

- **Workflows (`apps/backend/api/workflow_*`)**
  - `workflow_models.py` – Workflow, Stage, WorkItem, triggers.
  - `workflow_storage.py` – persistence + visibility‑aware queries.
  - `services/workflow_orchestrator.py` – state machine for workflows/items.
  - `workflow_service.py` – HTTP layer for workflows/templates/analytics.
  - `services/workflow_agent_integration.py` – Agent Assist integration.
  - `services/workflow_triggers.py` – event‑based triggers (e.g. agent.apply.success).
  - `services/workflow_analytics.py` – analytics aggregations.

- **Permissions (`apps/backend/api/permissions/*`)**
  - Core RBAC engine and decorators.

### 7.2 Data Flow Examples

- **Agent Assist run:**
  1. WorkItem transitions into `AGENT_ASSIST` stage.
  2. `WorkflowOrchestrator` calls `run_agent_assist_for_stage`.
  3. `context_bundle` builds repo context.
  4. `planning` generates plan.
  5. WorkItem `data.agent_recommendation` is updated and stored.
  6. Optionally, auto‑apply runs via `apply` and results are stored.

- **Agent apply event → workflow trigger:**
  1. `/agent/apply` succeeds.
  2. Agent orchestrator emits an internal event (e.g. `agent.apply.success`).
  3. `workflow_triggers.handle_agent_event` finds workflows with matching triggers.
  4. New WorkItems are created in those workflows, with `data.agent_event` set.

---

## 8. Extending the System

### 8.1 Adding New Stage Types

To add a new stage type:

1. Extend `StageType` enum in `workflow_models.py`.
2. Update `Stage` and relevant orchestrator logic.
3. Add UI handling (labels, behavior) in the frontend.
4. Add tests for:
   - Creation.
   - Transitions.
   - Visibility and analytics where relevant.

### 8.2 Adding New Agent Engines

To integrate a new engine/tool:

1. Extend capabilities detection in `agent/orchestration/capabilities.py`.
2. Add engine‑specific apply logic in `orchestration/apply.py`.
3. Update routing/model selection to consider the new engine.
4. Add tests to ensure:
   - Engine detection works.
   - Routing picks new engine when appropriate.

### 8.3 New Templates and Playbooks

You can add:

- New workflow templates tuned for:
  - Incident response.
  - Data migrations.
  - Large refactors.
- Documentation and in‑app hints that link to those templates.

Always:

- Choose appropriate visibility (personal/team/global).
- Consider including Agent Assist stages where the agent adds the most value.

---

## 9. Testing & Validation

### 9.1 E2E Smoke Tests

The complete Agent + Workflow integration is validated by comprehensive end-to-end smoke tests:

**Test Suite:** `apps/backend/tests/test_e2e_agent_workflow_smoke.py`

**Coverage:** 7 realistic scenarios that exercise the full stack:

1. **Template instantiation** - Global templates → team workflows
2. **Agent Assist flow** - Work items through AGENT_ASSIST stages with recommendations
3. **Auto-apply** - Automatic patch application when enabled
4. **Workflow triggers** - Agent events creating work items in listening workflows
5. **Multi-workflow triggers** - Single event triggering multiple workflows
6. **Personal workflow privacy** - Isolation between users

**Running E2E tests:**
```bash
# From repo root
cd apps/backend
ELOHIM_ENV=development PYTHONPATH="../packages:.:$PYTHONPATH" \
  ../venv/bin/python3 -m pytest tests/test_e2e_agent_workflow_smoke.py -v
```

These tests validate:
- Workflow orchestration (stage transitions, work item lifecycle)
- Agent integration (planning, auto-apply, error handling)
- Event triggers (agent.apply.success → workflow creation)
- Multi-tenancy (personal/team/global visibility isolation)
- Storage persistence and retrieval
- Graceful degradation (agent failures don't break workflows)

**CI Integration:** E2E tests run automatically in CI as part of backend checks (~1.3 seconds runtime).

For more details, see `docs/CI_SETUP.md`.

---

## 10. Summary

The Agent & Workflow system in ElohimOS gives you:

- A safe, observable way to bring AI into real development workflows.
- Strong multi‑tenant boundaries (personal/team/global).
- Rich tooling:
  - Agent Sessions.
  - Agent Assist stages.
  - Workflow templates.
  - Analytics.
  - Logs and metrics.

Humans stay in control; the agent provides context‑aware assistance at the right moments, while the platform ensures security, isolation, and traceability.

