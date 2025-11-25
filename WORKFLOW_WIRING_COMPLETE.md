# Workflow Wiring Complete ✓

## Overview
Step 4 (Workflows) has been fully implemented with all endpoints, models, service layer, and state management wired to the FastAPI backend.

## Components Created

### 1. Workflow Models
**Location**: `apps/native/Shared/Models/WorkflowModels.swift`

#### Workflow
```swift
struct Workflow: Codable, Identifiable {
    let id: String
    let name: String
    let description: String?
    let icon: String?
    let category: String?
    let workflowType: String?     // "local" | "team"
    let visibility: String?        // "personal" | "team" | "global"
    let isTemplate: Bool?
    let stages: [Stage]?
    let triggers: [WorkflowTrigger]?
    let ownerUserId: String?
}
```

#### Stage
```swift
struct Stage: Codable, Identifiable {
    let id: String
    let name: String
    let description: String?
    let stageType: String
    let assignmentType: String
    let order: Int
    let nextStages: [ConditionalRoute]?
    let slaMinutes: Int?
    let roleName: String?
}
```

#### ConditionalRoute
```swift
struct ConditionalRoute: Codable, Identifiable {
    let id: String?
    let nextStageId: String
    let conditions: [[String: AnyCodable]]?
}
```

#### WorkflowTrigger
```swift
struct WorkflowTrigger: Codable {
    let triggerType: String
    let enabled: Bool?
}
```

#### WorkItem
```swift
struct WorkItem: Codable, Identifiable {
    let id: String
    let workflowId: String
    let currentStageId: String
    let status: String             // "claimed" | "in_progress" | "completed"
    let priority: String           // "urgent" | "high" | "normal" | "low"
    let data: [String: AnyCodable]
    let referenceNumber: String?
    let currentStageName: String?
    let workflowName: String?
    let isOverdue: Bool?
    let completedAt: String?
}
```

#### WorkflowAnalytics
```swift
struct WorkflowAnalytics: Codable {
    let workflowName: String
    let totalItems: Int
    let completedItems: Int
    let inProgressItems: Int
    let averageCycleTimeSeconds: Int?
    let medianCycleTimeSeconds: Int?
    let cancelledItems: Int
    let failedItems: Int
    let stages: [StageAnalytics]?
}

struct StageAnalytics: Codable, Identifiable {
    let stageId: String
    let stageName: String
    let enteredCount: Int
    let completedCount: Int
    let averageTimeSeconds: Int?
    let medianTimeSeconds: Int?
}
```

#### Request Models
```swift
struct InstantiateTemplateRequest: Codable {
    let name: String
    let description: String?
}

struct SaveWorkflowRequest: Codable {
    let workflowId: String
    let name: String
    let nodes: [[String: AnyCodable]]
    let edges: [[String: AnyCodable]]
}

struct RunWorkflowRequest: Codable {
    let workflowId: String
    let name: String
    let nodes: [[String: AnyCodable]]
    let edges: [[String: AnyCodable]]
}
```

### 2. WorkflowService
**Location**: `apps/native/Shared/Services/WorkflowService.swift`

All endpoints wired:

| Method | Endpoint | Returns |
|--------|----------|---------|
| `listWorkflows(type:)` | `GET /v1/workflows?workflow_type={type}` | `[Workflow]` |
| `starWorkflow(id:)` | `POST /v1/workflows/{id}/star` | `EmptyResponse` |
| `unstarWorkflow(id:)` | `DELETE /v1/workflows/{id}/star` | `EmptyResponse` |
| `listTemplates()` | `GET /v1/workflow/templates` | `[Workflow]` |
| `instantiateTemplate(id:name:description:)` | `POST /v1/workflow/templates/{id}/instantiate` | `Workflow` |
| `getQueue(workflowId:role:)` | `GET /v1/workflows/{id}/work-items?role=...` | `[WorkItem]` |
| `getMyWork(workflowId:)` | `GET /v1/workflows/{id}/work-items/my` | `[WorkItem]` |
| `claimWorkItem(id:userId:)` | `POST /v1/work-items/{id}/claim` | `WorkItem` |
| `startWorkItem(id:userId:)` | `POST /v1/work-items/{id}/start` | `WorkItem` |
| `saveWorkflow(workflowId:name:nodes:edges:)` | `POST /v1/automation/save` | `EmptyResponse` |
| `runWorkflow(workflowId:name:nodes:edges:)` | `POST /v1/automation/run` | `EmptyResponse` |
| `fetchAnalytics(workflowId:)` | `GET /v1/workflows/{id}/analytics` | `WorkflowAnalytics` |

### 3. WorkflowStore
**Location**: `apps/native/Shared/Stores/WorkflowStore.swift`

