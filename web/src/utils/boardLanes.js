export const BOARD_LANES = [
  { id: 'todo', label: 'To Do', color: '#8b949e' },
  { id: 'in_progress', label: 'In Progress', color: '#d29922' },
  { id: 'in_review', label: 'In Review', color: '#58a6ff' },
  { id: 'dev_complete', label: 'Dev Complete', color: '#3fb950' },
];

export const WORKFLOWS = [
  {
    id: 'simple',
    label: 'Simple fix',
    title: 'Default agent workflow (plan → implement → lint → PR)',
  },
  {
    id: 'fix',
    label: 'Fix',
    title: 'Scoped fix — lint on, skip Copilot review (fts-ai-standards parallel mode)',
  },
  {
    id: 'full_cycle',
    label: 'Full cycle',
    title: 'Full cycle — lint, PR, and extended Copilot review pass',
  },
];

/** Resolve swim lane from ticket row, live state, and optional manual override. */
export function resolveTicketLane(ticket, ticketState = {}, laneOverride = null) {
  if (!ticket || ticket.archived_at) return null;
  if (laneOverride) return laneOverride;

  const ts = ticketState || {};

  if (ticket.board_lane === 'dev_complete') return 'dev_complete';
  if (ticket.board_lane === 'in_review') return 'in_review';
  if (ticket.board_lane === 'in_progress') return 'in_progress';
  if (ts.boardLane === 'dev_complete') return 'dev_complete';
  if (ts.boardLane === 'in_review') return 'in_review';
  if (ts.boardLane === 'in_progress') return 'in_progress';
  if (ts.status === 'running' || ts.active) return 'in_progress';
  if (ts.prUrl || ticket.pr_url) return 'in_review';
  if (ticket.board_lane && BOARD_LANES.some(l => l.id === ticket.board_lane)) {
    return ticket.board_lane;
  }
  return 'todo';
}

export function laneOverrideKey(projectId, ticketId) {
  return projectId ? `${projectId}:${ticketId}` : ticketId;
}

export function getLaneOverride(laneOverrides, ticket) {
  if (!ticket) return null;
  const scoped = ticket.project_id
    ? laneOverrides[laneOverrideKey(ticket.project_id, ticket.id)]
    : null;
  return scoped || laneOverrides[ticket.id] || null;
}

export function groupTicketsByLane(tickets, ticketStates, laneOverrides = {}) {
  const groups = Object.fromEntries(BOARD_LANES.map(l => [l.id, []]));
  for (const t of tickets) {
    if (t.archived_at) continue;
    const lane = resolveTicketLane(t, ticketStates[t.id], getLaneOverride(laneOverrides, t));
    if (lane && groups[lane]) groups[lane].push(t);
  }
  return groups;
}
