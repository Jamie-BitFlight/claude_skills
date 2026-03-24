let _token: string | null = null;

export function setToken(token: string): void {
  _token = token;
  localStorage.setItem('dot-dash-token', token);
}

export function getToken(): string | null {
  if (_token) return _token;
  _token = localStorage.getItem('dot-dash-token');
  return _token;
}

async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers as HeadersInit | undefined);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(path, { ...options, headers });
}

export async function fetchSessions(): Promise<unknown> {
  const res = await apiFetch('/api/sessions');
  if (!res.ok) throw new Error(`Failed to fetch sessions: ${res.status}`);
  return res.json();
}

export async function deleteSession(id: string): Promise<unknown> {
  const res = await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete session: ${res.status}`);
  return res.json();
}

export async function injectPrompt(sessionId: string, message: string): Promise<unknown> {
  const res = await apiFetch(`/api/sessions/${sessionId}/inject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`Failed to inject prompt: ${res.status}`);
  return res.json();
}
