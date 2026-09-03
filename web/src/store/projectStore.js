import { create } from 'zustand';
import { isDemoProjectId } from '../demo/demoData';
import { listTickets, listGlobalBoardTickets } from '../services/api';

const AGENTS = ['pm', 'designer', 'architect', 'developer'];

const AGENT_META = {
  pm:        { label: 'Project Manager', icon: '📋', color: '#58a6ff' },
  designer:  { label: 'Designer',        icon: '🎨', color: '#bc8cff' },
  architect: { label: 'Architect',       icon: '🏗️',  color: '#d29922' },
  developer: { label: 'Developer',       icon: '💻', color: '#3fb950' },
  senior_dev:{ label: 'Senior Engineer', icon: '🧑‍💻', color: '#3fb950' },
  code_reviewer:{ label: 'Code Reviewer', icon: '🔍', color: '#79c0ff' },
};

const JIRA_MILESTONES = [
  { id: 'fetch_ticket',     label: 'Load ticket' },
  { id: 'gather_context',   label: 'Gather repo context' },
  { id: 'create_worktree',  label: 'Create worktree' },
  { id: 'analyze_plan',     label: 'Analyze & plan' },
  { id: 'implement',        label: 'Implement' },
  { id: 'apply_patches',    label: 'Apply code changes' },
  { id: 'fix_lint',         label: 'Fix lint errors' },
  { id: 'commit_push',      label: 'Commit & push' },
  { id: 'create_pr',        label: 'Create pull request' },
  { id: 'address_review',   label: 'Address Copilot review' },
];

const initialAgentState = () =>
  Object.fromEntries(
    AGENTS.map(a => [a, { status: 'pending', output: '', chunks: [] }])
  );

const initialTicketState = () => ({
  status: 'pending',
  output: '',
  prUrl: '',
  tasks: [],
  milestones: Object.fromEntries(
    JIRA_MILESTONES.map(m => [m.id, { status: 'pending', detail: '' }])
  ),
  boardLane: 'todo',
  active: false,
  startedAt: null,
  thinkingSince: null,
  thinkingMessage: '',
  thinkingPhase: '',
  lastTokenAt: null,
});

