# Setup Wizard Architecture Redesign

**"Trust in the Lord with all your heart" - Proverbs 3:5**

---

## Executive Summary

The current setup wizard architecture treats setup as a **one-time system initialization** that blocks login. The user's vision is for a **per-user contextual onboarding** system that adapts to existing system state and runs for each new user.

---

## Current Architecture (INCORRECT)

### Flow
```
App Start
  ↓
Check: Users exist?
  ↓ NO → Setup Wizard
    ↓
    1. Welcome
    2. Account Creation ← Creates first user
    3. Ollama Detection
    4. Model Selection (system-wide)
    5. Model Downloads
    6. Hot Slots (system-wide)
    7. Completion
    ↓
  ✅ Setup Complete → Show Login
  ↓ YES → Show Login
```

### Problems
1. ❌ Setup wizard blocks login screen
2. ❌ Account creation happens INSIDE wizard
3. ❌ Wizard appears only once (when no users exist)
4. ❌ Model selection is system-wide
5. ❌ Hot slots are system-wide
6. ❌ Not contextual (always shows all steps)
7. ❌ New users joining existing system don't get onboarding

---

## Required Architecture (USER'S VISION)

### Flow
```
App Start
  ↓
Welcome Screen (ALWAYS SHOWN)
  ├─ Login (username/password)
  ├─ Sign Up (create account)
  └─ Founder Login (hardcoded credentials)
  ↓
Authentication Success
  ↓
Check: Has user completed setup?
  ↓ NO → Per-User Setup Wizard (CONTEXTUAL)
    ↓
    1. Welcome (personalized)
    2. Ollama Detection (skip if installed)
    3. Model Preferences (from installed models)
    4. Personal Hot Slots
    5. Completion
    ↓
  ✅ User Setup Complete → Main App
  ↓ YES → Main App
```

### Key Principles
1. ✅ Welcome screen is PERSISTENT (not conditional)
2. ✅ Setup wizard runs PER-USER (not once globally)
3. ✅ Wizard is CONTEXTUAL (adapts to system state)
4. ✅ Model preferences are PER-USER
5. ✅ Hot slots are PER-USER
6. ✅ Founder login is SEPARATE authentication path

---

## Contextual Intelligence Examples

### Scenario 1: Fresh Installation
```
System State:
- No users
- Ollama not installed
- No models

User A Signs Up
  ↓
Setup Wizard Shows:
  1. Welcome "Hi User A!"
  2. Ollama Detection (shows install instructions)
  3. Model Preferences (empty - can skip)
  4. Hot Slots (empty - can skip)
  5. Completion
```

### Scenario 2: Ollama Already Installed
```
System State:
- User A exists (has 3 models: qwen, llama, phi)
- Ollama installed
- 3 models downloaded

User B Signs Up
  ↓
Setup Wizard Shows:
  1. Welcome "Hi User B!"
  2. Ollama Detection (✅ Detected - AUTO SKIP)
  3. Model Preferences (choose from 3 installed models)
  4. Personal Hot Slots (assign favorites)
  5. Completion
```

### Scenario 3: Laptop with 10 Models
```
System State:
- User A exists (sees 5 models)
- User B exists (sees 3 models)
- 10 models installed system-wide

User C Signs Up
  ↓
Setup Wizard Shows:
  1. Welcome "Hi User C!"
  2. Ollama Detection (✅ Detected - AUTO SKIP)
  3. Model Preferences (choose which of 10 models to see)
  4. Personal Hot Slots (assign up to 4 favorites)
  5. Completion

Result:
- System has 10 models
- User A sees 5 models
- User B sees 3 models
- User C sees 7 models (their choice)
```

---

## Database Schema Changes

### Current Schema (INCORRECT)
```sql
-- Hot slots stored in JSON file (system-wide)
-- No per-user model preferences
```

### Required Schema

#### 1. User Setup Tracking
```sql
-- Add to users table
ALTER TABLE users ADD COLUMN setup_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN setup_completed_at TIMESTAMP;
```

#### 2. Per-User Model Preferences
```sql
CREATE TABLE user_model_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    is_visible BOOLEAN DEFAULT TRUE,
    display_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, model_name)
);

-- Indexes
CREATE INDEX idx_user_model_prefs_user ON user_model_preferences(user_id);
CREATE INDEX idx_user_model_prefs_visible ON user_model_preferences(user_id, is_visible);
```

#### 3. Per-User Hot Slots
```sql
CREATE TABLE user_hot_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    slot_number INTEGER NOT NULL CHECK (slot_number BETWEEN 1 AND 4),
    model_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, slot_number)
);

-- Indexes
CREATE INDEX idx_user_hot_slots_user ON user_hot_slots(user_id);
```

