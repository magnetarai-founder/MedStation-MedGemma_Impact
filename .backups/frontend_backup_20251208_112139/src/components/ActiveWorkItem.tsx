/**
 * ActiveWorkItem Component
 * Detail view for working on a claimed work item
 */

import React, { useState } from 'react';
import { useWorkItem, useWorkflow, useCompleteStage, useCancelWorkItem } from '../hooks/useWorkflowQueue';
import type { WorkItem, Stage } from '../types/workflow';
import { AgentAssistPanel } from './WorkItem/AgentAssistPanel';
import VisibilityBadge from './Automation/components/VisibilityBadge';

interface ActiveWorkItemProps {
  workItemId: string;
  userId: string;
  onClose?: () => void;
  onCompleted?: () => void;
}

export function ActiveWorkItem({ workItemId, userId, onClose, onCompleted }: ActiveWorkItemProps) {
  const { data: workItem, isLoading: loadingWorkItem, refetch } = useWorkItem(workItemId);
  const { data: workflow } = useWorkflow(workItem?.workflow_id || '');

  const [formData, setFormData] = useState<Record<string, any>>({});
  const [notes, setNotes] = useState('');

  const completeMutation = useCompleteStage();
  const cancelMutation = useCancelWorkItem();

  const currentStage = workflow?.stages.find(s => s.id === workItem?.current_stage_id);

  const handleComplete = async () => {
    if (!workItem || !currentStage) return;

    try {
      await completeMutation.mutateAsync({
        work_item_id: workItem.id,
        stage_id: currentStage.id,
        data: formData,
        notes: notes || undefined,
        userId,
      });

      if (onCompleted) onCompleted();
      if (onClose) onClose();
    } catch (error) {
      console.error('Failed to complete stage:', error);
      alert(error instanceof Error ? error.message : 'Failed to complete stage');
    }
  };

  const handleCancel = async () => {
    if (!workItem) return;

    const reason = prompt('Reason for cancellation:');
    if (!reason) return;

    try {
      await cancelMutation.mutateAsync({
        workItemId: workItem.id,
        userId,
        reason,
      });

      if (onClose) onClose();
    } catch (error) {
      console.error('Failed to cancel work item:', error);
      alert(error instanceof Error ? error.message : 'Failed to cancel work item');
    }
  };

  if (loadingWorkItem || !workItem) {
    return (
      <div className="flex items-center justify-center h-full bg-[#0a0a0a] text-white">
        <div>Loading work item...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            ← Back
          </button>
          <div>
            <h2 className="text-xl font-semibold">
              {workItem.reference_number || `Work Item ${workItem.id.slice(0, 8)}`}
            </h2>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span>{workItem.workflow_name} • {workItem.current_stage_name}</span>
              {/* T3-2: Show inherited workflow visibility */}
              {workflow?.visibility && (
                <VisibilityBadge
                  visibility={workflow.visibility}
                  showIcon={true}
                  showTooltip={false}
                  className="ml-2"
                />
              )}
            </div>
            {/* T3-2: Explanatory text for workflow visibility */}
            {workflow?.visibility && (
              <div className="text-xs text-gray-500 mt-1">
                {workflow.visibility === 'personal' &&
                  'Visible only to you. Work items in this workflow are private.'}
                {workflow.visibility === 'team' &&
                  'Visible to your team. Work items in this workflow are shared within your team.'}
                {workflow.visibility === 'global' &&
                  'Visible to all users with workflow access.'}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded text-sm ${
            workItem.priority === 'urgent'
              ? 'bg-red-900 text-red-200'
              : workItem.priority === 'high'
              ? 'bg-orange-900 text-orange-200'
              : 'bg-blue-900 text-blue-200'
          }`}>
            {workItem.priority}
          </span>
          <span className={`px-3 py-1 rounded text-sm ${
            workItem.status === 'in_progress'
              ? 'bg-blue-900 text-blue-200'
              : 'bg-gray-800 text-gray-300'
          }`}>
            {workItem.status.replace('_', ' ')}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Current Data */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <span>📊</span> Current Data
            </h3>
            <div className="space-y-2">
              {Object.entries(workItem.data).map(([key, value]) => (
                <div key={key} className="flex items-start gap-3">
                  <span className="text-gray-400 min-w-[120px]">{key}:</span>
                  <span className="text-white">{JSON.stringify(value)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Agent Assist Panel - Show for AGENT_ASSIST stages */}
          {currentStage && (
            <AgentAssistPanel
              workItem={workItem}
              stage={currentStage}
              onRefresh={() => refetch()}
            />
          )}

          {/* Stage Form */}
          {currentStage?.form && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <span>📝</span> {currentStage.form.name}
              </h3>
              {currentStage.form.description && (
                <p className="text-sm text-gray-400 mb-4">{currentStage.form.description}</p>
              )}

              <div className="space-y-4">
                {currentStage.form.fields.map((field) => (
                  <div key={field.id}>
                    <label className="block text-sm font-medium mb-2">
                      {field.label}
                      {field.required && <span className="text-red-400 ml-1">*</span>}
                    </label>

                    {field.help_text && (
                      <p className="text-xs text-gray-400 mb-2">{field.help_text}</p>
                    )}

                    {/* Text Input */}
                    {field.type === 'text' && (
                      <input
                        type="text"
                        value={formData[field.name] || ''}
                        onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
                        placeholder={field.placeholder}
                        required={field.required}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                      />
                    )}

                    {/* Textarea */}
                    {field.type === 'textarea' && (
                      <textarea
                        value={formData[field.name] || ''}
                        onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
                        placeholder={field.placeholder}
                        required={field.required}
                        rows={4}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                      />
                    )}

                    {/* Number Input */}
                    {field.type === 'number' && (
                      <input
                        type="number"
                        value={formData[field.name] || ''}
                        onChange={(e) => setFormData({ ...formData, [field.name]: parseFloat(e.target.value) })}
                        placeholder={field.placeholder}
                        required={field.required}
                        min={field.min_value}
                        max={field.max_value}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                      />
                    )}

                    {/* Select */}
                    {field.type === 'select' && field.options && (
                      <select
                        value={formData[field.name] || ''}
                        onChange={(e) => setFormData({ ...formData, [field.name]: e.target.value })}
                        required={field.required}
                        className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                      >
                        <option value="">Select...</option>
                        {field.options.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    )}

                    {/* Checkbox */}
                    {field.type === 'checkbox' && (
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={formData[field.name] || false}
                          onChange={(e) => setFormData({ ...formData, [field.name]: e.target.checked })}
                          className="w-4 h-4"
                        />
                        <span className="text-sm">{field.label}</span>
                      </label>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notes */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <span>💬</span> Notes (Optional)
            </h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any notes about this work..."
              rows={3}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* History */}
          {workItem.history.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <span>📜</span> History
              </h3>
              <div className="space-y-3">
                {workItem.history.map((transition, idx) => (
                  <div key={idx} className="flex items-start gap-3 text-sm">
                    <span className="text-gray-500">{new Date(transition.transitioned_at).toLocaleString()}</span>
                    <div className="text-gray-300">
                      {transition.from_stage_id ? 'Transitioned' : 'Created'}
                      {transition.notes && (
                        <span className="text-gray-400 ml-2">- {transition.notes}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="flex items-center justify-between p-4 border-t border-gray-800 bg-gray-900">
        <button
          onClick={handleCancel}
          disabled={cancelMutation.isPending}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {cancelMutation.isPending ? 'Cancelling...' : '❌ Cancel Work Item'}
        </button>

        <button
          onClick={handleComplete}
          disabled={completeMutation.isPending}
          className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
        >
          {completeMutation.isPending ? 'Completing...' : '✅ Complete Stage'}
        </button>
      </div>
    </div>
  );
}
