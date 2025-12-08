# Zustand Store Optimization Guide

## MED-03: Preventing Unnecessary Re-renders

### Problem
By default, Zustand triggers re-renders whenever **any** part of the store changes, even if your component only uses a specific field.

### Solution: Shallow Selectors

Always use **shallow equality** when selecting multiple fields from a store:

```typescript
import { shallow } from 'zustand/shallow'
import { useSessionStore } from '@/stores/sessionStore'

// ❌ BAD: Re-renders on ANY store change
function MyComponent() {
  const { sessionId, isExecuting } = useSessionStore()
  // ...
}

// ✅ GOOD: Only re-renders when sessionId or isExecuting change
function MyComponent() {
  const { sessionId, isExecuting } = useSessionStore(
    (state) => ({ sessionId: state.sessionId, isExecuting: state.isExecuting }),
    shallow
  )
  // ...
}

// ✅ ALSO GOOD: Single field selection (no shallow needed)
function MyComponent() {
  const isExecuting = useSessionStore((state) => state.isExecuting)
  // ...
}
```

### Common Patterns

#### Pattern 1: Selecting Multiple Fields
```typescript
const { field1, field2, field3 } = useStore(
  (state) => ({
    field1: state.field1,
    field2: state.field2,
    field3: state.field3,
  }),
  shallow
)
```

#### Pattern 2: Selecting Single Field (No shallow needed)
```typescript
const field1 = useStore((state) => state.field1)
```

#### Pattern 3: Selecting Actions Only (No shallow needed - actions don't change)
```typescript
const setField1 = useStore((state) => state.setField1)
```

### Audit Checklist

When reviewing components that use Zustand stores:

1. ✅ Does it use a selector function `useStore((state) => ...)`?
2. ✅ If selecting multiple fields, does it use `shallow`?
3. ✅ If selecting a single field, is `shallow` omitted?
4. ✅ Are selectors as specific as possible (only select what's needed)?

### Import Statement
```typescript
import { shallow } from 'zustand/shallow'
```

### Performance Impact

**Without shallow selectors:**
- Component re-renders on **every** store update (e.g., 100+ times during a chat session)

**With shallow selectors:**
- Component re-renders only when **selected fields** change (e.g., 5-10 times)

**Example**: A component displaying `isExecuting` would re-render when `sessionId`, `currentFile`, `currentQuery`, etc. change, even though it doesn't use those fields.

### Migration Strategy

1. Search for all `useStore()` calls without selectors
2. Identify which fields each component actually uses
3. Add shallow selectors for multi-field usage
4. Test that UI updates correctly

---

## Additional Optimization: Immer Middleware

For stores with deep nested objects, consider using Immer middleware:

```typescript
import { immer } from 'zustand/middleware/immer'

export const useComplexStore = create<Store>()(
  immer((set) => ({
    // ...
    updateNestedField: (value) => set((state) => {
      state.nested.deep.field = value  // Immer handles immutability
    })
  }))
)
```

This prevents accidental mutations and simplifies complex state updates.