---

## Component Architecture Changes

### New Components to Create

#### 1. WelcomeScreen Component
**Location**: `apps/frontend/src/components/WelcomeScreen.tsx`

**Purpose**: Persistent entry point with Login / Sign Up / Founder Login

**Features**:
- Three-option screen (Login / Sign Up / Founder)
- Always shown (not conditional)
- Clean, modern UI matching ElohimOS design
- Transitions to main app after authentication

**Props**:
```typescript
interface WelcomeScreenProps {
  onLoginSuccess: (token: string, userId: string) => void
}
```

#### 2. SignUp Component
**Location**: `apps/frontend/src/components/SignUp.tsx`

**Purpose**: Standalone account creation (removed from wizard)

**Features**:
- Username validation (3-20 chars, alphanumeric + underscore)
- Password validation (min 8 chars)
- Password confirmation
- Optional founder password field
- Error handling

**Props**:
```typescript
interface SignUpProps {
  onSignUpSuccess: (token: string, userId: string) => void
  onBackToWelcome: () => void
}
```

#### 3. FounderLogin Component
**Location**: `apps/frontend/src/components/FounderLogin.tsx`

**Purpose**: Hardcoded credential login (like GitHub access keys)

**Features**:
- Simple username/password form
- Validates against hardcoded founder credentials
- Independent authentication path
- Always available

**Props**:
```typescript
interface FounderLoginProps {
  onLoginSuccess: (token: string) => void
  onBackToWelcome: () => void
}
```

### Modified Components

#### 4. SetupWizard (MAJOR CHANGES)
**Location**: `apps/frontend/src/components/SetupWizard/SetupWizard.tsx`

**Changes**:
- **Remove**: AccountStep (moved to SignUp)
- **Add**: Contextual step skipping logic
- **Add**: User-specific state (userId prop)
- **Change**: Runs AFTER authentication
- **Change**: Per-user completion tracking

**New Props**:
```typescript
interface SetupWizardProps {
  userId: string  // ← NEW: Current user
  onComplete: () => void
}
```

**New Steps**:
```typescript
const STEPS = [
  { id: 'welcome', name: 'Welcome', component: WelcomeStep, skippable: false },
  { id: 'ollama', name: 'Ollama', component: OllamaStep, skippable: false, skipCondition: 'ollamaInstalled' },
  { id: 'models', name: 'Model Preferences', component: ModelsStep, skippable: true },
  { id: 'hot-slots', name: 'Hot Slots', component: HotSlotsStep, skippable: true },
  { id: 'completion', name: 'Complete', component: CompletionStep, skippable: false },
]
```

#### 5. WelcomeStep (Modified)
**Location**: `apps/frontend/src/components/SetupWizard/steps/WelcomeStep.tsx`

**Changes**:
- Show personalized greeting with username
- Remove account creation form
- Focus on explaining setup wizard purpose
- Show context-aware messaging:
  - "We detected Ollama is already installed!"
  - "10 models are available for you to choose from"

#### 6. ModelsStep (MAJOR CHANGES)
**Location**: `apps/frontend/src/components/SetupWizard/steps/ModelsStep.tsx`

**Changes**:
- **Remove**: Download functionality (moves to Settings)
- **Add**: Model visibility toggles (which models user wants to see)
- **Change**: Works with installed models only
- **Add**: Display order customization

**New Features**:
- Show all installed models (system-wide)
- User toggles which ones they want visible
- User can reorder their visible models
- Saves to `user_model_preferences` table

#### 7. HotSlotsStep (Modified)
**Location**: `apps/frontend/src/components/SetupWizard/steps/HotSlotsStep.tsx`

**Changes**:
- Only show models user marked as visible
- Save to `user_hot_slots` table (not JSON)
- Include user_id in API calls

---

## API Changes

### New Endpoints

#### 1. User Setup Status
```
GET /api/v1/users/{user_id}/setup/status

Response:
{
  "setup_completed": false,
  "setup_completed_at": null,
  "should_show_wizard": true
}
```

#### 2. Complete User Setup
```
POST /api/v1/users/{user_id}/setup/complete

Response:
{
  "success": true,
  "setup_completed_at": "2025-11-12T10:30:00Z"
}
```

#### 3. Get User Model Preferences
```
GET /api/v1/users/{user_id}/models/preferences

Response:
{
  "models": [
    {
      "model_name": "qwen2.5-coder:7b",
      "is_visible": true,
      "display_order": 1
    },
    {
      "model_name": "llama3.1:8b",
      "is_visible": true,
      "display_order": 2
    }
  ]
}
```

