/**
 * WorkflowDesigner Component
 * Visual workflow builder - create workflows from scratch
 */

import React, { useState } from 'react';
import { Plus, Save, Settings, Trash2, FileText, GitBranch, Loader2, X } from 'lucide-react';
import type {
  Workflow,
  Stage,
  StageType,
  AssignmentType,
  WorkflowTriggerType,
  ConditionalRoute,
  FormDefinition,
} from '../types/workflow';
import { FormBuilder } from './FormBuilder';
import { RoutingEditor } from './RoutingEditor';
import { useCreateWorkflow } from '../hooks/useWorkflowQueue';

interface WorkflowDesignerProps {
  workflowId?: string; // For editing existing workflow
  onSave?: (workflow: Workflow) => void;
  onCancel?: () => void;
}

export function WorkflowDesigner({ workflowId, onSave, onCancel }: WorkflowDesignerProps) {
  const [workflowName, setWorkflowName] = useState('New Workflow');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [workflowIcon, setWorkflowIcon] = useState('⚡');
  const [workflowCategory, setWorkflowCategory] = useState('');

  const [stages, setStages] = useState<Stage[]>([]);
  const [selectedStage, setSelectedStage] = useState<Stage | null>(null);
  const [editingStageId, setEditingStageId] = useState<string | null>(null);

  const [triggers, setTriggers] = useState<{ trigger_type: WorkflowTriggerType; enabled: boolean }[]>([
    { trigger_type: 'manual', enabled: true },
  ]);

  const createWorkflowMutation = useCreateWorkflow();

  // ============================================
  // STAGE MANAGEMENT
  // ============================================

  const addStage = () => {
    const newStage: Stage = {
      id: `stage_${Date.now()}`,
      name: `Stage ${stages.length + 1}`,
      description: '',
      stage_type: 'human',
      assignment_type: 'role',
      order: stages.length,
      next_stages: [],
    };

    setStages([...stages, newStage]);
    setSelectedStage(newStage);
    setEditingStageId(newStage.id);
  };

  const updateStage = (stageId: string, updates: Partial<Stage>) => {
    setStages(prev => prev.map(s =>
      s.id === stageId ? { ...s, ...updates } : s
    ));

    if (selectedStage?.id === stageId) {
      setSelectedStage({ ...selectedStage, ...updates });
    }
  };

  const deleteStage = (stageId: string) => {
    setStages(prev => prev.filter(s => s.id !== stageId));

    // Remove references from other stages' next_stages
    setStages(prev => prev.map(s => ({
      ...s,
      next_stages: s.next_stages.filter(r => r.next_stage_id !== stageId),
    })));

    if (selectedStage?.id === stageId) {
      setSelectedStage(null);
      setEditingStageId(null);
    }
  };

  const moveStage = (stageId: string, direction: 'up' | 'down') => {
    const index = stages.findIndex(s => s.id === stageId);
    if (index === -1) return;

    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === stages.length - 1) return;

    const newStages = [...stages];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;

    [newStages[index], newStages[targetIndex]] = [newStages[targetIndex], newStages[index]];

    // Update order
    newStages.forEach((stage, idx) => {
      stage.order = idx;
    });

    setStages(newStages);
  };

  // ============================================
  // ROUTING MANAGEMENT
  // ============================================

  const addRoute = (fromStageId: string, toStageId: string) => {
    setStages(prev => prev.map(s => {
      if (s.id === fromStageId) {
        const route: ConditionalRoute = {
          id: `route_${Date.now()}`,
          next_stage_id: toStageId,
          conditions: null,
          description: 'Default route',
        };

        return {
          ...s,
          next_stages: [...s.next_stages, route],
        };
      }
      return s;
    }));
  };

  const removeRoute = (stageId: string, routeId: string) => {
    setStages(prev => prev.map(s => {
      if (s.id === stageId) {
        return {
          ...s,
          next_stages: s.next_stages.filter(r => r.id !== routeId),
        };
      }
      return s;
    }));
  };

  // ============================================
  // SAVE WORKFLOW
  // ============================================

  const handleSave = async () => {
    // Validation
    if (!workflowName.trim()) {
      alert('Workflow name is required');
      return;
    }

    if (stages.length === 0) {
      alert('Workflow must have at least one stage');
      return;
    }

    // Check that all stages have names
    const invalidStages = stages.filter(s => !s.name.trim());
    if (invalidStages.length > 0) {
      alert('All stages must have names');
      return;
    }

    try {
      const workflowData = {
        name: workflowName,
        description: workflowDescription,
        icon: workflowIcon,
        category: workflowCategory,
        stages,
        triggers: triggers.map(t => ({
          id: `trigger_${Date.now()}`,
          trigger_type: t.trigger_type,
          enabled: t.enabled,
        })),
        created_by: 'system', // TODO: Get from auth context
      };

      const savedWorkflow = await createWorkflowMutation.mutateAsync(workflowData);

      if (onSave) {
        onSave(savedWorkflow);
      } else {
        // Show success message
        alert(`Workflow "${savedWorkflow.name}" created successfully!`);
        if (onCancel) onCancel();
      }
    } catch (error) {
      console.error('Failed to save workflow:', error);
      alert(`Failed to save workflow: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // ============================================
  // RENDER
  // ============================================

  return (
    <div className="flex h-full bg-[#0a0a0a] text-white">
      {/* Left Sidebar - Workflow Properties */}
      <div className="w-80 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Workflow Properties</h2>
            {onCancel && (
              <button
                onClick={onCancel}
                className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                title="Close workflow designer"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Icon</label>
              <input
                type="text"
                value={workflowIcon}
                onChange={(e) => setWorkflowIcon(e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-2xl text-center"
                maxLength={2}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input
                type="text"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                placeholder="Workflow name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                value={workflowDescription}
                onChange={(e) => setWorkflowDescription(e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                placeholder="What does this workflow do?"
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Category</label>
              <input
                type="text"
                value={workflowCategory}
                onChange={(e) => setWorkflowCategory(e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                placeholder="e.g., Healthcare, Legal, Ministry"
              />
            </div>
          </div>
        </div>

        <div className="p-4 border-b border-gray-800">
          <h3 className="text-sm font-semibold mb-3">Triggers</h3>
          <div className="space-y-2">
            {(['manual', 'form', 'schedule', 'webhook'] as WorkflowTriggerType[]).map(type => (
              <label key={type} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={triggers.some(t => t.trigger_type === type && t.enabled)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setTriggers([...triggers, { trigger_type: type, enabled: true }]);
                    } else {
                      setTriggers(triggers.filter(t => t.trigger_type !== type));
                    }
                  }}
                  className="w-4 h-4"
                />
                <span className="text-sm capitalize">{type}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="flex-1 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">Stages ({stages.length})</h3>
            <button
              onClick={addStage}
              className="p-1 hover:bg-gray-800 rounded"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-2">
            {stages.map((stage, index) => (
              <div
                key={stage.id}
                onClick={() => {
                  setSelectedStage(stage);
                  setEditingStageId(stage.id);
                }}
                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedStage?.id === stage.id
                    ? 'bg-blue-900 border-blue-600'
                    : 'bg-gray-900 border-gray-700 hover:border-gray-600'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="font-medium text-sm">{stage.name}</div>
                    <div className="text-xs text-gray-400 mt-1">
                      {stage.stage_type} • {stage.assignment_type}
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {index > 0 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          moveStage(stage.id, 'up');
                        }}
                        className="p-1 hover:bg-gray-700 rounded text-xs"
                      >
                        ↑
                      </button>
                    )}
                    {index < stages.length - 1 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          moveStage(stage.id, 'down');
                        }}
                        className="p-1 hover:bg-gray-700 rounded text-xs"
                      >
                        ↓
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-gray-800 flex gap-2">
          <button
            onClick={onCancel}
            disabled={createWorkflowMutation.isPending}
            className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={createWorkflowMutation.isPending}
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {createWorkflowMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Canvas - Stage Editor */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden min-w-0">
        {selectedStage ? (
          <StageEditor
            stage={selectedStage}
            allStages={stages}
            onUpdate={(updates) => updateStage(selectedStage.id, updates)}
            onDelete={() => deleteStage(selectedStage.id)}
            onAddRoute={(toStageId) => addRoute(selectedStage.id, toStageId)}
            onRemoveRoute={(routeId) => removeRoute(selectedStage.id, routeId)}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Settings className="w-16 h-16 mb-4 opacity-20" />
            <div className="text-lg font-medium">No Stage Selected</div>
            <div className="text-sm mt-2">Add a stage to get started</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// STAGE EDITOR COMPONENT
// ============================================

interface StageEditorProps {
  stage: Stage;
  allStages: Stage[];
  onUpdate: (updates: Partial<Stage>) => void;
  onDelete: () => void;
  onAddRoute: (toStageId: string) => void;
  onRemoveRoute: (routeId: string) => void;
}

function StageEditor({ stage, allStages, onUpdate, onDelete, onAddRoute, onRemoveRoute }: StageEditorProps) {
  const [activeTab, setActiveTab] = useState<'basic' | 'form' | 'routing'>('basic');

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Edit Stage: {stage.name}</h2>
          <button
            onClick={onDelete}
            className="p-2 text-red-400 hover:bg-red-900/20 rounded-lg transition-colors"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('basic')}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
              activeTab === 'basic'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <Settings className="w-4 h-4" />
            Basic Info
          </button>
          <button
            onClick={() => setActiveTab('form')}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
              activeTab === 'form'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <FileText className="w-4 h-4" />
            Form Builder
          </button>
          <button
            onClick={() => setActiveTab('routing')}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
              activeTab === 'routing'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <GitBranch className="w-4 h-4" />
            Routing
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        {activeTab === 'basic' && (
          <div className="p-6 max-w-4xl mx-auto w-full">
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h3 className="font-semibold mb-4">Basic Information</h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Stage Name</label>
                  <input
                    type="text"
                    value={stage.name}
                    onChange={(e) => onUpdate({ name: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea
                    value={stage.description || ''}
                    onChange={(e) => onUpdate({ description: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Stage Type</label>
                    <select
                      value={stage.stage_type}
                      onChange={(e) => onUpdate({ stage_type: e.target.value as StageType })}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                    >
                      <option value="human">Human</option>
                      <option value="automation">Automation</option>
                      <option value="ai">AI</option>
                      <option value="hybrid">Hybrid</option>
                      <option value="approval">Approval</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Assignment</label>
                    <select
                      value={stage.assignment_type}
                      onChange={(e) => onUpdate({ assignment_type: e.target.value as AssignmentType })}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                    >
                      <option value="role">Role-Based</option>
                      <option value="user">Specific User</option>
                      <option value="queue">Queue</option>
                      <option value="automation">Automation</option>
                      <option value="round_robin">Round Robin</option>
                    </select>
                  </div>
                </div>

                {stage.assignment_type === 'role' && (
                  <div>
                    <label className="block text-sm font-medium mb-1">Role Name</label>
                    <input
                      type="text"
                      value={stage.role_name || ''}
                      onChange={(e) => onUpdate({ role_name: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                      placeholder="e.g., nurse, doctor, admin"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-1">SLA (minutes)</label>
                  <input
                    type="number"
                    value={stage.sla_minutes || ''}
                    onChange={(e) => onUpdate({ sla_minutes: parseInt(e.target.value) || undefined })}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none"
                    placeholder="Optional time limit"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'form' && (
          <FormBuilder
            form={stage.form || null}
            onUpdate={(form) => onUpdate({ form })}
          />
        )}

        {activeTab === 'routing' && (
          <div className="p-6 max-w-4xl">
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <RoutingEditor
                currentStage={stage}
                allStages={allStages}
                onUpdate={(routes) => onUpdate({ next_stages: routes })}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