export const useProjectStore = create((set, get) => ({
  projects: [],
  setProjects: (projects) => set({ projects }),

  activeProject: null,
  setActiveProject: (project) => set({ activeProject: project }),

  // Greenfield
  agentStates: initialAgentState(),
  activeAgent: null,
  feedMessages: [],
  ws: null,

  // Jira mode — keyed by ticket_id
  ticketStates: {},
  tickets: [],
  activeTicketId: null,

  setTickets: (incoming) => {
    const rows = Array.isArray(incoming) ? incoming : [];
    const { activeProject, ticketStates: prevStates } = get();
    const ticketStates = {};
    for (const t of rows) {
      const prev = prevStates[t.id] || {};
      ticketStates[t.id] = {
        ...initialTicketState(),
        ...prev,
        status: t.status || prev.status || 'pending',
        output: t.output || prev.output || '',
        prUrl: t.pr_url || prev.prUrl || '',
        boardLane: t.board_lane || prev.boardLane || 'todo',
        tasks: (() => {
          if (!t.tasks_json) return prev.tasks || [];
          try {
            return JSON.parse(t.tasks_json);
          } catch {
            return prev.tasks || [];
          }
        })(),
      };
    }
    const withModel = rows.map(t => ({
      ...t,
      assigned_provider: t.assigned_provider || t.project_provider || activeProject?.provider,
      assigned_model: t.assigned_model || t.project_model || activeProject?.model,
    }));
    set({ tickets: withModel, ticketStates });
  },

  mergeTickets: (incoming) => {
    const rows = Array.isArray(incoming) ? incoming : [];
    const { tickets } = get();
    const byId = new Map(tickets.map(t => [t.id, t]));
    for (const t of rows) {
      byId.set(t.id, { ...byId.get(t.id), ...t });
    }
    get().setTickets([...byId.values()]);
  },

  syncTicketsFromApi: async (projectId) => {
    if (!projectId || isDemoProjectId(projectId)) return;
    try {
      const rows = await listTickets(projectId);
      get().setTickets(rows);
    } catch (e) {
      console.warn('Failed to sync tickets', e);
    }
  },

  syncGlobalBoardTickets: async () => {
    try {
      const data = await listGlobalBoardTickets();
      get().setTickets(data.tickets || []);
      return data;
    } catch (e) {
      console.warn('Failed to sync global board tickets', e);
      return { tickets: [], project_count: 0 };
    }
  },

  updateTicketRow: (ticketId, patch) => set(s => ({
    tickets: s.tickets.map(t => t.id === ticketId ? { ...t, ...patch } : t),
  })),

  removeDemoTicket: (ticketId) => set(s => ({
    tickets: s.tickets.filter(t => t.id !== ticketId),
    ticketStates: Object.fromEntries(
      Object.entries(s.ticketStates).filter(([id]) => id !== ticketId),
    ),
  })),

  addDemoTicket: (payload) => set(s => {
    const id = `demo-${Date.now().toString(36)}`;
    const key = payload.ticket_key || `DEMO-${s.tickets.length + 1}`;
    const row = {
      id,
      ticket_key: key,
      title: payload.manual?.title || key,
      description: payload.manual?.description || '',
      acceptance_criteria: payload.manual?.acceptance_criteria || '',
      jira_url: payload.jira_url || '',
      status: 'pending',
      board_lane: 'todo',
      assigned_provider: s.activeProject?.provider || 'ollama',
      assigned_model: s.activeProject?.model || 'codestral',
    };
    return {
      tickets: [...s.tickets, row],
      ticketStates: {
        ...s.ticketStates,
        [id]: { ...initialTicketState(), boardLane: 'todo' },
      },
    };
  }),

  resetRun: () => set({
    agentStates: initialAgentState(),
    activeAgent: null,
    feedMessages: [],
    ticketStates: {},
    tickets: [],
    activeTicketId: null,
  }),

  clearBoardRunState: () => set({
    ticketStates: {},
    activeTicketId: null,
    feedMessages: [],
  }),

  handleWsEvent: (event) => {
    const { type, agent, data, ticket_id: ticketId } = event;

    // ── Jira mode events ───────────────────────────────────────────────────
    if (ticketId) {
      set(s => {
        const ts = { ...(s.ticketStates[ticketId] || initialTicketState()) };

        if (type === 'ticket_start' || type === 'agent_start') {
          ts.active = true;
          ts.status = 'running';
          ts.startedAt = ts.startedAt || Date.now();
          ts.thinkingSince = ts.thinkingSince || Date.now();
        } else if (type === 'token') {
          ts.output = (ts.output || '') + data;
          ts.lastTokenAt = Date.now();
        } else if (type === 'thinking') {
          ts.thinkingSince = ts.thinkingSince || Date.now();
          try {
            const info = JSON.parse(data);
            ts.thinkingMessage = info.message || 'Thinking…';
            if (info.phase) ts.thinkingPhase = info.phase;
          } catch {
            ts.thinkingMessage = data || 'Thinking…';
          }
        } else if (type === 'milestone') {
          try {
            const m = JSON.parse(data);
            ts.milestones = {
              ...ts.milestones,
              [m.milestone_id]: { status: m.status, detail: m.detail || '' },
            };
            if (m.status === 'running') {
              ts.thinkingSince = Date.now();
              ts.thinkingPhase = m.milestone_id;
              ts.thinkingMessage = m.detail || '';
            }
          } catch {}
        } else if (type === 'tasks') {
          try { ts.tasks = JSON.parse(data); } catch {}
        } else if (type === 'agent_done' || type === 'ticket_done') {
          ts.status = 'done';
          ts.active = false;
        } else if (type === 'pr_created') {
          ts.prUrl = data;
        } else if (type === 'board_lane') {
          ts.boardLane = data;
        } else if (type === 'error') {
          ts.status = 'error';
          ts.active = false;
        } else if (type === 'replay') {
          ts.output = data;
          ts.status = 'done';
        }

        return {
          ticketStates: { ...s.ticketStates, [ticketId]: ts },
          tickets: type === 'board_lane'
            ? s.tickets.map(t => t.id === ticketId ? { ...t, board_lane: data } : t)
            : type === 'pr_created'
              ? s.tickets.map(t => t.id === ticketId ? { ...t, pr_url: data } : t)
              : s.tickets,
          activeTicketId: ts.active ? ticketId : s.activeTicketId,
          feedMessages: [
            ...s.feedMessages,
            {
              id: Date.now() + Math.random(),
              agent: agent || 'senior_dev',
              type: type === 'error' ? 'error' : 'start',
              text: typeof data === 'string' ? data.slice(0, 200) : type,
              ts: new Date(),
              ticketId,
            },
          ],
        };
      });
      if (['ticket_start', 'ticket_done', 'board_lane', 'pr_created', 'error'].includes(type)) {
        const projectId = get().activeProject?.id;
        if (projectId && !isDemoProjectId(projectId)) {
          get().syncTicketsFromApi(projectId);
        }
      }
      return;
    }

    // ── Greenfield events (unchanged) ──────────────────────────────────────
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
    } else if (type === 'token') {
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
    } else if (type === 'agent_done') {
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
    } else if (type === 'error') {
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
    } else if (type === 'pipeline_done') {
      set(s => ({
        activeAgent: null,
        feedMessages: [
          ...s.feedMessages,
          { id: Date.now(), agent: 'system', type: 'done', text: data, ts: new Date() },
        ],
      }));
    } else if (type === 'replay') {
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
  JIRA_MILESTONES,
}));