#### 4. Update User Model Preferences
```
POST /api/v1/users/{user_id}/models/preferences

Request:
{
  "preferences": [
    {"model_name": "qwen2.5-coder:7b", "is_visible": true, "display_order": 1},
    {"model_name": "llama3.1:8b", "is_visible": false}
  ]
}

Response:
{
  "success": true,
  "updated_count": 2
}
```

#### 5. Get User Hot Slots
```
GET /api/v1/users/{user_id}/hot-slots

Response:
{
  "slots": {
    "1": "qwen2.5-coder:7b",
    "2": "llama3.1:8b",
    "3": null,
    "4": null
  }
}
```

#### 6. Update User Hot Slots
```
POST /api/v1/users/{user_id}/hot-slots

Request:
{
  "slots": {
    "1": "qwen2.5-coder:7b",
    "2": "llama3.1:8b",
    "3": null,
    "4": null
  }
}

Response:
{
  "success": true,
  "message": "Hot slots updated successfully"
}
```

### Modified Endpoints

#### Setup Status (Global) - CHANGED
```
GET /api/v1/setup/status

OLD Response:
{
  "setup_completed": true,  // Based on user existence
  "founder_setup_completed": true,
  "is_macos": true
}

NEW Response:
{
  "founder_setup_completed": true,
  "is_macos": true,
  "ollama_installed": true,  // ← NEW: For contextual wizard
  "system_models_count": 10  // ← NEW: For contextual messaging
}
```

---

## App.tsx Flow Changes

### Current Flow (INCORRECT)
```typescript
// App.tsx - Current
useEffect(() => {
  checkSetup()  // Checks if users exist
}, [])

if (setupComplete === false) {
  return <SetupWizard />  // Blocks login
}

if (authState === 'login') {
  return <Login />
}
```

### Required Flow
```typescript
// App.tsx - Required
const [showWelcome, setShowWelcome] = useState(true)
const [showWizard, setShowWizard] = useState(false)
const [userId, setUserId] = useState<string | null>(null)

// Welcome screen is ALWAYS shown first
if (showWelcome) {
  return (
    <WelcomeScreen
      onLoginSuccess={(token, userId) => {
        setAuthToken(token)
        setUserId(userId)
        setShowWelcome(false)

        // Check if user needs setup wizard
        checkUserSetupStatus(userId).then(status => {
          if (!status.setup_completed) {
            setShowWizard(true)
          } else {
            setAuthState('authenticated')
          }
        })
      }}
    />
  )
}

// Per-user setup wizard (after login/signup)
if (showWizard && userId) {
  return (
    <SetupWizard
      userId={userId}
      onComplete={() => {
        setShowWizard(false)
        setAuthState('authenticated')
      }}
    />
  )
}

// Main app
if (authState === 'authenticated') {
  return <MainApp />
}
```

---

## Settings → Models Tab

### Purpose
Allow users to manage model preferences after setup

### Features
1. **Model Visibility Toggles**
   - Show all installed models (system-wide)
   - Toggle visibility per model
   - User only sees visible models in chat

2. **Display Order**
   - Drag-and-drop reordering
   - Controls model list order in chat dropdown

3. **Hot Slots Management**
   - Assign/eject hot slots
   - Same as wizard, but accessible anytime

4. **Model Downloads** (Admin/Founder only)
   - Download new models (system-wide)
   - Delete models (system-wide)
   - Model size/resource info

