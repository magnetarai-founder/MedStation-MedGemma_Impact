/**
 * N8N Configuration Component
 * Allows users to configure n8n integration for workflow automation
 */

import React, { useState, useEffect } from 'react';
import { Zap, CheckCircle, XCircle, AlertCircle, ExternalLink, RefreshCw } from 'lucide-react';

interface N8NConfig {
  configured: boolean;
  enabled: boolean;
  base_url?: string;
}

interface N8NWorkflow {
  id: string;
  name: string;
  active: boolean;
  tags?: string[];
}

export function N8NConfig() {
  const [config, setConfig] = useState<N8NConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [workflows, setWorkflows] = useState<N8NWorkflow[]>([]);

  // Form state
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [enabled, setEnabled] = useState(true);

  // Fetch current config
  useEffect(() => {
    fetchConfig();
    fetchHealth();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/v1/n8n/config');
      const data = await response.json();
      setConfig(data);

      if (data.configured && data.base_url) {
        setBaseUrl(data.base_url);
        setEnabled(data.enabled);
      }

      setLoading(false);
    } catch (err) {
      setError('Failed to load n8n configuration');
      setLoading(false);
    }
  };

  const fetchHealth = async () => {
    try {
      const response = await fetch('/api/v1/n8n/health');
      const data = await response.json();
      setHealthStatus(data);
    } catch (err) {
      console.error('Failed to fetch health status:', err);
    }
  };

  const fetchWorkflows = async () => {
    try {
      const response = await fetch('/api/v1/n8n/workflows');
      if (response.ok) {
        const data = await response.json();
        setWorkflows(data.workflows || []);
      }
    } catch (err) {
      console.error('Failed to fetch workflows:', err);
    }
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    setSaving(true);

    try {
      const response = await fetch('/api/v1/n8n/configure', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          base_url: baseUrl,
          api_key: apiKey,
          enabled,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to configure n8n');
      }

      setSuccess('n8n integration configured successfully!');
      await fetchConfig();
      await fetchHealth();

      // Clear API key for security
      setApiKey('');

      // Fetch workflows after successful configuration
      if (enabled) {
        await fetchWorkflows();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setError(null);
    setSuccess(null);
    setTesting(true);

    try {
      const response = await fetch('/api/v1/n8n/health');
      const data = await response.json();
      setHealthStatus(data);

      if (data.status === 'healthy') {
        setSuccess(`Connection successful! Found ${data.n8n_workflows || 0} n8n workflows.`);
        await fetchWorkflows();
      } else if (data.status === 'not_configured') {
        setError('n8n is not configured yet');
      } else {
        setError(data.error || 'Connection test failed');
      }
    } catch (err: any) {
      setError('Failed to test connection');
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading n8n configuration...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6 text-purple-500" />
            n8n Integration
          </h2>
          <p className="text-gray-400 mt-1">
            Connect ElohimOS workflows with n8n for advanced automation
          </p>
        </div>
        {healthStatus && (
          <button
            onClick={fetchHealth}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            title="Refresh health status"
          >
            <RefreshCw className="h-5 w-5 text-gray-400" />
          </button>
        )}
      </div>

      {/* Health Status */}
      {healthStatus && (
        <div
          className={`p-4 rounded-lg border ${
            healthStatus.status === 'healthy'
              ? 'bg-green-900/20 border-green-800'
              : healthStatus.status === 'not_configured'
              ? 'bg-gray-800 border-gray-700'
              : 'bg-red-900/20 border-red-800'
          }`}
        >
          <div className="flex items-center gap-3">
            {healthStatus.status === 'healthy' ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : healthStatus.status === 'not_configured' ? (
              <AlertCircle className="h-5 w-5 text-gray-400" />
            ) : (
              <XCircle className="h-5 w-5 text-red-500" />
            )}
            <div className="flex-1">
              <div className="font-medium">
                {healthStatus.status === 'healthy' && 'Connected to n8n'}
                {healthStatus.status === 'not_configured' && 'Not Configured'}
                {healthStatus.status === 'unhealthy' && 'Connection Failed'}
              </div>
              {healthStatus.status === 'healthy' && (
                <div className="text-sm text-gray-400">
                  {healthStatus.n8n_workflows || 0} workflows available
                </div>
              )}
              {healthStatus.status === 'unhealthy' && (
                <div className="text-sm text-red-400">{healthStatus.error}</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error/Success Messages */}
      {error && (
        <div className="p-4 bg-red-900/20 border border-red-800 rounded-lg flex items-start gap-3">
          <XCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="text-red-300">{error}</div>
        </div>
      )}

      {success && (
        <div className="p-4 bg-green-900/20 border border-green-800 rounded-lg flex items-start gap-3">
          <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
          <div className="text-green-300">{success}</div>
        </div>
      )}

      {/* Configuration Form */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-6">
        <h3 className="text-lg font-semibold">Configuration</h3>

        {/* Base URL */}
        <div>
          <label className="block text-sm font-medium mb-2">
            n8n Base URL <span className="text-red-400">*</span>
          </label>
          <input
            type="url"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white"
            placeholder="https://n8n.example.com"
          />
          <p className="text-xs text-gray-500 mt-1">
            The base URL of your n8n instance (without trailing slash)
          </p>
        </div>

        {/* API Key */}
        <div>
          <label className="block text-sm font-medium mb-2">
            API Key <span className="text-red-400">*</span>
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white font-mono"
            placeholder="n8n_api_xxxxxxxxxxxxxxxx"
          />
          <p className="text-xs text-gray-500 mt-1">
            Your n8n API key (Settings → API in n8n)
          </p>
        </div>

        {/* Enabled Toggle */}
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="n8n-enabled"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="w-4 h-4 rounded"
          />
          <label htmlFor="n8n-enabled" className="text-sm">
            Enable n8n integration
          </label>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 border-t border-gray-800">
          <button
            onClick={handleSave}
            disabled={saving || !baseUrl || !apiKey}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg transition-colors"
          >
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>

          {config?.configured && (
            <button
              onClick={handleTest}
              disabled={testing}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
          )}

          {baseUrl && (
            <a
              href={baseUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors flex items-center gap-2"
            >
              Open n8n
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
      </div>

      {/* Available Workflows */}
      {workflows.length > 0 && (
        <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Available n8n Workflows</h3>
            <button
              onClick={fetchWorkflows}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              Refresh
            </button>
          </div>

          <div className="space-y-2">
            {workflows.map((workflow) => (
              <div
                key={workflow.id}
                className="p-3 bg-gray-800 rounded-lg flex items-center justify-between"
              >
                <div className="flex-1">
                  <div className="font-medium">{workflow.name}</div>
                  <div className="text-xs text-gray-500 font-mono">
                    ID: {workflow.id}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {workflow.tags && workflow.tags.length > 0 && (
                    <div className="flex gap-1">
                      {workflow.tags.slice(0, 3).map((tag, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-gray-700 rounded text-xs"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <div
                    className={`px-2 py-1 rounded text-xs ${
                      workflow.active
                        ? 'bg-green-900/30 text-green-400'
                        : 'bg-gray-700 text-gray-400'
                    }`}
                  >
                    {workflow.active ? 'Active' : 'Inactive'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documentation */}
      <div className="bg-gray-900 rounded-lg border border-gray-800 p-6 space-y-3">
        <h3 className="text-lg font-semibold">How it Works</h3>
        <div className="space-y-2 text-sm text-gray-400">
          <p>
            1. <strong className="text-white">Export Stages:</strong> Convert ElohimOS workflow
            stages into n8n workflows for complex automation.
          </p>
          <p>
            2. <strong className="text-white">Webhook Triggers:</strong> ElohimOS sends work items
            to n8n via webhooks, n8n processes them, and returns results.
          </p>
          <p>
            3. <strong className="text-white">Hybrid Workflows:</strong> Combine human review stages
            with automated n8n stages in the same workflow.
          </p>
          <p>
            4. <strong className="text-white">Bidirectional Sync:</strong> Changes in n8n workflows
            can be imported back into ElohimOS.
          </p>
        </div>
      </div>
    </div>
  );
}
