// API client for Jarvis backend
const API_BASE = 'http://localhost:8400';

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

export const api = {
  health: () => fetchAPI<HealthStatus>('/health'),
  chat: (message: string) =>
    fetchAPI<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
  command: (command: string) =>
    fetchAPI<ChatResponse>('/api/command', {
      method: 'POST',
      body: JSON.stringify({ command }),
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
};