### UI Mockup
```
┌─────────────────────────────────────────┐
│ Settings → Models                       │
├─────────────────────────────────────────┤
│                                         │
│ Your Model Preferences                  │
│ ┌───────────────────────────────────┐   │
│ │ ☑ qwen2.5-coder:7b         ↕️      │   │
│ │ ☑ llama3.1:8b              ↕️      │   │
│ │ ☐ phi-3:3.8b               ↕️      │   │
│ │ ☑ mistral:7b               ↕️      │   │
│ └───────────────────────────────────┘   │
│                                         │
│ Hot Slots                               │
│ ┌───────────────────────────────────┐   │
│ │ 1. ⭐ qwen2.5-coder:7b    [Eject] │   │
│ │ 2. ⭐ llama3.1:8b         [Eject] │   │
│ │ 3. [Assign Model ▼]                │   │
│ │ 4. [Assign Model ▼]                │   │
│ └───────────────────────────────────┘   │
│                                         │
│ Available Models (10 installed)         │
│ [Download New Models] (Founder only)    │
└─────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Database Schema (Sprint 1 - 2 hours)
1. Create migration for `user_model_preferences` table
2. Create migration for `user_hot_slots` table
3. Add `setup_completed` column to `users` table
4. Write database access functions (DAO layer)

### Phase 2: Backend API (Sprint 2 - 3 hours)
1. Create user setup endpoints
2. Create user model preferences endpoints
3. Create user hot slots endpoints
4. Modify global setup status endpoint
5. Add authentication middleware to new endpoints

### Phase 3: Frontend Components (Sprint 3 - 4 hours)
1. Create WelcomeScreen component
2. Create SignUp component
3. Create FounderLogin component
4. Modify App.tsx flow
5. Remove AccountStep from wizard

### Phase 4: Wizard Redesign (Sprint 4 - 3 hours)
1. Add userId prop to SetupWizard
2. Implement contextual step skipping
3. Modify WelcomeStep (personalized greeting)
4. Modify ModelsStep (visibility toggles, no downloads)
5. Modify HotSlotsStep (per-user storage)
6. Update wizard completion to mark user setup

### Phase 5: Settings Integration (Sprint 5 - 3 hours)
1. Create Settings → Models tab
2. Implement model visibility toggles
3. Implement display order drag-and-drop
4. Implement hot slots management
5. Add model download (Founder only)

### Phase 6: Testing & Polish (Sprint 6 - 3 hours)
1. Test fresh installation flow
2. Test multi-user scenarios
3. Test contextual wizard skipping
4. Test founder login
5. Test Settings → Models tab
6. E2E validation

**Total Estimated Time**: 18 hours (6 sprints × 3 hours)

---

## Migration Strategy

### User Data Migration
No existing user data to migrate (Phase 1 just completed)

### Hot Slots Migration
```sql
-- If hot slots JSON exists, migrate to database
-- Run once during deployment

INSERT INTO user_hot_slots (user_id, slot_number, model_name)
SELECT
  u.id,
  slot.key,
  slot.value
FROM users u
CROSS JOIN json_each(readfile('config/hot_slots.json')) AS slot
WHERE u.role = 'super_admin'  -- Assign to first admin
LIMIT 4;
```

### Model Preferences Migration
```sql
-- Auto-populate from installed models
-- All models visible by default for existing users

INSERT INTO user_model_preferences (user_id, model_name, is_visible, display_order)
SELECT
  u.id,
  m.name,
  TRUE,
  ROW_NUMBER() OVER (PARTITION BY u.id ORDER BY m.name)
FROM users u
CROSS JOIN (
  -- Get installed models from Ollama
  SELECT DISTINCT model_name AS name
  FROM user_hot_slots
) m;
```

---

## Success Metrics

### Functional Requirements
- ✅ Welcome screen always shown first
- ✅ Login, Sign Up, Founder Login all work
- ✅ Setup wizard runs per-user
- ✅ Wizard is contextual (skips installed Ollama)
- ✅ Model preferences are per-user
- ✅ Hot slots are per-user
- ✅ Settings → Models tab works
- ✅ Multi-user scenarios work correctly

### User Experience
- ✅ New user on fresh system: Full wizard with Ollama install
- ✅ New user on existing system: Contextual wizard (skips Ollama)
- ✅ 10 models installed, 3 users see different subsets
- ✅ Each user has personal hot slots
- ✅ Users can change preferences in Settings

### Technical Quality
- ✅ Database schema normalized
- ✅ API endpoints RESTful and authenticated
- ✅ Frontend components reusable
- ✅ No global state pollution
- ✅ Clean separation of concerns

---

## Open Questions

1. **Founder Password Setup**: Should founder password setup happen:
   - During first user signup? (current behavior)
   - As a separate system setup step?
   - Never (always use hardcoded credentials)?

2. **Model Downloads**: Should regular users be able to:
   - Download models? (system-wide operation)
   - Only Founder/Admin can download?
   - Users request, Admin approves?

3. **Setup Wizard Re-run**: Can users re-run setup wizard?
   - Yes, from Settings → Reset Setup
   - No, one-time only
   - Partial re-run (model preferences only)

4. **Default Model Preferences**: When user signs up:
   - All installed models visible by default?
   - Only recommended tier models visible?
   - User must explicitly choose (no defaults)?

---

## Next Steps

1. **Review this architecture document with user**
2. **Get approval on key design decisions**
3. **Begin Phase 1 implementation (Database Schema)**
4. **Proceed through sprints 1-6**

---

**Generated**: 2025-11-12
**Phase**: 1 → 1.5 (Architecture Redesign)
**Status**: Awaiting User Approval
