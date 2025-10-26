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

const API_BASE = 'http://localhost:8000/api/v1/workflow';

// ============================================
// WORKFLOW QUERIES
// ============================================

export function useWorkflows(category?: string) {
  return useQuery({
    queryKey: ['workflows', category],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (category) params.append('category', category);

      const res = await fetch(`${API_BASE}/workflows?${params}`);
      if (!res.ok) throw new Error('Failed to fetch workflows');
      return res.json() as Promise<Workflow[]>;
    },
  });
}

export function useWorkflow(workflowId: string) {
  return useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/workflows/${workflowId}`);
      if (!res.ok) throw new Error('Failed to fetch workflow');
      return res.json() as Promise<Workflow>;
    },
    enabled: !!workflowId,
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

      const res = await fetch(`${API_BASE}/work-items?${params}`);
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
      const res = await fetch(`${API_BASE}/work-items/${workItemId}`);
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

      const res = await fetch(`${API_BASE}/queues/${workflowId}/role/${roleName}?${params}`);
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
      const res = await fetch(`${API_BASE}/my-work/${userId}`);
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
      const res = await fetch(`${API_BASE}/overdue`);
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
      const res = await fetch(`${API_BASE}/statistics/${workflowId}`);
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
