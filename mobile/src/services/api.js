import axios from 'axios';

const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:3001';

const api = axios.create({ baseURL: API_URL, timeout: 15000 });

// ── Projects ──────────────────────────────────────────────────────────────────
export const listProjects = () =>
  api.get('/api/projects').then(r => r.data.projects);

export const createProject = ({ name, brief, provider, model }) =>
  api.post('/api/projects', { name, brief, provider, model }).then(r => r.data);

export const getProject = (id) =>
  api.get(`/api/projects/${id}`).then(r => r.data);

export const getAgentRuns = (id) =>
  api.get(`/api/projects/${id}/agents`).then(r => r.data.agents);

export const getArtifacts = (id) =>
  api.get(`/api/projects/${id}/artifacts`).then(r => r.data.artifacts);

export const pushToGitHub = (id) =>
  api.post(`/api/projects/${id}/push`).then(r => r.data);

// ── Models ────────────────────────────────────────────────────────────────────
export const listModels = () =>
  api.get('/api/models').then(r => r.data);

export const deleteModel = (model) =>
  api.delete('/api/models', { data: { model } }).then(r => r.data);

// ── WebSocket ─────────────────────────────────────────────────────────────────
export const WS_URL = (API_URL.replace(/^http/, 'ws'));

export function connectWS(projectId, onMessage, onClose) {
  const ws = new WebSocket(`${WS_URL}/ws/${projectId}`);
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  ws.onclose = onClose || (() => {});
  ws.onerror = (e) => console.warn('WS error', e);
  return ws;
}
