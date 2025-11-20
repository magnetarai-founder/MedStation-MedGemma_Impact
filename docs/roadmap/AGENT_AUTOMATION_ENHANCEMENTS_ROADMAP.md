# Agent Engines & Automation Enhancements Roadmap

**Status:** Planning  
**Scope:** New agent engines, opinionated stage types, high‑quality global templates, and richer automation paths on top of the existing Agent ↔ Workflow system.  
**Audience:** You / future maintainers designing and implementing advanced automation features in ElohimOS.

This roadmap assumes the current foundation is in place:

- Modular backend services with Agent Orchestrator, Learning System, Workflows, Permissions, and Code Editor refactors complete.
- Frontend Agent Sessions, Templates, Analytics, and Agent Assist UI shipped.
- Multi‑tenant hardening (personal/team/global) enforced and surfaced in UI.
- CI + E2E smoke tests (Agent + Workflow) passing.

The phases below are ordered from **easiest / least complex** to **most complex**, with the intent that each phase is independently shippable and adds visible value.

---

## 0. Design Principles & Guardrails

Before diving into phases, these principles must remain true across all enhancements:

- **Assistive, not fully autonomous by default**
  - New engines and stage types default to **advisory** behavior.
  - Auto‑apply or destructive actions are always opt‑in and heavily gated.

- **Multi‑tenant safe**
  - All new features respect workflow visibility (personal/team/global).
  - No cross‑user or cross‑team data leakage in logs, analytics, or agent context.

- **RBAC consistent**
  - New endpoints or actions must honor existing permission patterns:
    - `code.use`, `code.edit`, `workflows.*`, `settings.update`, etc.
  - Admin/support features go through `admin_support` style patterns with audit logging.

- **Audited & observable**
  - Every automated engine action leaves:
    - Audit log entry (who/what/when).
    - WorkItem history entry (where relevant).
    - Metrics (counts, latencies, failures).

- **Composable**
  - New stage types, engines, and templates should be **Lego pieces**:
    - Simple primitives that can be used in many workflows.
    - No “magic” monolith flows that are hard to reuse or test.

---

## 1. Phase 1 – Opinionated Stage Types (No New Engines)

**Goal:** Introduce high‑signal stage types that reuse the existing Agent Assist plumbing, without adding new engine integrations yet.

These are “semantic wrappers” around the existing `AGENT_ASSIST` behavior. They give users clearer intent (“code review”, “test suggestion”, etc.) while internally reusing the same planning engine and context builder.

### 1.1 Stage Types to Introduce

Start with 2–3 of these:

1. `CODE_REVIEW`
   - Purpose: Pre‑review a diff or change set.
   - Agent prompt template:
     - “You are a code reviewer. Review the following changes for correctness, readability, and maintainability. Summarize key risks and suggested improvements.”
   - Uses:
     - Workflows around pull requests, pre‑merge checks.

2. `TEST_ENRICHMENT`
   - Purpose: Suggest or generate tests for a given change or bugfix.
   - Agent prompt template:
     - “You are a test engineer. Based on the following code and description, propose or generate test cases that validate behavior and edge cases.”
   - Uses:
     - Bug workflows, feature workflows, regression flows.

3. (Optional early) `DOC_UPDATE`
   - Purpose: Help update docs and release notes.
   - Agent prompt template:
     - “You are a documentation writer. Update or summarize the documentation to reflect these changes.”
   - Uses:
     - Release workflows, onboarding docs.

### 1.2 Backend Tasks

Files to touch (backend):

- `apps/backend/api/workflow_models.py`
  - Extend `StageType` enum with new values:
    - `StageType.CODE_REVIEW`
    - `StageType.TEST_ENRICHMENT`
    - (optional) `StageType.DOC_UPDATE`
  - No new persistence fields needed; reuse `agent_prompt`, `agent_target_path`, `agent_model_hint`, `agent_auto_apply`.

- `apps/backend/api/services/workflow_agent_integration.py`
  - When `stage.stage_type` is one of the new types:
    - If `stage.agent_prompt` is not set, supply a default prompt template based on type.
    - Optionally adjust `agent_target_path`:
      - `CODE_REVIEW`: use the diff or changed files (if available).
      - `TEST_ENRICHMENT`: focus on `tests/` and relevant source files.
      - `DOC_UPDATE`: focus on `docs/` or `README` files.

### 1.3 Frontend Tasks

Files to touch (frontend):

- `src/types/workflow.ts`
  - Extend `StageType` union to include new types.

