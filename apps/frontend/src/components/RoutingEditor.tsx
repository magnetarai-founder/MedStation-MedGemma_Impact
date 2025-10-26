/**
 * RoutingEditor Component
 * Configure conditional routing between workflow stages
 */

import React, { useState } from 'react';
import { Plus, Trash2, AlertCircle } from 'lucide-react';
import type { Stage, ConditionalRoute } from '../types/workflow';

interface RoutingEditorProps {
  currentStage: Stage;
  allStages: Stage[];
  onUpdate: (routes: ConditionalRoute[]) => void;
}

const OPERATORS = [
  { value: '==', label: 'Equals (==)', symbol: '==' },
  { value: '!=', label: 'Not Equals (!=)', symbol: '!=' },
  { value: '>', label: 'Greater Than (>)', symbol: '>' },
  { value: '<', label: 'Less Than (<)', symbol: '<' },
  { value: 'contains', label: 'Contains', symbol: 'contains' },
  { value: 'not_contains', label: 'Not Contains', symbol: '!contains' },
  { value: 'is_true', label: 'Is True', symbol: 'is_true' },
  { value: 'is_false', label: 'Is False', symbol: 'is_false' },
];

const LOGICAL_OPERATORS = [
  { value: 'AND', label: 'AND (all must match)' },
  { value: 'OR', label: 'OR (any can match)' },
];

