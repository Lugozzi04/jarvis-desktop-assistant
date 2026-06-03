// API client for Jarvis backend.
// Uses relative URLs when loaded from the backend (desktop app / SPA),
// falls back to localhost:8400 when running standalone dev server.
const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? window.location.origin
  : 'http://localhost:8400';

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json();
}

export interface HealthStatus {
  status: string;
  version: string;
  env: string;
  skills: string[];
  llm: {
    provider: string;
    available: boolean;
    model: string;
    allow_cloud: boolean;
    providers: Record<string, { configured: boolean }>;
  };
}

export interface ChatResponse {
  response: string;
  intent: { kind: string; skill: string; action: string; confidence: number } | null;
  result: {
    success: boolean;
    skill: string;
    action: string;
    risk: string;
    result: string;
    error: string | null;
  } | null;
  needs_confirmation: boolean;
  confirmation_message: string;
  duration_ms: number;
}

export interface SkillInfo {
  name: string;
  display_name: string;
  description: string;
  version: string;
  enabled: boolean;
  actions: string[];
}

export interface SkillDetail {
  name: string;
  display_name: string;
  description: string;
  version: string;
  enabled: boolean;
  actions: { name: string; description: string; parameters: Record<string, string>; risk: string }[];
}

export interface LogEntry {
  id: number;
  timestamp: string;
  input_raw: string;
  intent_kind: string;
  skill: string;
  action: string;
  risk: string;
  result_success: boolean;
  result_summary: string;
  error: string | null;
  duration_ms: number;
}

export interface SettingsInfo {
  env: string;
  log_level: string;
  llm: {
    default_provider: string;
    default_model: string;
    allow_cloud: boolean;
    has_api_key: boolean;
  };
}

export interface LLMStatus {
  provider: string;
  available: boolean;
  model: string;
  allow_cloud: boolean;
  providers: Record<string, { configured: boolean }>;
}

export interface LLMTestResult {
  success: boolean;
  provider: string;
  available: boolean;
  test_response?: string;
  error?: string;
}

// ── Document Memory ──

export interface PendingAction {
  id: string;
  skill: string;
  action: string;
  risk: string;
  reason: string;
  parameters: Record<string, unknown>;
  created_at: string;
  status: string; // pending | approved | rejected | executed | failed | expired
  resolved_at: string | null;
  reject_reason: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  source: string;
  timeout_minutes: number;
}

export interface PendingActionsResponse {
  actions: PendingAction[];
  count: number;
}

export interface DocumentInfo {
  id: string;
  path: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
  error: string | null;
  metadata: Record<string, unknown>;
  chunk_count: number;
  created_at: string;
  indexed_at: string | null;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  token_count: number;
  metadata: Record<string, unknown>;
}

export interface SearchResult {
  document_id: string;
  filename: string;
  chunk_id: string;
  chunk_index: number;
  score: number;
  text_preview: string;
  metadata: Record<string, unknown>;
}

export interface RAGAnswer {
  question: string;
  answer: string;
  sources: SearchResult[];
  provider: string;
  error: string | null;
}

export interface MemoryStatus {
  documents: number;
  chunks: number;
  embedding_provider: string;
  ready: boolean;
  error: string | null;
}

export interface DocumentsListResponse {
  documents: DocumentInfo[];
  count: number;
}

export interface DocumentDetailResponse {
  document: DocumentInfo;
  chunks: DocumentChunk[];
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  count: number;
}

export interface IndexFolderResponse {
  documents: DocumentInfo[];
  total: number;
  indexed: number;
  failed: number;
}

export interface HealthFullResponse {
  timestamp: string;
  backend: { online: boolean; version: string; skills_loaded: number; initialized: boolean };
  llm: { provider: string; available: boolean; model: string; error?: string };
  documents: { ready: boolean; documents: number; chunks: number; embedding_provider: string; provider_available?: boolean; error?: string };
  voice: { available: boolean; stt: string; tts: string };
  automations: { scheduler_running: boolean; automations_loaded: number };
  workflows: { workflows_loaded: number };
  skills: { loaded: string[] };
  pending_actions: { count: number; queue_enabled: boolean };
  desktop: { electron: boolean; portable_mode: boolean };
  environment: { python: string; system: string; release: string; machine: string };
  warnings: string[];
  errors: string[];
  recommended_next_steps: string[];
}

export interface PendingCountResponse {
  count: number;
}

