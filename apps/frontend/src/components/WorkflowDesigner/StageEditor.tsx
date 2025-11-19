/**
 * StageEditor Component
 * Multi-tab editor for workflow stage configuration
 */

import React, { useState } from 'react';
import { Settings, Trash2, FileText, GitBranch } from 'lucide-react';
import type {
  Stage,
  StageType,
  AssignmentType,
} from '../../types/workflow';
import { FormBuilder } from '../FormBuilder';
import { RoutingEditor } from '../RoutingEditor';

interface StageEditorProps {
  stage: Stage;
  allStages: Stage[];
  onUpdate: (updates: Partial<Stage>) => void;
  onDelete: () => void;
  onAddRoute: (toStageId: string) => void;
  onRemoveRoute: (routeId: string) => void;
}

export function StageEditor({ stage, allStages, onUpdate, onDelete, onAddRoute, onRemoveRoute }: StageEditorProps) {
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
