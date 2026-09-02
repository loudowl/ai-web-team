import { useProjectStore } from '../store/projectStore';

const STATUS_COLORS = {
  pending: '#30363d',
  running: '#d29922',
  done:    '#3fb950',
  error:   '#f85149',
};

const STATUS_LABELS = {
  pending: 'Waiting',
  running: 'Working…',
  done:    'Done ✓',
  error:   'Error ✗',
};

export default function AgentKanban({ onAgentPress }) {
  const { AGENTS, AGENT_META, agentStates, activeAgent } = useProjectStore();

  return (
    <div className="kanban">
      <span className="section-label">AGENT STATUS</span>
      <div className="kanban-row">
        {AGENTS.map(agentKey => {
          const meta     = AGENT_META[agentKey];
          const state    = agentStates[agentKey];
          const isActive = agentKey === activeAgent;
          const progress = state.status === 'running';
          const statusColor = STATUS_COLORS[state.status];

          return (
            <button
              key={agentKey}
              className={`kanban-card${isActive ? ' active' : ''}`}
              style={{ borderColor: meta.color }}
              onClick={() => onAgentPress && onAgentPress(agentKey)}
            >
              {isActive && (
                <span className="active-border" style={{ background: meta.color + '22' }} />
              )}

              <div className="kanban-icon">{meta.icon}</div>
              <div className="kanban-label" style={{ color: meta.color }}>{meta.label}</div>

              <div className="status-badge" style={{ background: statusColor + '33', borderColor: statusColor }}>
                <span className="status-badge-text" style={{ color: statusColor }}>
                  {STATUS_LABELS[state.status]}
                </span>
              </div>

              {progress && (
                <div className="kanban-progress">
                  <div className="kanban-progress-fill" style={{ background: meta.color }} />
                </div>
              )}

              {state.output.length > 0 && (
                <div className="kanban-preview">{state.output.slice(0, 80)}…</div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
