import { create } from 'zustand';
import { DEMO_TICKETS, isDemoProjectId } from '../demo/demoData';

const OVERRIDE_KEY = 'ai-web-team-lane-overrides';
const DEMO_ARCHIVED_KEY = 'ai-web-team-demo-archived';

const DEMO_TICKET_IDS = new Set(DEMO_TICKETS.map(t => t.id));

function loadOverrides() {
  try {
    return JSON.parse(localStorage.getItem(OVERRIDE_KEY) || '{}');
  } catch {
    return {};
  }
}

function loadDemoArchived() {
  try {
    return JSON.parse(localStorage.getItem(DEMO_ARCHIVED_KEY) || '[]');
  } catch {
    return [];
  }
}

export const useBoardStore = create((set, get) => ({
  laneOverrides: loadOverrides(),
  demoArchived: loadDemoArchived(),

  setLaneOverride: (ticketId, lane, projectId = null) => {
    const key = laneOverrideKey(projectId, ticketId);
    const laneOverrides = { ...get().laneOverrides, [key]: lane };
    localStorage.setItem(OVERRIDE_KEY, JSON.stringify(laneOverrides));
    set({ laneOverrides });
  },

  clearLaneOverride: (ticketId, projectId = null) => {
    const laneOverrides = { ...get().laneOverrides };
    delete laneOverrides[laneOverrideKey(projectId, ticketId)];
    delete laneOverrides[ticketId];
    localStorage.setItem(OVERRIDE_KEY, JSON.stringify(laneOverrides));
    set({ laneOverrides });
  },

  archiveDemoTicket: (ticket) => {
    const demoArchived = [
      { ...ticket, archived_at: new Date().toISOString(), board_lane: 'archived' },
      ...get().demoArchived.filter(t => t.id !== ticket.id),
    ];
    localStorage.setItem(DEMO_ARCHIVED_KEY, JSON.stringify(demoArchived));
    set({ demoArchived });
  },

  restoreDemoTicket: (ticketId) => {
    const demoArchived = get().demoArchived.filter(t => t.id !== ticketId);
    localStorage.setItem(DEMO_ARCHIVED_KEY, JSON.stringify(demoArchived));
    set({ demoArchived });
  },

  clearDemoArchived: () => {
    localStorage.removeItem(DEMO_ARCHIVED_KEY);
    set({ demoArchived: [] });
  },

  resetDemoBoard: () => {
    const laneOverrides = { ...get().laneOverrides };
    for (const id of DEMO_TICKET_IDS) {
      delete laneOverrides[id];
    }
    localStorage.setItem(OVERRIDE_KEY, JSON.stringify(laneOverrides));
    localStorage.removeItem(DEMO_ARCHIVED_KEY);
    set({ laneOverrides, demoArchived: [] });
  },
}));

export function getArchivedDemoTickets() {
  return useBoardStore.getState().demoArchived;
}

export function isTicketArchived(ticket, projectId) {
  if (ticket.archived_at) return true;
  if (isDemoProjectId(projectId)) {
    return useBoardStore.getState().demoArchived.some(t => t.id === ticket.id);
  }
  return false;
}