State management with comprehensive workflow operations:

#### Published State
```swift
@Published var workflows: [Workflow] = []
@Published var templates: [Workflow] = []
@Published var starredIds: Set<String> = []
@Published var queueItems: [WorkItem] = []
@Published var myWorkItems: [WorkItem] = []
@Published var analytics: WorkflowAnalytics?
@Published var selectedWorkflow: Workflow?
@Published var isLoading = false
@Published var error: String?
```

#### Public Methods

**Workflow Management**
- `loadWorkflows(type:)` - Loads workflows by type (local/team)
- `toggleStar(id:)` - Stars/unstars workflow, updates starredIds

**Templates**
- `loadTemplates()` - Fetches all templates
- `instantiateTemplate(templateId:name:description:)` - Creates new workflow from template

**Work Items / Queue**
- `loadQueue(workflowId:role:)` - Fetches queue items (optionally filtered by role)
- `loadMyWork(workflowId:)` - Fetches user's active work items
- `claimAndStart(workItemId:userId:)` - Claims and starts item (combo operation)
- `claimWorkItem(workItemId:userId:)` - Claims item only
- `startWorkItem(workItemId:userId:)` - Starts claimed item

**Builder**
- `saveWorkflow(workflowId:name:nodes:edges:)` - Saves workflow definition
- `runWorkflow(workflowId:name:nodes:edges:)` - Executes workflow

**Analytics**
- `loadAnalytics(workflowId:)` - Fetches workflow analytics

**Helpers**
- `workItemsByStage(items:)` - Groups work items by current stage
- `starredWorkflows` - Computed property for starred workflows
- `workflows(byCategory:)` - Filters workflows by category

## API Endpoints Wired

### Workflow Management
```
GET /api/v1/workflows?workflow_type=local|team
→ [Workflow]

POST /api/v1/workflows/{id}/star
→ EmptyResponse

DELETE /api/v1/workflows/{id}/star
→ EmptyResponse
```

### Templates
```
GET /api/v1/workflow/templates
→ [Workflow]

POST /api/v1/workflow/templates/{id}/instantiate
Body: { name: String, description?: String }
→ Workflow
```

### Work Items / Queue
```
GET /api/v1/workflows/{id}/work-items?role={role}
→ [WorkItem]

GET /api/v1/workflows/{id}/work-items/my
→ [WorkItem]

POST /api/v1/work-items/{id}/claim
Body: { userId: String }
→ WorkItem

POST /api/v1/work-items/{id}/start
Body: { userId: String }
→ WorkItem
```

### Builder (Save/Run)
```
POST /api/v1/automation/save
Body: { workflow_id, name, nodes: [[...]], edges: [[...]] }
→ EmptyResponse

POST /api/v1/automation/run
Body: { workflow_id, name, nodes: [[...]], edges: [[...]] }
→ EmptyResponse
```

### Analytics
```
GET /api/v1/workflows/{id}/analytics
→ WorkflowAnalytics
```

## UI Binding Checklist

### Workflow Dashboard
✓ **List workflows**: `workflowStore.workflows`
✓ **Filter by type**: `loadWorkflows(type: "local")` or `"team"`
✓ **Star toggle**: `toggleStar(id:)`, bind to `starredIds.contains(id)`
✓ **Starred only**: `workflowStore.starredWorkflows`
✓ **Category filter**: `workflows(byCategory:)`
✓ **Create from template**: Show templates modal

### Templates Modal
✓ **List templates**: `workflowStore.templates`
✓ **Load**: `loadTemplates()`
✓ **Instantiate**: `instantiateTemplate(templateId:name:description:)`
✓ **On success**: New workflow added to list, selected

### Queue / My Work
✓ **Load queue**: `loadQueue(workflowId:role:)`
✓ **Load my work**: `loadMyWork(workflowId:)`
✓ **Claim**: `claimWorkItem(workItemId:userId:)`
✓ **Start**: `startWorkItem(workItemId:userId:)`
✓ **Claim + Start**: `claimAndStart(workItemId:userId:)`
✓ **Remove from queue**: Auto-removed after claim
✓ **Add to my work**: Auto-added after claim

### Workflow Builder
✓ **Save**: `saveWorkflow(workflowId:name:nodes:edges:)`
✓ **Run**: `runWorkflow(workflowId:name:nodes:edges:)`
✓ **Loading state**: `workflowStore.isLoading`
✓ **Nodes/edges**: Pass as `[[String: Any]]` arrays

### Analytics View
✓ **Load**: `loadAnalytics(workflowId:)`
✓ **Display**: `workflowStore.analytics`
✓ **Stage breakdown**: `analytics.stages` array
✓ **Metrics**: totalItems, completedItems, cycle times, etc.

