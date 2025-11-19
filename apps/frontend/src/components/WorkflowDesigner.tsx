/**
 * WorkflowDesigner legacy entrypoint.
 *
 * The implementation has been moved to:
 *   - components/WorkflowDesigner/WorkflowDesigner.tsx
 *   - components/WorkflowDesigner/StageList.tsx
 *   - components/WorkflowDesigner/StageEditor.tsx
 *
 * This file re-exports the main component for backwards compatibility.
 */

export { WorkflowDesigner } from './WorkflowDesigner/WorkflowDesigner';