- Stage configuration / designer UI:
  - Wherever stage type is selected (workflow designer):
    - Add labels:
      - “Code Review (Agent)”
      - “Test Enrichment (Agent)”
      - “Documentation Update (Agent)”
    - Add short descriptions when hovering or in a side panel.

- `AgentAssistPanel`:
  - When the stage is one of the new types:
    - Show a contextual header:
      - “Agent Code Review”
      - “Agent Test Suggestions”
      - “Agent Documentation Suggestions”
    - Optionally show an icon that matches type (e.g. clipboard, test beaker, doc icon).

### 1.4 Tests

Backend tests:

- New test file or class:
  - `test_workflow_stage_types.py` (or extend `test_workflow_agent_assist.py`).
  - Verify:
    - Default `agent_prompt` is applied based on stage type when not set.
    - `run_agent_assist_for_stage` produces a recommendation with expected fields.

Frontend tests (optional at this stage):

- Light unit tests or snapshot tests for:
  - Stage type labels and descriptions.
  - `AgentAssistPanel` header text given stage type.

Complexity: **Low** – new enums, prompt templates, and UI labels on top of existing behavior.

---

## 2. Phase 2 – High‑Quality Global Templates

**Goal:** Provide a curated library of **global** (system) templates that highlight the new stage types and give teams instant value.

Templates are where all of the earlier work (Sessions, Agent Assist, Analytics, visibility) start to shine for real users.

### 2.1 Template Candidates

Design 3–5 initial global templates:

1. **Standard Code Review Workflow**
   - Stages:
     - “Intake” (HUMAN) – create work item from PR or diff.
     - “Agent Code Review” (`CODE_REVIEW`) – agent suggests review notes.
     - “Reviewer Review” (HUMAN) – human reviewer makes final decision.
   - Triggers:
     - Optional: `ON_WEBHOOK` or placeholder for future PR integration.
   - Visibility:
     - `global`, `is_template=True`.

2. **Bug Fix + Test Workflow**
   - Stages:
     - “Bug Intake” (HUMAN).
     - “Agent Diagnosis” (`AGENT_ASSIST` with bug prompt).
     - “Agent Test Suggestions” (`TEST_ENRICHMENT`).
     - “Fix & Verify” (HUMAN).
   - Analytics:
     - Measures time from intake to verify.

3. **Security Review Workflow** (later phase when security engine exists)
   - Stages:
     - “Change Intake” (HUMAN).
     - “Security Scan” (SECURITY_REVIEW, see Phase 4).
     - “Human Security Review” (HUMAN).

4. **Release Notes & Docs Workflow**
   - Stages:
     - “Release Candidate” (HUMAN).
     - “Agent Release Notes Draft” (`DOC_UPDATE`).
     - “Docs Review & Publish” (HUMAN).

### 2.2 Implementation Steps

Backend:

- Use `workflow_storage` + `workflow_orchestrator` to seed global templates:
  - Add a small seeding script or migration:
    - Checks if templates already exist (idempotent).
    - Creates templates with:
      - `is_template=True`, `visibility="global"`, and meaningful names/descriptions.

Frontend:

- Templates list (`TemplatesList.tsx`):
  - Highlight system templates (global templates) with:
    - Special label: “System Template”.
    - Category tags (Code Review, Bug Workflow, Security, Release).
  - Optionally surface “Recommended” templates at the top for new users.

Docs:

- Update `AGENT_WORKFLOW_USER_GUIDE.md`:
  - Add a section “Recommended Templates” describing each global template and when to use it.

Tests:

- Backend:
  - Simple tests to verify seeded templates exist with correct fields.
  - E2E:
    - Extend existing smoke tests to instantiate at least one global template and run through a stage or two.

Complexity: **Low‑Medium** – design and seeding work; little new logic.

---

## 3. Phase 3 – New Engines: Test & Static Analysis Helpers

**Goal:** Introduce two “low‑risk” engines that are mostly wrappers around local tools and existing agent capabilities.

Focus: test enrichment and static analysis. These can run purely locally with clear safety boundaries.

### 3.1 Test Enrichment Engine

Responsibilities:

- Analyze a code change or bug description.
- Propose or generate tests (possibly as text or file patches).
- Optionally run tests and report pass/fail.

Backend tasks:

- `agent/orchestration/capabilities.py`:
  - Add a `TEST_ENRICHMENT` capability flag (if capabilities are typed by engine).
- `agent/orchestration/apply.py`:
  - Add an engine branch that:
    - Accepts a plan/test generation request.
    - Writes tests to `/tmp` or to `tests/` (in a sandboxed fashion).
    - Optionally runs `pytest` with a safe subset of flags.
    - Returns:
      - Generated test file names.
      - Test run results (test names, pass/fail).

