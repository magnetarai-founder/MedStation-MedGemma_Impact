/**
 * FormBuilder Component
 * Visual builder for creating data collection forms for workflow stages
 */

import React, { useState } from 'react';
import { Plus, Trash2, GripVertical, ChevronDown, ChevronUp } from 'lucide-react';
import type { FormDefinition, FormField } from '../types/workflow';

interface FormBuilderProps {
  form: FormDefinition | null;
  onUpdate: (form: FormDefinition) => void;
}

const FIELD_TYPES = [
  { value: 'text', label: 'Text Input', icon: '📝' },
  { value: 'textarea', label: 'Text Area', icon: '📄' },
  { value: 'number', label: 'Number', icon: '🔢' },
  { value: 'email', label: 'Email', icon: '📧' },
  { value: 'phone', label: 'Phone', icon: '📞' },
  { value: 'date', label: 'Date', icon: '📅' },
  { value: 'time', label: 'Time', icon: '⏰' },
  { value: 'datetime', label: 'Date & Time', icon: '📆' },
  { value: 'select', label: 'Dropdown', icon: '🔽' },
  { value: 'multiselect', label: 'Multi-Select', icon: '☑️' },
  { value: 'checkbox', label: 'Checkbox', icon: '✓' },
  { value: 'radio', label: 'Radio Buttons', icon: '⚪' },
  { value: 'file', label: 'File Upload', icon: '📎' },
];

