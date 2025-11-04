/**
 * React Query hooks for Workflow Queue operations
 * Handles My Work, Active Work, and Queue management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  WorkItem,
  Workflow,
  WorkItemStatus,
  WorkItemPriority,
  CreateWorkItemRequest,
  CompleteStageRequest,
} from '../types/workflow';

// Use relative base so it works with any backend port and in production
const API_BASE = '/api/v1/workflow';

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ============================================
// WORKFLOW QUERIES
// ============================================

export function useWorkflows(filters?: { category?: string; workflow_type?: 'local' | 'team' }) {
  return useQuery({
    queryKey: ['workflows', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.category) params.append('category', filters.category);
      if (filters?.workflow_type) params.append('workflow_type', filters.workflow_type);

      const res = await fetch(`${API_BASE}/workflows?${params}` , { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch workflows');
      return res.json() as Promise<Workflow[]>;
    },
  });
}

export function useWorkflow(workflowId: string) {
  return useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/workflows/${workflowId}`, { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch workflow');
      return res.json() as Promise<Workflow>;
    },
    enabled: !!workflowId,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (workflow: Partial<Workflow> & { created_by: string }) => {
      const res = await fetch(`${API_BASE}/workflows?created_by=${workflow.created_by}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          name: workflow.name,
          description: workflow.description,
          icon: workflow.icon,
          category: workflow.category,
          workflow_type: workflow.workflow_type || 'team',
          stages: workflow.stages,
          triggers: workflow.triggers,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to create workflow');
      }

      return res.json() as Promise<Workflow>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });
}

// ============================================
// WORK ITEM QUERIES
// ============================================

export function useWorkItems(filters?: {
  workflowId?: string;
  status?: WorkItemStatus;
  assignedTo?: string;
  priority?: WorkItemPriority;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['workItems', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.workflowId) params.append('workflow_id', filters.workflowId);
      if (filters?.status) params.append('status', filters.status);
      if (filters?.assignedTo) params.append('assigned_to', filters.assignedTo);
      if (filters?.priority) params.append('priority', filters.priority);
      if (filters?.limit) params.append('limit', filters.limit.toString());

      const res = await fetch(`${API_BASE}/work-items?${params}`, { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch work items');
      return res.json() as Promise<WorkItem[]>;
    },
    refetchInterval: 5000, // Refresh every 5s for real-time feel
  });
}

export function useWorkItem(workItemId: string) {
  return useQuery({
    queryKey: ['workItem', workItemId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/work-items/${workItemId}`, { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch work item');
      return res.json() as Promise<WorkItem>;
    },
    enabled: !!workItemId,
    refetchInterval: 3000, // Refresh frequently for active work
  });
}

// ============================================
// QUEUE QUERIES
// ============================================

export function useQueueForRole(workflowId: string, roleName: string, stageId?: string) {
  return useQuery({
    queryKey: ['queue', workflowId, roleName, stageId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (stageId) params.append('stage_id', stageId);

      const res = await fetch(`${API_BASE}/queues/${workflowId}/role/${roleName}?${params}`, { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch queue');
      return res.json() as Promise<WorkItem[]>;
    },
    enabled: !!workflowId && !!roleName,
    refetchInterval: 5000, // Real-time queue updates
  });
}

export function useMyActiveWork(userId: string) {
  return useQuery({
    queryKey: ['myWork', userId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/my-work/${userId}`, { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch my work');
      return res.json() as Promise<WorkItem[]>;
    },
    enabled: !!userId,
    refetchInterval: 3000, // Frequent updates for active work
  });
}

export function useOverdueItems() {
  return useQuery({
    queryKey: ['overdueItems'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/overdue`, { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch overdue items');
      return res.json() as Promise<WorkItem[]>;
    },
    refetchInterval: 10000, // Check every 10s
  });
}

export function useWorkflowStatistics(workflowId: string) {
  return useQuery({
    queryKey: ['workflowStats', workflowId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/statistics/${workflowId}`, { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch statistics');
      return res.json();
    },
    enabled: !!workflowId,
    refetchInterval: 10000,
  });
}

// ============================================
// WORK ITEM MUTATIONS
// ============================================

export function useCreateWorkItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CreateWorkItemRequest & { createdBy: string }) => {
      const res = await fetch(`${API_BASE}/work-items?created_by=${request.createdBy}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          workflow_id: request.workflow_id,
          data: request.data,
          priority: request.priority,
          tags: request.tags,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to create work item');
      }

      return res.json() as Promise<WorkItem>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workItems'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
  });
}

export function useClaimWorkItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ workItemId, userId }: { workItemId: string; userId: string }) => {
      const res = await fetch(`${API_BASE}/work-items/${workItemId}/claim?user_id=${userId}`, {
        method: 'POST',
        headers: { ...authHeaders() },
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to claim work item');
      }

      return res.json() as Promise<WorkItem>;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workItem', variables.workItemId] });
      queryClient.invalidateQueries({ queryKey: ['myWork'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
  });
}

export function useStartWork() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ workItemId, userId }: { workItemId: string; userId: string }) => {
      const res = await fetch(`${API_BASE}/work-items/${workItemId}/start?user_id=${userId}`, {
        method: 'POST',
        headers: { ...authHeaders() },
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to start work');
      }

      return res.json() as Promise<WorkItem>;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workItem', variables.workItemId] });
      queryClient.invalidateQueries({ queryKey: ['myWork'] });
    },
  });
}

export function useCompleteStage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CompleteStageRequest & { userId: string }) => {
      const res = await fetch(`${API_BASE}/work-items/${request.work_item_id}/complete?user_id=${request.userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          work_item_id: request.work_item_id,
          stage_id: request.stage_id,
          data: request.data,
          next_stage_id: request.next_stage_id,
          notes: request.notes,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to complete stage');
      }

      return res.json() as Promise<WorkItem>;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workItem', variables.work_item_id] });
      queryClient.invalidateQueries({ queryKey: ['myWork'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['workflowStats'] });
    },
  });
}

export function useCancelWorkItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ workItemId, userId, reason }: {
      workItemId: string;
      userId: string;
      reason?: string;
    }) => {
      const params = new URLSearchParams({ user_id: userId });
      if (reason) params.append('reason', reason);

      const res = await fetch(`${API_BASE}/work-items/${workItemId}/cancel?${params}`, {
        method: 'POST',
        headers: { ...authHeaders() },
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to cancel work item');
      }

      return res.json() as Promise<WorkItem>;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workItem', variables.workItemId] });
      queryClient.invalidateQueries({ queryKey: ['myWork'] });
      queryClient.invalidateQueries({ queryKey: ['workItems'] });
    },
  });
}

// ============================================
// STARRING FUNCTIONALITY
// ============================================

export function useStarredWorkflows(workflow_type?: 'local' | 'team') {
  return useQuery({
    queryKey: ['starredWorkflows', workflow_type],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (workflow_type) params.append('workflow_type', workflow_type);

      const res = await fetch(`${API_BASE}/workflows/starred/list?${params}`, { headers: { ...authHeaders() } });
      if (!res.ok) throw new Error('Failed to fetch starred workflows');
      const data = await res.json();
      return data.starred_workflows as string[];
    },
  });
}

export function useStarWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (workflowId: string) => {
      const res = await fetch(`${API_BASE}/workflows/${workflowId}/star`, {
        method: 'POST',
        headers: { ...authHeaders() },
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to star workflow');
      }

      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['starredWorkflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });
}

export function useUnstarWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (workflowId: string) => {
      const res = await fetch(`${API_BASE}/workflows/${workflowId}/star`, {
        method: 'DELETE',
        headers: { ...authHeaders() },
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to unstar workflow');
      }

      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['starredWorkflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });
}
