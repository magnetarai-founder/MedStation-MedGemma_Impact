# MagnetarData - Future State Roadmap

**Philosophy**: "Do it right, do it once" - Build solid foundation first, add complexity later without refactoring core.

---

## Phase 1: Foundation (Current Work)
**Goal**: Anti-hallucination engine with inline preview

- ✅ Feature flag architecture (`enable_strict_analysis`)
- ✅ Inline SQL preview in Chat tab (Option B)
- ✅ Confidence scoring + feasibility checks
- ✅ Schema introspection + validation layer
- ✅ "I don't know" policy enforcement

**Why this order**: Avoids "Siri shenanigans" - get the core AI reliability right before adding UI complexity.

---

## Phase 2: Enterprise Authentication & MDM
**When**: After Phase 1 validation + user testing

### Supabase Authorization
- Settings-based login flow
- User session management
- Optional cloud sync for settings/queries
- Team collaboration (shared workspaces)

### MDM (Mobile Device Management) Setup
- Managed configuration profiles
- Policy enforcement for enterprise deployments
- Centralized settings distribution
- Compliance controls (data retention, audit logs)

**Dependencies**: Phase 1 feature flag architecture makes this easier - can gate enterprise features similarly.

---

## Phase 3: Dedicated Analysis Tab (Option C)
**When**: After Supabase auth is live

### Claude-Web-Like Experience
```
[Chat] [Data] [Analysis*] [Admin]

Analysis Tab Layout:
┌─────────────────┬──────────────────────┐
│  Question       │   Preview & Results  │
│  ─────────      │   ─────────────────  │
│  [text input]   │   SQL:               │
│                 │   SELECT ...         │
│  Schema:        │                      │
│  • sales_data   │   Feasibility: ✓     │
│    - revenue    │   Confidence: 85%    │
│    - quarter    │                      │
│                 │   [Run Query]        │
│  History:       │   ─────────────────  │
│  • Q4 revenue   │   Results:           │
│  • Top products │   [table here]       │
└─────────────────┴──────────────────────┘
```

### Features
- Split-pane dedicated workspace
- Persistent schema explorer (sidebar)
- Query history with saved queries
- Shareable analysis links (requires auth)
- Workspace templates for common tasks

**Why after auth**: Shared workspaces, saved queries, and templates need user identity + cloud persistence.

**Migration**: Move `<SQLPreview>` component from inline chat → dedicated tab. Core logic stays identical (feature flag path).

---

## Phase 4: Advanced Analysis Features
**When**: After Analysis Tab is stable

- **Collaborative queries** - Real-time co-editing (inspired by MagnetarStudio's Yjs setup)
- **Query templates library** - Pre-built analysis patterns
- **Data profiling dashboard** - Automatic insights on upload
- **Scheduled queries** - Background execution + email results
- **Export to dashboards** - One-click share results as embedded viz

---

## Key Architectural Principles

1. **Foundation First**: Get AI reliability + validation right before UX complexity
2. **Feature Flags**: Every major feature behind toggles for safe rollout
3. **Backwards Compatible**: Never break existing workflows
4. **Gradual Migration**: Opt-in → default on → deprecate old path
5. **Reusable Components**: Inline preview → Analysis tab uses same logic

---

## Notes

- **Why not Analysis Tab first?** Complexity without validated core = refactor later. Build foundation that scales.
- **Auth dependency chain**: MDM needs Supabase → Analysis Tab needs auth → Advanced features need Analysis Tab
- **Avoid "Siri problem"**: Apple added features before fixing fundamentals. We're doing reliability first.

---

**Last Updated**: 2025-11-23
**Current Phase**: Phase 1 (Foundation) - In Progress