Integration:

- For `TEST_ENRICHMENT` stage type:
  - Use this engine instead of generic patch engine.
  - Attach results to `work_item.data["test_enrichment"]` (e.g. list of suggested tests + run results).

### 3.2 Static Analysis Engine

Responsibilities:

- Run selected static analysis tools (e.g. `ruff`, `eslint`, `mypy`, or `semgrep`).
- Summarize findings for the agent / user.

Backend tasks:

- Similar pattern:
  - Add `STATIC_ANALYSIS` engine flag.
  - Implement engine in `apply.py` that:
    - Runs configured tools in the workspace.
    - Collects output (e.g. JSON or parsed text).
    - Stores results in `work_item.data["static_analysis"]`.

Stage type:

- Optionally add a `STATIC_ANALYSIS` stage type (later phase) once engine is stable.

Tests:

- Unit tests for engine wrappers with small sample repos.
- E2E test:
  - Stage that runs test enrichment and/or static analysis in a workflow and asserts data is stored.

Complexity: **Medium** – new engines and subprocess handling, but constrained to local tools.

---

## 4. Phase 4 – Security & Compliance Engine (Higher Risk)

**Goal:** Add a security‑focused engine for SAST/secret scanning/dependency checking, with conservative defaults and strong guardrails.

Capabilities:

- Run tools like:
  - `bandit`, `semgrep`, or language‑specific security scanners.
  - Secret scanners.
  - Dependency scanners (e.g. pip audit, npm audit).
- Summarize:
  - Findings by severity.
  - Files impacted.

Stage type:

- `SECURITY_REVIEW` (new stage type).

Behavior:

- Never auto‑apply changes.
- Always advisory; human must review.

Backend tasks:

- Implement a security engine similar to static analysis:
  - Wrap CLI tools and parse output.
  - Normalize to a common finding model:
    - Severity, category, location, description, remediation hint.
  - Attach to `work_item.data["security_findings"]`.
- Extend Agent Assist:
  - Agent can “explain” findings and suggest remediation steps (PLAN).

Frontend:

- Work item view:
  - Add a Security Findings section:
    - Grouped by severity.
    - Collapsible panels.

Tests:

- Local sample repo with known issues.
- E2E test where:
  - A `SECURITY_REVIEW` stage runs and stores at least one synthetic finding.

Complexity: **Medium‑High** – integration with more sensitive tools and data; requires careful tuning.

---

## 5. Phase 5 – CI / PR Integration (Webhooks & PR Workflows)

**Goal:** Tie the Agent + Workflow system into Git hosting/CI events (e.g. GitHub webhooks, CI failures).

Use cases:

- PR opened → create a WorkItem in Code Review workflow with PR metadata.
- CI fails → create a WorkItem in “CI Triage” workflow.

Backend tasks:

- Add a webhook endpoint (e.g. `POST /api/v1/hooks/github`) that:
  - Validates source and signature.
  - Normalizes events:
    - `pull_request.opened`, `pull_request.synchronize`.
    - `check_run.completed` / CI failure events.
  - Emits internal events similar to `agent.apply.success`.

- Extend `workflow_triggers`:
  - Add `ON_WEBHOOK` or a more specific trigger type:
    - `ON_PR_EVENT`, `ON_CI_FAILURE`.
  - Resolve which workflows have triggers configured for those events.
  - Create WorkItems with relevant event data:
    - PR URL, branch, CI job, logs link, etc.

Frontend:

- WorkflowDesigner:
  - Allow configuration of triggers:
    - Dropdown for “When a PR is opened” or “When CI fails” (even if initially backed by static config).

Tests:

- Unit tests for webhook handler with sample payloads.
- E2E:
  - Simulated webhook POST → WorkItem created in the right workflow.

Complexity: **High** – external integration, webhook security, user expectations.

---

## 6. Phase 6 – File Pattern & Scheduled Triggers

**Goal:** Make workflows react to file changes and time‑based events, expanding automation beyond manual triggers.

Use cases:

- “When files under `infra/**` change, create a work item in the 'Infra Review' workflow.”
- “Nightly, run dependency updates workflow.”

Backend tasks:

- `ON_FILE_PATTERN` triggers (already partly designed):
  - Implement a watcher or a periodic task that:
    - Inspects recent commits or file system changes.
    - Emits `file_event` structures (path, change type).
  - Extend `workflow_triggers`:
    - `handle_file_event` to match patterns and create WorkItems.

