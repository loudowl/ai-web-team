import { useProjectStore } from '../store/projectStore';
import { getTicketActivity, formatElapsed } from './ThinkingIndicator';

function milestoneProgress(milestones, milestoneDefs) {
  const total = milestoneDefs.length;
  const done = milestoneDefs.filter(m => milestones?.[m.id]?.status === 'done').length;
  const running = milestoneDefs.find(m => milestones?.[m.id]?.status === 'running');
  const pct = total ? Math.round((done / total) * 100) : 0;
  return { done, total, pct, running };
}

function stepText(ts, activity, milestones) {
  if (ts.status === 'done') return 'Complete — pull request opened';
  if (ts.status === 'error') return ts.output?.slice(0, 120) || 'Failed';
  if (activity?.isStreaming) return 'Streaming code changes…';
  if (activity?.thinkingMessage) return activity.thinkingMessage;
  const running = milestones.find(m => ts.milestones?.[m.id]?.status === 'running');
  if (running) return `${running.label}…`;
  if (ts.status === 'pending') return 'Queued';
  return 'Working…';
}

export default function TicketProgressCard({ ticket, compact = false }) {
  const { ticketStates, JIRA_MILESTONES } = useProjectStore();
  const ts = ticketStates[ticket.id] || {};
  const activity = getTicketActivity(ts, JIRA_MILESTONES);
  const { pct, running } = milestoneProgress(ts.milestones, JIRA_MILESTONES);
  const status = ts.status || ticket.status || 'pending';

  const barColor = status === 'done'
    ? '#3fb950'
    : status === 'error'
      ? '#f85149'
      : status === 'running' || ts.active
        ? '#d29922'
        : '#484f58';

  const step = stepText(ts, activity, JIRA_MILESTONES);
  const elapsed = activity?.since ? formatElapsed(Date.now() - activity.since) : null;

  return (
    <div className={`ticket-progress-card${compact ? ' compact' : ''}`}>
      <div className="ticket-progress-header">
        <span className="ticket-progress-key">{ticket.ticket_key || ticket.id}</span>
        {elapsed && (status === 'running' || ts.active) && (
          <span className="ticket-progress-elapsed">{elapsed}</span>
        )}
      </div>
      {!compact && (
        <div className="ticket-progress-title">{ticket.title}</div>
      )}
      <div className="ticket-progress-bar">
        <div
          className="ticket-progress-fill"
          style={{ width: `${pct}%`, background: barColor }}
        />
      </div>
      <div className="ticket-progress-meta">
        <span style={{ color: barColor }}>
          {running?.label || (status === 'done' ? 'Done' : status === 'error' ? 'Error' : 'Pending')}
        </span>
        <span className="ticket-progress-pct">{pct}%</span>
      </div>
      <div className="ticket-progress-step">{step}</div>
    </div>
  );
}
