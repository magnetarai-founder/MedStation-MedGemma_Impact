/**
 * OmniStudio History API Client
 * Replaces localStorage with SQLite backend for query history
 */

const API_BASE = 'http://localhost:8000/api';

export interface HistoryItem {
  id: number;
  query: string;
  query_type: 'sql' | 'json';
  execution_time?: number;
  row_count?: number;
  success: boolean;
  error_message?: string;
  timestamp: string;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AddHistoryRequest {
  query: string;
  query_type: 'sql' | 'json';
  execution_time?: number;
  row_count?: number;
  success?: boolean;
  error_message?: string;
  file_context?: string;
}

/**
 * Add a query to history
 */
export async function addToHistory(request: AddHistoryRequest): Promise<number> {
  const response = await fetch(`${API_BASE}/history`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to add to history: ${response.statusText}`);
  }

  const data = await response.json();
  return data.id;
}

/**
 * Get query history with pagination
 */
export async function getHistory(params: {
  query_type?: 'sql' | 'json';
  limit?: number;
  offset?: number;
  date_filter?: 'all' | 'today' | 'week';
}): Promise<HistoryResponse> {
  const searchParams = new URLSearchParams();

  if (params.query_type) searchParams.append('query_type', params.query_type);
  if (params.limit) searchParams.append('limit', params.limit.toString());
  if (params.offset) searchParams.append('offset', params.offset.toString());
  if (params.date_filter && params.date_filter !== 'all') {
    searchParams.append('date_filter', params.date_filter);
  }

  const response = await fetch(`${API_BASE}/history?${searchParams}`);

  if (!response.ok) {
    throw new Error(`Failed to get history: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a specific history item
 */
export async function deleteHistoryItem(id: number): Promise<boolean> {
  const response = await fetch(`${API_BASE}/history/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to delete history item: ${response.statusText}`);
  }

  const data = await response.json();
  return data.success;
}

/**
 * Clear all history or filtered history
 */
export async function clearHistory(params?: {
  query_type?: 'sql' | 'json';
  before_date?: string;
}): Promise<number> {
  const searchParams = new URLSearchParams();

  if (params?.query_type) searchParams.append('query_type', params.query_type);
  if (params?.before_date) searchParams.append('before_date', params.before_date);

  const response = await fetch(`${API_BASE}/history?${searchParams}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`Failed to clear history: ${response.statusText}`);
  }

  const data = await response.json();
  return data.deleted_count;
}

/**
 * Search for similar queries
 */
export async function searchSimilarQueries(params: {
  query: string;
  query_type?: 'sql' | 'json';
  limit?: number;
}): Promise<HistoryItem[]> {
  const searchParams = new URLSearchParams();
  searchParams.append('query', params.query);

  if (params.query_type) searchParams.append('query_type', params.query_type);
  if (params.limit) searchParams.append('limit', params.limit.toString());

  const response = await fetch(`${API_BASE}/history/search?${searchParams}`);

  if (!response.ok) {
    throw new Error(`Failed to search history: ${response.statusText}`);
  }

  const data = await response.json();
  return data.results;
}
