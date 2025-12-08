/**
 * StageList Component
 * Displays the list of workflow stages with add/move functionality
 */

import React from 'react';
import { Plus } from 'lucide-react';
import type { Stage } from '../../types/workflow';

interface StageListProps {
  stages: Stage[];
  selectedStageId: string | null;
  onSelectStage: (stageId: string) => void;
  onAddStage: () => void;
  onMoveStage: (stageId: string, direction: 'up' | 'down') => void;
}

export function StageList({
  stages,
  selectedStageId,
  onSelectStage,
  onAddStage,
  onMoveStage,
}: StageListProps) {
  return (
    <div className="flex-1 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">Stages ({stages.length})</h3>
        <button
          onClick={onAddStage}
          className="p-1 hover:bg-gray-800 rounded"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-2">
        {stages.map((stage, index) => (
          <div
            key={stage.id}
            onClick={() => onSelectStage(stage.id)}
            className={`p-3 rounded-lg border cursor-pointer transition-colors ${
              selectedStageId === stage.id
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
                      onMoveStage(stage.id, 'up');
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
                      onMoveStage(stage.id, 'down');
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
  );
}