export function RoutingEditor({ currentStage, allStages, onUpdate }: RoutingEditorProps) {
  const [expandedRoute, setExpandedRoute] = useState<string | null>(null);

  const routes = currentStage.next_stages || [];

  // Filter out current stage and earlier stages to prevent loops
  const availableNextStages = allStages.filter(
    (s) => s.order > currentStage.order && s.id !== currentStage.id
  );

  const addRoute = () => {
    if (availableNextStages.length === 0) {
      alert('No stages available to route to. Add more stages first.');
      return;
    }

    const newRoute: ConditionalRoute = {
      id: `route_${Date.now()}`,
      next_stage_id: availableNextStages[0].id,
      conditions: [],
    };

    onUpdate([...routes, newRoute]);
    setExpandedRoute(`route-${routes.length}`);
  };

  const updateRoute = (index: number, updates: Partial<ConditionalRoute>) => {
    const newRoutes = routes.map((r, idx) => (idx === index ? { ...r, ...updates } : r));
    onUpdate(newRoutes);
  };

  const deleteRoute = (index: number) => {
    const newRoutes = routes.filter((_, idx) => idx !== index);
    onUpdate(newRoutes);
    setExpandedRoute(null);
  };

  const addCondition = (routeIndex: number) => {
    const route = routes[routeIndex];
    const newConditions = [
      ...(route.conditions || []),
      {
        field: '',
        operator: '==',
        value: '',
      },
    ];

    updateRoute(routeIndex, { conditions: newConditions });
  };

  const updateCondition = (
    routeIndex: number,
    conditionIndex: number,
    updates: { field?: string; operator?: string; value?: any }
  ) => {
    const route = routes[routeIndex];
    const newConditions = (route.conditions || []).map((c, idx) =>
      idx === conditionIndex ? { ...c, ...updates } : c
    );

    updateRoute(routeIndex, { conditions: newConditions });
  };

  const deleteCondition = (routeIndex: number, conditionIndex: number) => {
    const route = routes[routeIndex];
    const newConditions = (route.conditions || []).filter(
      (_, idx) => idx !== conditionIndex
    );

    updateRoute(routeIndex, { conditions: newConditions });
  };

  const getStageNameById = (stageId: string): string => {
    const stage = allStages.find((s) => s.id === stageId);
    return stage?.name || 'Unknown Stage';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-medium">Stage Routing</h4>
          <p className="text-xs text-gray-400 mt-1">
            Define where work items go after completing this stage
          </p>
        </div>
        <button
          onClick={addRoute}
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors"
          disabled={availableNextStages.length === 0}
        >
          <Plus className="inline-block mr-1 h-4 w-4" />
          Add Route
        </button>
      </div>

      {routes.length === 0 ? (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 text-center">
          <AlertCircle className="h-8 w-8 text-gray-500 mx-auto mb-2" />
          <p className="text-gray-400 text-sm">
            No routes configured. This stage will complete the workflow.
          </p>
          {availableNextStages.length > 0 && (
            <button
              onClick={addRoute}
              className="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded transition-colors text-sm"
            >
              Add First Route
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {routes.map((route, routeIdx) => {
            const isExpanded = expandedRoute === `route-${routeIdx}`;
            const hasConditions = route.conditions && route.conditions.length > 0;

            return (
              <div
                key={routeIdx}
                className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden"
              >
                {/* Route Header */}
                <div
                  className="p-3 flex items-center justify-between cursor-pointer hover:bg-gray-750"
                  onClick={() =>
                    setExpandedRoute(isExpanded ? null : `route-${routeIdx}`)
                  }
                >
                  <div className="flex items-center gap-3 flex-1">
                    <span className="text-xl">
                      {hasConditions ? '🔀' : '➡️'}
                    </span>
                    <div className="flex-1">
                      <div className="font-medium">
                        → {getStageNameById(route.next_stage_id)}
                      </div>
                      <div className="text-xs text-gray-400">
                        {hasConditions
                          ? `${route.conditions?.length} condition(s)`
                          : 'No conditions'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteRoute(routeIdx);
                      }}
                      className="p-1 hover:bg-red-900 rounded text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Route Configuration (Expanded) */}
                {isExpanded && (
                  <div className="p-4 border-t border-gray-700 space-y-4">
                    {/* Next Stage Selection */}
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Next Stage
                      </label>
                      <select
                        value={route.next_stage_id}
                        onChange={(e) =>
                          updateRoute(routeIdx, { next_stage_id: e.target.value })
                        }
                        className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
                      >
                        {availableNextStages.map((stage) => (
                          <option key={stage.id} value={stage.id}>
                            {stage.name} (Order: {stage.order})
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Conditions */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-sm font-medium">
                          Conditions
                          <span className="text-gray-500 ml-2 text-xs">
                            (Leave empty for unconditional route)
                          </span>
                        </label>
                        <button
                          onClick={() => addCondition(routeIdx)}
                          className="text-xs text-blue-400 hover:text-blue-300"
                        >
                          <Plus className="inline-block h-3 w-3 mr-1" />
                          Add Condition
                        </button>
                      </div>

                      {route.conditions && route.conditions.length > 0 ? (
                        <div className="space-y-3">
                          {/* Condition List */}
                          {route.conditions.map((condition, condIdx) => (
                            <div
                              key={condIdx}
                              className="bg-gray-900 border border-gray-700 rounded p-3 space-y-2"
                            >
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-medium text-gray-400">
                                  Condition {condIdx + 1}
                                </span>
                                <button
                                  onClick={() => deleteCondition(routeIdx, condIdx)}
                                  className="text-red-400 hover:text-red-300"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              </div>

                              {/* Field */}
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">
                                  Field Name
                                </label>
                                <input
                                  type="text"
                                  value={condition.field}
                                  onChange={(e) =>
                                    updateCondition(routeIdx, condIdx, {
                                      field: e.target.value,
                                    })
                                  }
                                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
                                  placeholder="e.g., urgency, status, amount"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                  Field name from form data
                                </p>
                              </div>

                              {/* Operator */}
                              <div>
                                <label className="block text-xs text-gray-400 mb-1">
                                  Operator
                                </label>
                                <select
                                  value={condition.operator}
                                  onChange={(e) =>
                                    updateCondition(routeIdx, condIdx, {
                                      operator: e.target.value,
                                    })
                                  }
                                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
                                >
                                  {OPERATORS.map((op) => (
                                    <option key={op.value} value={op.value}>
                                      {op.label}
                                    </option>
                                  ))}
                                </select>
                              </div>

                              {/* Value (not shown for is_true/is_false) */}
                              {!['is_true', 'is_false'].includes(
                                condition.operator
                              ) && (
                                <div>
                                  <label className="block text-xs text-gray-400 mb-1">
                                    Value
                                  </label>
                                  <input
                                    type="text"
                                    value={
                                      typeof condition.value === 'object'
                                        ? JSON.stringify(condition.value)
                                        : condition.value
                                    }
                                    onChange={(e) => {
                                      let value: any = e.target.value;
                                      // Try to parse as JSON for arrays/objects
                                      try {
                                        if (
                                          value.startsWith('[') ||
                                          value.startsWith('{')
                                        ) {
                                          value = JSON.parse(value);
                                        }
                                      } catch {
                                        // Keep as string
                                      }
                                      updateCondition(routeIdx, condIdx, { value });
                                    }}
                                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
                                    placeholder="Comparison value"
                                  />
                                  <p className="text-xs text-gray-500 mt-1">
                                    Value to compare the field against
                                  </p>
                                </div>
                              )}

                              {/* Condition Preview */}
                              <div className="mt-2 p-2 bg-gray-800 rounded text-xs font-mono">
                                <span className="text-blue-300">
                                  {condition.field || '(field)'}
                                </span>{' '}
                                <span className="text-yellow-300">
                                  {
                                    OPERATORS.find(
                                      (op) => op.value === condition.operator
                                    )?.symbol
                                  }
                                </span>{' '}
                                {!['is_true', 'is_false'].includes(
                                  condition.operator
                                ) && (
                                  <span className="text-green-300">
                                    {typeof condition.value === 'object'
                                      ? JSON.stringify(condition.value)
                                      : `"${condition.value}"`}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-center text-gray-500 text-sm py-4 bg-gray-900 rounded border border-gray-700">
                          No conditions - route always applies
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Routing Info */}
      {routes.length > 0 && (
        <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-blue-400 mt-0.5" />
            <div className="text-xs text-blue-300">
              <p className="font-medium mb-1">Routing Logic:</p>
              <ul className="list-disc list-inside space-y-1 text-blue-200">
                <li>Routes are evaluated in order from top to bottom</li>
                <li>First route with matching conditions is taken</li>
                <li>Routes without conditions always match</li>
                <li>If no routes match, workflow completes</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
