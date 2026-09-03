import {
  DEMO_PROJECT_ID,
  DEMO_TICKETS,
  createDemoProject,
  DEMO_THOUGHTS,
  demoTicketNumber,
  getDemoPlan,
  getDemoCode,
  getDemoTasks,
} from './demoData';

const MILESTONES = [
  'fetch_ticket',
  'gather_context',
  'create_worktree',
  'analyze_plan',
  'implement',
  'apply_patches',
  'commit_push',
  'create_pr',
];

const MILESTONE_LABELS = {
  fetch_ticket: 'Load ticket',
  gather_context: 'Gather repo context',
  create_worktree: 'Create worktree',
  analyze_plan: 'Analyze & plan',
  implement: 'Implement',
  apply_patches: 'Apply code changes',
  commit_push: 'Commit & push',
  create_pr: 'Create pull request',
};

/** Per-milestone dwell time (ms) — slow enough to open modals mid-run. */
const PACE = {
  fetch_ticket: 2200,
  gather_context: 2400,
  create_worktree: 2600,
  analyze_plan: 4500,
  implement: 6500,
  apply_patches: 2800,
  commit_push: 2400,
  create_pr: 2200,
};

const START_STAGGER_MS = 1400;

function emit(onEvent, type, data, ticketId) {
  onEvent({
    type,
    agent: 'senior_dev',
    data: typeof data === 'string' ? data : JSON.stringify(data),
    ticket_id: ticketId,
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function streamText(onEvent, ticketId, text, chunkMs = 35) {
  const chunkSize = 28;
  for (let i = 0; i < text.length; i += chunkSize) {
    emit(onEvent, 'token', text.slice(i, i + chunkSize), ticketId);
    await sleep(chunkMs);
  }
}

/**
 * Replay scripted WS events for all demo tickets in parallel.
 * Returns a stop function — does not touch the backend.
 */
export function startDemoSimulation(onEvent, onProjectUpdate) {
  let cancelled = false;

  const runTicket = async (ticket, startDelayMs) => {
    await sleep(startDelayMs);
    if (cancelled) return;

    const thoughts = DEMO_THOUGHTS[ticket.id] || ['Working…'];
    let thoughtIdx = 0;
    const prNum = 2400 + demoTicketNumber(ticket.id);

    emit(onEvent, 'ticket_start', `Starting ${ticket.ticket_key}…`, ticket.id);
    emit(onEvent, 'agent_start', `Senior Dev → ${ticket.title}`, ticket.id);

    for (let i = 0; i < MILESTONES.length; i += 1) {
      if (cancelled) return;
      const mid = MILESTONES[i];
      const label = MILESTONE_LABELS[mid];
      const dwell = PACE[mid] || 2500;

      emit(onEvent, 'milestone', {
        milestone_id: mid,
        label,
        status: 'running',
        detail: label,
      }, ticket.id);

      emit(onEvent, 'thinking', {
        phase: mid,
        message: thoughts[thoughtIdx] || `Working on ${label.toLowerCase()}…`,
      }, ticket.id);
      thoughtIdx = Math.min(thoughtIdx + 1, thoughts.length - 1);

      if (mid === 'analyze_plan') {
        const plan = getDemoPlan(ticket);
        await streamText(onEvent, ticket.id, plan, 40);
        if (cancelled) return;
        const tasks = getDemoTasks(ticket);
        emit(onEvent, 'tasks', JSON.stringify(tasks), ticket.id);
        await sleep(Math.max(800, dwell - plan.length * 40));
      } else if (mid === 'implement') {
        const code = getDemoCode(ticket);
        await streamText(onEvent, ticket.id, '\n\n---\n\n# Implementation\n\n' + code, 28);
        if (cancelled) return;
        await sleep(1200);
      } else {
        await sleep(dwell);
      }

      if (cancelled) return;

      emit(onEvent, 'milestone', {
        milestone_id: mid,
        label,
        status: 'done',
        detail: mid === 'create_pr' ? `https://github.com/foxnews/foxnews.com/pull/${prNum}` : '',
      }, ticket.id);
    }

    if (cancelled) return;
    emit(onEvent, 'pr_created', `https://github.com/foxnews/foxnews.com/pull/${prNum}`, ticket.id);
    emit(onEvent, 'ticket_done', `PR opened for ${ticket.ticket_key}`, ticket.id);
    emit(onEvent, 'agent_done', `Finished ${ticket.ticket_key}`, ticket.id);
  };

  (async () => {
    onProjectUpdate(createDemoProject());
    await Promise.all(
      DEMO_TICKETS.map((t, i) => runTicket(t, i * START_STAGGER_MS)),
    );

    if (cancelled) return;

    emit(onEvent, 'pipeline_done', `Jira mode complete — ${DEMO_TICKETS.length} ticket(s) processed.`);
    onProjectUpdate({
      ...createDemoProject(),
      status: 'done',
      updated_at: new Date().toISOString(),
    });
  })();

  return () => {
    cancelled = true;
  };
}

export function getDemoProject() {
  return createDemoProject();
}

export function getDemoTickets() {
  return DEMO_TICKETS.map(t => ({ ...t }));
}

export { DEMO_PROJECT_ID };