### Status Tracker
✓ **Group by stage**: `workItemsByStage(items:)`
✓ **Pass items**: `queueItems` or `myWorkItems`
✓ **Returns**: `[stageId: [WorkItem]]` dictionary

## State Flow Examples

### Load and Star Workflows
```swift
// 1. Load workflows
await workflowStore.loadWorkflows(type: "local")
// → workflows populated

// 2. Star a workflow
await workflowStore.toggleStar(id: "workflow-123")
// → starredIds updated

// 3. Get starred only
let starred = workflowStore.starredWorkflows
// → filtered list
```

### Create from Template
```swift
// 1. Load templates
await workflowStore.loadTemplates()
// → templates populated

// 2. User selects template, enters name
await workflowStore.instantiateTemplate(
    templateId: "template-abc",
    name: "My Custom Workflow",
    description: "Based on approval template"
)
// → new workflow created, added to workflows list, selectedWorkflow set
```

### Claim and Start Work
```swift
// 1. Load queue for workflow
await workflowStore.loadQueue(workflowId: "workflow-123", role: "approver")
// → queueItems populated

// 2. User claims and starts item
await workflowStore.claimAndStart(
    workItemId: "item-456",
    userId: currentUserId
)
// → item removed from queueItems
// → item added to myWorkItems with status "in_progress"
```

### Save and Run Workflow
```swift
// 1. User designs workflow in builder
let nodes: [[String: Any]] = [...]
let edges: [[String: Any]] = [...]

// 2. Save
await workflowStore.saveWorkflow(
    workflowId: "workflow-123",
    name: "Updated Approval Flow",
    nodes: nodes,
    edges: edges
)
// → saved to backend

// 3. Run
await workflowStore.runWorkflow(
    workflowId: "workflow-123",
    name: "Updated Approval Flow",
    nodes: nodes,
    edges: edges
)
// → workflow executed
```

### View Analytics
```swift
// 1. Load analytics
await workflowStore.loadAnalytics(workflowId: "workflow-123")
// → analytics populated

// 2. Display metrics
let total = workflowStore.analytics?.totalItems
let completed = workflowStore.analytics?.completedItems
let avgCycleTime = workflowStore.analytics?.averageCycleTimeSeconds

// 3. Show stage breakdown
if let stages = workflowStore.analytics?.stages {
    for stage in stages {
        print("\(stage.stageName): \(stage.completedCount) completed")
    }
}
```

### Group Work Items by Stage
```swift
// 1. Get items
let items = workflowStore.myWorkItems

// 2. Group by stage
let byStage = workflowStore.workItemsByStage(items: items)
// → ["stage-1": [item1, item2], "stage-2": [item3]]

// 3. Display in columns/sections
ForEach(byStage.keys.sorted(), id: \.self) { stageId in
    let items = byStage[stageId] ?? []
    // Render stage column with items
}
```

## Error Handling

All errors surfaced via `@Published var error: String?`:
- Network errors
- 401/403 auth errors
- API errors (4xx, 5xx)
- Validation errors
- Star/unstar failures
- Claim/start failures

UI should bind to `workflowStore.error` for toast/banner display.

## Integration with ContentView

Add to ContentView (if not already using existing workflow stores):
```swift
@StateObject private var workflowStore = WorkflowStore.shared

// In .authenticated case:
MainAppView()
    .environmentObject(workflowStore)

// On auth success (optional):
.onChange(of: authStore.authState) { _, newState in
    if newState == .authenticated {
        Task {
            await workflowStore.loadWorkflows(type: "local")
        }
    }
}
```

## Next Steps

Workflows are fully wired! Ready for:

### Step 5: Vault
- Unlock: `POST /v1/vault/unlock`
- Files: `GET /v1/vault/files`, `GET /v1/vault/files/{id}/download`
- Upload: `POST /v1/vault/files`
- Folders: `GET /v1/vault/folders`, `POST /v1/vault/folders`
- Delete: `DELETE /v1/vault/files/{id}`, `DELETE /v1/vault/folders`

### Step 6: Settings
- Saved queries: `GET/POST/PUT/DELETE /v1/settings/saved-queries`
- Metal4 monitoring: `GET /v1/monitoring/metal4`

## Notes

- All snake_case API fields auto-converted via JSONDecoder
- All auth requests auto-inject `Authorization: Bearer <token>`
- Starred workflows stored in Set for O(1) lookup
- Work items auto-move from queue to myWork on claim
- ClaimAndStart is atomic operation (claim → start)
- Analytics include both workflow-level and stage-level metrics
- Nodes/edges use `[[String: AnyCodable]]` for flexible JSON structure
- WorkflowAnalytics renamed to avoid potential conflicts
- Helper methods for filtering and grouping workflows/items