export function FormBuilder({ form, onUpdate }: FormBuilderProps) {
  const [expandedField, setExpandedField] = useState<string | null>(null);

  const currentForm: FormDefinition = form || {
    id: `form_${Date.now()}`,
    name: 'New Form',
    fields: [],
    submit_button_text: 'Submit',
  };

  const addField = () => {
    const newField: FormField = {
      id: `field_${Date.now()}`,
      name: `field_${currentForm.fields.length + 1}`,
      label: 'New Field',
      type: 'text',
      required: false,
      order: currentForm.fields.length,
    };

    onUpdate({
      ...currentForm,
      fields: [...currentForm.fields, newField],
    });

    setExpandedField(newField.id);
  };

  const updateField = (fieldId: string, updates: Partial<FormField>) => {
    onUpdate({
      ...currentForm,
      fields: currentForm.fields.map((f) =>
        f.id === fieldId ? { ...f, ...updates } : f
      ),
    });
  };

  const deleteField = (fieldId: string) => {
    onUpdate({
      ...currentForm,
      fields: currentForm.fields
        .filter((f) => f.id !== fieldId)
        .map((f, idx) => ({ ...f, order: idx })),
    });
    setExpandedField(null);
  };

  const moveField = (fieldId: string, direction: 'up' | 'down') => {
    const currentIndex = currentForm.fields.findIndex((f) => f.id === fieldId);
    if (
      (direction === 'up' && currentIndex === 0) ||
      (direction === 'down' && currentIndex === currentForm.fields.length - 1)
    ) {
      return;
    }

    const newFields = [...currentForm.fields];
    const swapIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    [newFields[currentIndex], newFields[swapIndex]] = [
      newFields[swapIndex],
      newFields[currentIndex],
    ];

    // Update order
    newFields.forEach((f, idx) => {
      f.order = idx;
    });

    onUpdate({
      ...currentForm,
      fields: newFields,
    });
  };

  const addOption = (fieldId: string) => {
    const field = currentForm.fields.find((f) => f.id === fieldId);
    if (!field) return;

    const newOptions = [
      ...(field.options || []),
      { value: `option_${(field.options?.length || 0) + 1}`, label: 'New Option' },
    ];

    updateField(fieldId, { options: newOptions });
  };

  const updateOption = (
    fieldId: string,
    optionIndex: number,
    updates: { value?: string; label?: string }
  ) => {
    const field = currentForm.fields.find((f) => f.id === fieldId);
    if (!field || !field.options) return;

    const newOptions = field.options.map((opt, idx) =>
      idx === optionIndex ? { ...opt, ...updates } : opt
    );

    updateField(fieldId, { options: newOptions });
  };

  const deleteOption = (fieldId: string, optionIndex: number) => {
    const field = currentForm.fields.find((f) => f.id === fieldId);
    if (!field || !field.options) return;

    const newOptions = field.options.filter((_, idx) => idx !== optionIndex);
    updateField(fieldId, { options: newOptions });
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <h3 className="text-lg font-semibold mb-4">Form Builder</h3>

        {/* Form Name */}
        <div className="mb-3">
          <label className="block text-sm font-medium mb-1">Form Name</label>
          <input
            type="text"
            value={currentForm.name}
            onChange={(e) =>
              onUpdate({
                ...currentForm,
                name: e.target.value,
              })
            }
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
            placeholder="e.g., Patient Intake Form"
          />
        </div>

        {/* Form Description */}
        <div>
          <label className="block text-sm font-medium mb-1">Description (Optional)</label>
          <input
            type="text"
            value={currentForm.description || ''}
            onChange={(e) =>
              onUpdate({
                ...currentForm,
                description: e.target.value,
              })
            }
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
            placeholder="What is this form for?"
          />
        </div>
      </div>

      {/* Form Fields */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {currentForm.fields.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            <p className="mb-4">No form fields yet</p>
            <button
              onClick={addField}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Plus className="inline-block mr-2 h-4 w-4" />
              Add First Field
            </button>
          </div>
        ) : (
          currentForm.fields
            .sort((a, b) => a.order - b.order)
            .map((field) => {
              const isExpanded = expandedField === field.id;
              const fieldType = FIELD_TYPES.find((t) => t.value === field.type);

              return (
                <div
                  key={field.id}
                  className="bg-gray-900 rounded-lg border border-gray-800 overflow-hidden"
                >
                  {/* Field Header */}
                  <div
                    className="p-3 flex items-center justify-between cursor-pointer hover:bg-gray-850"
                    onClick={() =>
                      setExpandedField(isExpanded ? null : field.id)
                    }
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <GripVertical className="h-4 w-4 text-gray-500" />
                      <span className="text-lg">{fieldType?.icon}</span>
                      <div className="flex-1">
                        <div className="font-medium">{field.label}</div>
                        <div className="text-xs text-gray-500">
                          {fieldType?.label}
                          {field.required && (
                            <span className="ml-2 text-red-400">*Required</span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          moveField(field.id, 'up');
                        }}
                        disabled={field.order === 0}
                        className="p-1 hover:bg-gray-700 rounded disabled:opacity-30"
                      >
                        <ChevronUp className="h-4 w-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          moveField(field.id, 'down');
                        }}
                        disabled={field.order === currentForm.fields.length - 1}
                        className="p-1 hover:bg-gray-700 rounded disabled:opacity-30"
                      >
                        <ChevronDown className="h-4 w-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteField(field.id);
                        }}
                        className="p-1 hover:bg-red-900 rounded text-red-400"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Field Configuration (Expanded) */}
                  {isExpanded && (
                    <div className="p-4 border-t border-gray-800 space-y-4">
                      {/* Field Name */}
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Field Name (ID)
                        </label>
                        <input
                          type="text"
                          value={field.name}
                          onChange={(e) =>
                            updateField(field.id, { name: e.target.value })
                          }
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
                          placeholder="field_name"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Used in data storage (no spaces, lowercase)
                        </p>
                      </div>

                      {/* Field Label */}
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Label (Display Text)
                        </label>
                        <input
                          type="text"
                          value={field.label}
                          onChange={(e) =>
                            updateField(field.id, { label: e.target.value })
                          }
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
                          placeholder="What users see"
                        />
                      </div>

                      {/* Field Type */}
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Field Type
                        </label>
                        <select
                          value={field.type}
                          onChange={(e) =>
                            updateField(field.id, { type: e.target.value })
                          }
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
                        >
                          {FIELD_TYPES.map((type) => (
                            <option key={type.value} value={type.value}>
                              {type.icon} {type.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Placeholder */}
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Placeholder
                        </label>
                        <input
                          type="text"
                          value={field.placeholder || ''}
                          onChange={(e) =>
                            updateField(field.id, { placeholder: e.target.value })
                          }
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
                          placeholder="Enter placeholder text..."
                        />
                      </div>

                      {/* Default Value */}
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Default Value
                        </label>
                        <input
                          type="text"
                          value={field.default_value || ''}
                          onChange={(e) =>
                            updateField(field.id, { default_value: e.target.value })
                          }
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
                          placeholder="Default value..."
                        />
                      </div>

                      {/* Options (for select, multiselect, radio) */}
                      {['select', 'multiselect', 'radio'].includes(field.type) && (
                        <div>
                          <label className="block text-sm font-medium mb-2">
                            Options
                          </label>
                          <div className="space-y-2 mb-2">
                            {(field.options || []).map((option, idx) => (
                              <div key={idx} className="flex gap-2">
                                <input
                                  type="text"
                                  value={option.value}
                                  onChange={(e) =>
                                    updateOption(field.id, idx, {
                                      value: e.target.value,
                                    })
                                  }
                                  className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
                                  placeholder="Value"
                                />
                                <input
                                  type="text"
                                  value={option.label}
                                  onChange={(e) =>
                                    updateOption(field.id, idx, {
                                      label: e.target.value,
                                    })
                                  }
                                  className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
                                  placeholder="Label"
                                />
                                <button
                                  onClick={() => deleteOption(field.id, idx)}
                                  className="p-2 hover:bg-red-900 rounded text-red-400"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            ))}
                          </div>
                          <button
                            onClick={() => addOption(field.id)}
                            className="text-sm text-blue-400 hover:text-blue-300"
                          >
                            <Plus className="inline-block h-4 w-4 mr-1" />
                            Add Option
                          </button>
                        </div>
                      )}

                      {/* Required */}
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id={`required-${field.id}`}
                          checked={field.required}
                          onChange={(e) =>
                            updateField(field.id, { required: e.target.checked })
                          }
                          className="rounded"
                        />
                        <label
                          htmlFor={`required-${field.id}`}
                          className="text-sm"
                        >
                          Required field
                        </label>
                      </div>

                      {/* Validation */}
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Validation Rules
                        </label>
                        <textarea
                          value={
                            field.validation
                              ? JSON.stringify(field.validation, null, 2)
                              : ''
                          }
                          onChange={(e) => {
                            try {
                              const validation = JSON.parse(e.target.value);
                              updateField(field.id, { validation });
                            } catch {
                              // Invalid JSON, ignore
                            }
                          }}
                          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm font-mono"
                          placeholder='{"min": 0, "max": 100}'
                          rows={3}
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          JSON format (e.g., min/max for numbers, pattern for text)
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800 flex justify-between items-center">
        <div>
          <label className="block text-sm font-medium mb-1">
            Submit Button Text
          </label>
          <input
            type="text"
            value={currentForm.submit_button_text}
            onChange={(e) =>
              onUpdate({
                ...currentForm,
                submit_button_text: e.target.value,
              })
            }
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
            placeholder="Submit"
          />
        </div>
        {currentForm.fields.length > 0 && (
          <button
            onClick={addField}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <Plus className="inline-block mr-2 h-4 w-4" />
            Add Field
          </button>
        )}
      </div>
    </div>
  );
}