- Scheduled triggers:
  - Use a simple scheduler (cron‑like) in the background jobs service:
    - Emits `schedule_event` at configured times.
  - `workflow_triggers.handle_schedule_event` triggers workflows accordingly.

Frontend:

- WorkflowDesigner:
  - Triggers UI allowing:
    - File pattern configuration (`glob`, `regex`).
    - Schedule configuration (`cron` or friendly UI).

Tests:

- Unit tests for pattern matching and scheduling.
- E2E:
  - Simulate a file event or schedule tick and verify WorkItem creation.

Complexity: **High** – background jobs, pattern semantics, and scheduling.

---

## 7. Phase 7 – Incident Response & External Tools

**Goal:** Turn the system into a hub for incident response and cross‑tool automation.

Use cases:

- Monitoring alert → “Incident Response” workflow with Agent Assist summarizing logs.
- Ticketing system (Jira, Linear, etc.) → WorkItems synced in workflows.

Backend tasks:

- Add connectors:
  - In a `services/integrations/` package:
    - `monitoring_integration.py` (e.g. Prometheus, Datadog, Sentry).
    - `ticketing_integration.py` (e.g. Jira, Linear).
  - Map events → triggers → WorkItems.

- Agent Assist for incidents:
  - Stage type `INCIDENT_ANALYSIS` with prompts tailored to log summarization and mitigation suggestions.

Frontend:

- Workflows:
  - Prebuilt “Incident Response” template with:
    - Intake.
    - Agent incident analysis.
    - Human mitigation steps.

Tests:

- Unit tests for integration adapters using stubbed payloads.
- E2E:
  - Simulated alert payload → WorkItem + Agent analysis.

Complexity: **Very High** – external APIs, authentication, error handling, and user expectations.

---

## 8. Phase 8 – Multi‑Step Auto‑Flows & Playbooks

**Goal:** Allow carefully controlled, multi‑step automation “playbooks” that can run semi‑automatically with checkpointing and rollback.

Concept:

- A “playbook” is a workflow + engine configuration that:
  - Executes sequences of agent + non‑agent steps.
  - Includes safe automated transitions (e.g. from `STATIC_ANALYSIS` to `TEST_ENRICHMENT`).
  - Requires human approvals at key steps (security review, deployment).

Backend tasks:

- Extend WorkflowOrchestrator:
  - Allow stages to declare **auto‑transition rules**:
    - E.g. “If all tests pass and no high‑severity findings, auto‑move to next stage.”
  - Support checkpointing:
    - Capture a snapshot of key data at each stage for debugging/rollback.

- Add rollback hooks:
  - For certain engines, support optional rollback actions (e.g., revert patch if auto‑apply fails later).

Frontend:

- “Playbook” view:
  - Show a condensed view of the high‑level flow.
  - Surface where auto transitions can happen and where approvals are required.

Tests:

- Complex E2E scenarios:
  - Simulate a playbook from start to finish with auto steps and manual approvals.

Complexity: **Very High** – cross‑cutting across orchestrator, engines, UI, and user training.

---

## 9. Suggested Implementation Order

From easiest to hardest, and which deliver immediate value:

1. **Phase 1 – Opinionated Stage Types**
   - Quick wins on top of existing Agent Assist.
   - Low risk, mostly prompts + labels.

2. **Phase 2 – High‑Quality Global Templates**
   - Makes the system feel “ready to use” for real workflows.
   - No new engines needed.

3. **Phase 3 – Test & Static Analysis Engines**
   - First real new engine integrations, but limited blast radius.
   - Strong value for code quality and confidence.

4. **Phase 4 – Security Engine**
   - Higher sensitivity; add once the previous engines and stage types feel stable.

5. **Phase 5 – CI / PR Integration**
   - Starts pulling external systems into the loop.
   - Requires careful design for webhooks and trust boundaries.

6. **Phase 6 – File Pattern & Scheduled Triggers**
   - Powerful for “always‑on” automation.
   - Requires background processing and careful scheduling semantics.

7. **Phase 7 – Incident Response & External Tools**
   - Strategic integrations, complex and high‑impact.

8. **Phase 8 – Multi‑Step Auto‑Flows & Playbooks**
   - Capstone: orchestrated, semi‑automatic workflows with strong guardrails.

At each phase:

- Keep behavior **opt‑in**.
- Add **at least one template** that showcases the new capabilities.
- Extend **E2E smoke tests** to cover a “happy path” through the new feature.
- Update **docs** so the product story stays aligned with the implementation.

