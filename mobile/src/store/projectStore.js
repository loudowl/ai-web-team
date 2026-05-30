import { create } from 'zustand';

const AGENTS = ['pm', 'designer', 'architect', 'developer'];

const AGENT_META = {
  pm:        { label: 'Project Manager', icon: '📋', color: '#58a6ff' },
  designer:  { label: 'Designer',        icon: '🎨', color: '#bc8cff' },
  architect: { label: 'Architect',       icon: '🏗️',  color: '#d29922' },
  developer: { label: 'Developer',       icon: '💻', color: '#3fb950' },
};

const initialAgentState = () =>
  Object.fromEntries(
    AGENTS.map(a => [a, { status: 'pending', output: '', chunks: [] }])
  );

export const useProjectStore = create((set, get) => ({
  // Projects list
  projects: [],
  setProjects: (projects) => set({ projects }),

  // Active project
  activeProject: null,
  setActiveProject: (project) => set({ activeProject: project }),

  // Agent states for active run
  agentStates: initialAgentState(),
  activeAgent: null,
  feedMessages: [],   // chat-feed messages: { id, agent, type, text, ts }
  ws: null,

  // ── Reset for new run ────────────────────────────────────────────────────────
  resetRun: () => set({
    agentStates: initialAgentState(),
    activeAgent: null,
    feedMessages: [],
  }),

  // ── WebSocket event handler ───────────────────────────────────────────────
  handleWsEvent: (event) => {
    const { type, agent, data } = event;
    const state = get();

    if (type === 'agent_start') {
      set(s => ({
        activeAgent: agent,
        agentStates: {
          ...s.agentStates,
          [agent]: { ...s.agentStates[agent], status: 'running' },
        },
        feedMessages: [
          ...s.feedMessages,
          { id: Date.now() + Math.random(), agent, type: 'start', text: data, ts: new Date() },
        ],
      }));
    }

    else if (type === 'token') {
      set(s => {
        const existing = s.agentStates[agent];
        return {
          agentStates: {
            ...s.agentStates,
            [agent]: {
              ...existing,
              output: existing.output + data,
              chunks: [...existing.chunks, data],
            },
          },
        };
      });
    }

    else if (type === 'agent_done') {
      set(s => ({
        agentStates: {
          ...s.agentStates,
          [agent]: { ...s.agentStates[agent], status: 'done' },
        },
        feedMessages: [
          ...s.feedMessages,
          { id: Date.now() + Math.random(), agent, type: 'done', text: data, ts: new Date() },
        ],
      }));
    }

    else if (type === 'error') {
      set(s => ({
        agentStates: {
          ...s.agentStates,
          [agent]: { ...s.agentStates[agent], status: 'error' },
        },
        feedMessages: [
          ...s.feedMessages,
          { id: Date.now() + Math.random(), agent, type: 'error', text: data, ts: new Date() },
        ],
      }));
    }

    else if (type === 'pipeline_done') {
      set(s => ({
        activeAgent: null,
        feedMessages: [
          ...s.feedMessages,
          { id: Date.now(), agent: 'system', type: 'done', text: data, ts: new Date() },
        ],
      }));
      // Refresh active project
      if (state.activeProject) {
        // caller should refresh
      }
    }

    else if (type === 'replay') {
      set(s => ({
        agentStates: {
          ...s.agentStates,
          [agent]: { ...s.agentStates[agent], status: 'done', output: data },
        },
      }));
    }
  },

  setWs: (ws) => set({ ws }),

  AGENTS,
  AGENT_META,
}));