export const api = {
  health: () => fetchAPI<HealthStatus>('/health'),
  healthFull: () => fetchAPI<HealthFullResponse>('/api/health/full'),
  pendingActionsCount: () => fetchAPI<PendingCountResponse>('/api/pending-actions/count'),
  chat: (message: string, sessionId?: string) =>
    fetchAPI<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId || 'default' }),
    }),
  command: (command: string, sessionId?: string) =>
    fetchAPI<ChatResponse>('/api/command', {
      method: 'POST',
      body: JSON.stringify({ command, session_id: sessionId || 'default' }),
    }),
  skills: () => fetchAPI<{ skills: SkillInfo[] }>('/api/skills'),
  skillDetail: (name: string) => fetchAPI<SkillDetail>(`/api/skills/${name}`),
  logs: () => fetchAPI<{ logs: LogEntry[] }>('/api/logs'),
  settings: () => fetchAPI<SettingsInfo>('/api/settings'),
  llmStatus: () => fetchAPI<LLMStatus>('/api/llm/status'),
  testLLM: (provider: string, baseUrl: string, apiKey: string, model: string) =>
    fetchAPI<LLMTestResult>('/api/settings/llm/test', {
      method: 'POST',
      body: JSON.stringify({ provider, base_url: baseUrl, api_key: apiKey, model }),
    }),
  workflows: () => fetchAPI<{ workflows: unknown[] }>('/api/workflows'),
  automations: () => fetchAPI<{ automations: unknown[] }>('/api/automations'),
  automation: (id: string) => fetchAPI(`/api/automations/${id}`),
  createAutomation: (data: unknown) =>
    fetchAPI('/api/automations', { method: 'POST', body: JSON.stringify(data) }),
  updateAutomation: (id: string, data: unknown) =>
    fetchAPI(`/api/automations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAutomation: (id: string) =>
    fetchAPI(`/api/automations/${id}`, { method: 'DELETE' }),
  enableAutomation: (id: string) =>
    fetchAPI(`/api/automations/${id}/enable`, { method: 'POST' }),
  disableAutomation: (id: string) =>
    fetchAPI(`/api/automations/${id}/disable`, { method: 'POST' }),
  runAutomation: (id: string) =>
    fetchAPI(`/api/automations/${id}/run`, { method: 'POST' }),
  automationEngineStatus: () => fetchAPI('/api/automations/engine/status'),

  // Document Memory
  documentsList: (status?: string) =>
    fetchAPI<DocumentsListResponse>(`/api/documents${status ? `?status=${status}` : ''}`),
  documentsStatus: () => fetchAPI<MemoryStatus>('/api/documents/status'),
  documentDetail: (id: string) => fetchAPI<DocumentDetailResponse>(`/api/documents/${id}`),
  indexFile: (path: string) =>
    fetchAPI<{ document: DocumentInfo }>('/api/documents/index', {
      method: 'POST',
      body: JSON.stringify({ path }),
    }),
  indexFolder: (folderPath: string, recursive: boolean = true) =>
    fetchAPI<IndexFolderResponse>('/api/documents/index-folder', {
      method: 'POST',
      body: JSON.stringify({ folder_path: folderPath, recursive }),
    }),
  searchDocuments: (query: string, topK: number = 5) =>
    fetchAPI<SearchResponse>('/api/documents/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    }),
  askDocuments: (question: string, topK: number = 5) =>
    fetchAPI<RAGAnswer>('/api/documents/ask', {
      method: 'POST',
      body: JSON.stringify({ question, top_k: topK }),
    }),
  deleteDocument: (id: string) =>
    fetchAPI<{ deleted: string }>(`/api/documents/${id}`, { method: 'DELETE' }),
  clearDocuments: () =>
    fetchAPI<{ cleared: boolean }>('/api/documents/clear', { method: 'POST' }),

  // Pending Security Actions
  pendingActions: () => fetchAPI<PendingActionsResponse>('/api/pending-actions'),
  approvePendingAction: (id: string) =>
    fetchAPI<{ status: string; id: string }>(`/api/pending-actions/${id}/approve`, { method: 'POST' }),
  rejectPendingAction: (id: string, reason?: string) =>
    fetchAPI<{ status: string; id: string; reject_reason: string | null }>(
      `/api/pending-actions/${id}/reject`,
      { method: 'POST', body: JSON.stringify({ reason: reason ?? null }) },
    ),
  cleanupPendingActions: (retentionHours?: number) =>
    fetchAPI<{ status: string; removed: number; retention_hours: number }>(
      '/api/pending-actions/cleanup',
      { method: 'POST', body: JSON.stringify({ retention_hours: retentionHours ?? 1 }) },
    ),
};
