import { useProjectStore } from '../store/projectStore';
import ThinkingIndicator, { getTicketActivity, formatElapsed } from './ThinkingIndicator';
import { useEffect, useState } from 'react';

const STATUS_COLORS = {
  pending: '#8b949e',
  running: '#d29922',
  done:    '#3fb950',
  error:   '#f85149',
};

export default function TicketBoard({ onTicketPress }) {
  const { tickets, ticketStates, JIRA_MILESTONES } = useProjectStore();
  const [, tick] = useState(0);

  useEffect(() => {
    const hasActive = tickets.some(t => {
      const ts = ticketStates[t.id];
      return ts?.active || ts?.status === 'running';
    });
    if (!hasActive) return undefined;
    const id = setInterval(() => tick(n => n + 1), 1000);
    return () => clearInterval(id);
  }, [tickets, ticketStates]);

  if (!tickets.length) {
    return <div className="empty-italic" style={{ padding: 16 }}>No tickets loaded.</div>;
  }

  return (
    <div className="kanban">
      <span className="section-label">JIRA TICKETS</span>
      <div className="kanban-row">
        {tickets.map(t => {
          const ts = ticketStates[t.id] || {};
          const status = ts.status || t.status || 'pending';
          const activity = getTicketActivity(ts, JIRA_MILESTONES);
          const doneTasks = (ts.tasks || []).filter(x => x.status === 'done').length;
          const totalTasks = (ts.tasks || []).length;

          return (
            <button
              key={t.id}
              className={`kanban-card${ts.active ? ' active' : ''}`}
              style={{ borderColor: '#58a6ff', minWidth: 180 }}
              onClick={() => onTicketPress(t.id)}
            >
              <div className="kanban-label" style={{ color: '#58a6ff' }}>
                {t.ticket_key || t.id}
              </div>
              <div style={{ fontSize: 11, color: '#e6edf3', marginBottom: 6, lineHeight: 1.3 }}>
                {t.title}
              </div>
              <div className="status-badge" style={{
                background: STATUS_COLORS[status] + '33',
                borderColor: STATUS_COLORS[status],
              }}>
                <span className="status-badge-text" style={{ color: STATUS_COLORS[status] }}>
                  {status}
                </span>
              </div>
              {totalTasks > 0 && (
                <div className="meta-text" style={{ marginTop: 6 }}>
                  Tasks: {doneTasks}/{totalTasks}
                </div>
              )}
              {(t.pr_url || ts.prUrl) && (
                <div className="meta-text" style={{ marginTop: 6, color: '#58a6ff' }}>
                  PR ready
                </div>
              )}
              {activity && (
                <div className="meta-text" style={{ marginTop: 6, color: '#d29922' }}>
                  {activity.isStreaming ? 'Streaming' : activity.isThinking ? 'Thinking' : 'Working'}
                  {' · '}
                  {activity.label}
                  {' · '}
                  {formatElapsed(Date.now() - (activity.since || Date.now()))}
                </div>
              )}
              {ts.active && (
                <div className="kanban-progress" style={{ marginTop: 8 }}>
                  <div className="kanban-progress-fill" style={{ background: '#58a6ff' }} />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
