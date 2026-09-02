import { useEffect, useState } from 'react';
import { useProjectStore } from '../store/projectStore';

const LLM_MILESTONES = new Set(['analyze_plan', 'implement']);

export function formatElapsed(ms) {
  if (!ms || ms < 0) return '0:00';
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, '0')}`;
}

export function getTicketActivity(ticketState, milestones) {
  const ms = ticketState?.milestones || {};
  const running = milestones.find(m => ms[m.id]?.status === 'running');
  const isLlm = running && LLM_MILESTONES.has(running.id);
  const isActive = ticketState?.status === 'running' || ticketState?.active;
  const since = ticketState?.thinkingSince || ticketState?.startedAt;
  const hasRecentTokens = ticketState?.lastTokenAt
    && Date.now() - ticketState.lastTokenAt < 8000;

  if (!isActive) return null;

  if (running) {
    return {
      label: running.label,
      message: ticketState?.thinkingMessage
        || (isLlm && !hasRecentTokens
          ? 'Model is thinking — first tokens can take several minutes on local Ollama'
          : `${running.label}…`),
      isThinking: isLlm && !hasRecentTokens,
      isStreaming: isLlm && hasRecentTokens && !!ticketState?.output,
      since,
    };
  }

  if (isActive) {
    return {
      label: 'Working',
      message: ticketState?.thinkingMessage || 'Starting…',
      isThinking: true,
      isStreaming: false,
      since,
    };
  }

  return null;
}

export default function ThinkingIndicator({ ticketId, compact = false }) {
  const { ticketStates, JIRA_MILESTONES } = useProjectStore();
  const ts = ticketStates[ticketId] || {};
  const activity = getTicketActivity(ts, JIRA_MILESTONES);
  const [, tick] = useState(0);

  useEffect(() => {
    if (!activity?.since) return undefined;
    const id = setInterval(() => tick(n => n + 1), 1000);
    return () => clearInterval(id);
  }, [activity?.since]);

  if (!activity) return null;

  const elapsed = formatElapsed(Date.now() - (activity.since || Date.now()));

  return (
    <div className={`thinking-indicator${compact ? ' compact' : ''}`}>
      <span className={`thinking-dot${activity.isThinking ? ' pulse' : ''}`} />
      <div className="thinking-copy">
        <div className="thinking-title">
          {activity.isStreaming ? 'Streaming' : activity.isThinking ? 'Thinking' : 'Working'}
          {' · '}
          <span className="thinking-elapsed">{elapsed}</span>
        </div>
        <div className="thinking-message">
          {activity.label}
          {activity.message ? ` — ${activity.message}` : ''}
        </div>
      </div>
    </div>
  );
}
