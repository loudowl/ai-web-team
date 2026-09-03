import { X, ExternalLink } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useProjectStore } from '../store/projectStore';
import ThinkingIndicator, { getTicketActivity } from './ThinkingIndicator';
import { isDemoProjectId } from '../demo/demoData';
import { formatModelAssignment, workflowLabel } from '../utils/modelPicker';

const DEMO_PR_PLACEHOLDER = 'https://github.com/foxnews/fts-foxnews.com';

export default function TicketModal({ ticketId, onClose }) {
  const { tickets, ticketStates, JIRA_MILESTONES, activeProject } = useProjectStore();
  const ticket = tickets.find(t => t.id === ticketId);
  const ts = ticketStates[ticketId] || {};
  const activity = getTicketActivity(ts, JIRA_MILESTONES);
  const isRunning = ts.status === 'running' || ts.active;
  const isDone = ts.status === 'done' || ticket?.status === 'done';
  const isDemo = isDemoProjectId(activeProject?.id);
  const realPrUrl = ts.prUrl || ticket?.pr_url;
  const prHref = isDemo ? DEMO_PR_PLACEHOLDER : realPrUrl;
  const showPrButton = isDone && !!prHref;

  const modelAssignment = formatModelAssignment(
    ticket?.assigned_provider || activeProject?.provider,
    ticket?.assigned_model || activeProject?.model,
  );
  const workflow = ticket?.workflow;

  if (!ticket) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="ticket-modal-heading">
            <span className="modal-title">
              🎫 {ticket.ticket_key || ticket.id} — {ticket.title}
            </span>
            <div className="ticket-modal-meta">
              <div className="ticket-modal-meta-item">
                <span className="ticket-modal-meta-label">Coding model</span>
                <span className="ticket-modal-model-chip">{modelAssignment.summary}</span>
              </div>
              {workflow && (
                <div className="ticket-modal-meta-item">
                  <span className="ticket-modal-meta-label">Workflow</span>
                  <span className="ticket-modal-workflow-chip">{workflowLabel(workflow)}</span>
                </div>
              )}
              {ticket.fix_version && (
                <div className="ticket-modal-meta-item">
                  <span className="ticket-modal-meta-label">Fix version</span>
                  <span className="ticket-modal-meta-value">{ticket.fix_version}</span>
                </div>
              )}
              {ticket.collab_branch && (
                <div className="ticket-modal-meta-item">
                  <span className="ticket-modal-meta-label">Base branch</span>
                  <span className="ticket-modal-meta-value mono">{ticket.collab_branch}</span>
                </div>
              )}
            </div>
          </div>
          <button className="icon-btn" type="button" onClick={onClose}>
            <X size={24} color="#e6edf3" />
          </button>
        </div>

        <div style={{ padding: '12px 16px', background: '#161b22', borderBottom: '1px solid #30363d' }}>
          {isRunning && <ThinkingIndicator ticketId={ticketId} />}
          <div className="section-label" style={{ margin: '0 0 8px' }}>MILESTONES</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {JIRA_MILESTONES.map(m => {
              const ms = ts.milestones?.[m.id] || { status: 'pending' };
              const color = ms.status === 'done' ? '#3fb950' : ms.status === 'running' ? '#d29922' : '#484f58';
              const isActiveStep = ms.status === 'running' && activity?.label === m.label;
              return (
                <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <span
                    className={isActiveStep ? 'milestone-dot pulse' : 'milestone-dot'}
                    style={{ background: color }}
                  />
                  <span style={{ color: '#e6edf3', flex: 1 }}>{m.label}</span>
                  {ms.detail && <span className="meta-text">{ms.detail.slice(0, 40)}</span>}
                </div>
              );
            })}
          </div>
        </div>

        {(ts.tasks || []).length > 0 && (
          <div style={{ padding: '12px 16px', background: '#0d1117', borderBottom: '1px solid #30363d' }}>
            <div className="section-label" style={{ margin: '0 0 8px' }}>TASK LIST</div>
            {(ts.tasks || []).map(task => (
              <div key={task.id} style={{ fontSize: 12, color: task.status === 'done' ? '#3fb950' : '#8b949e', marginBottom: 4 }}>
                {task.status === 'done' ? '✓' : '○'} {task.label}
              </div>
            ))}
          </div>
        )}

        <div className="modal-body">
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {ts.output || (isRunning
                ? `_Waiting for model output — local Codestral can take several minutes before the first token appears._`
                : ticket.description || '_Waiting for agent output…_')}
            </ReactMarkdown>
          </div>
        </div>

        {showPrButton && (
          <div className="modal-footer">
            <a
              href={prHref}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-push modal-pr-btn"
            >
              <ExternalLink size={18} />
              View pull request
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
