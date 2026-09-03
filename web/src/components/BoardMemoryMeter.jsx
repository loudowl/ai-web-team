import { useEffect, useMemo, useState } from 'react';
import { getOllamaMemory } from '../services/api';
import { useProjectStore } from '../store/projectStore';
import { useBoardStore } from '../store/boardStore';
import { groupTicketsByLane } from '../utils/boardLanes';
import { isDemoProjectId } from '../demo/demoData';
import { formatGB, meterColor, estimateBudgetBytes, estimatePerTicketBytes } from '../utils/memoryFormat';

export default function BoardMemoryMeter({ projectId, model }) {
  const { tickets, ticketStates } = useProjectStore();
  const { laneOverrides, demoArchived } = useBoardStore();
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  const isDemo = isDemoProjectId(projectId);

  const inProgressCount = useMemo(() => {
    const visible = isDemo
      ? tickets.filter(t => !demoArchived.some(a => a.id === t.id))
      : tickets.filter(t => !t.archived_at);
    const groups = groupTicketsByLane(visible, ticketStates, laneOverrides);
    return groups.in_progress.length;
  }, [tickets, ticketStates, laneOverrides, demoArchived, isDemo]);

  useEffect(() => {
    let cancelled = false;

    const load = () => {
      getOllamaMemory({ model, inProgress: inProgressCount })
        .then(data => {
          if (cancelled) return;
          setStats(data);
          setError(data.available ? null : data.error || 'Ollama unreachable');
        })
        .catch(e => {
          if (cancelled) return;
          setStats(null);
          setError(e.message || 'Failed to load memory stats');
        });
    };

    load();
    const id = setInterval(load, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [model, inProgressCount]);

  const fallbackPerTicket = estimatePerTicketBytes(model);
  const loadedBytes = stats?.loaded_bytes || 0;
  const systemRam = stats?.system_ram_bytes || 0;
  const budget = stats
    ? {
        budgetedBytes: stats.budgeted_bytes ?? loadedBytes,
        reserveBytes: stats.reserve_bytes ?? 0,
        perTicketBytes: stats.per_ticket_bytes || fallbackPerTicket,
      }
    : estimateBudgetBytes(0, inProgressCount, fallbackPerTicket);

  const budgetedBytes = budget.budgetedBytes;
  const reserveBytes = budget.reserveBytes;
  const remainingBytes = stats?.remaining_bytes
    ?? (systemRam ? Math.max(0, systemRam - budgetedBytes) : 0);

  const budgetPct = systemRam
    ? Math.min(100, (budgetedBytes / systemRam) * 100)
    : stats?.budget_pct || 0;
  const loadedPct = systemRam
    ? Math.min(100, (loadedBytes / systemRam) * 100)
    : stats?.loaded_pct || 0;
  const reservePct = systemRam
    ? Math.min(100 - loadedPct, (reserveBytes / systemRam) * 100)
    : 0;

  const color = meterColor(budgetPct);
  const modelLabel = stats?.model_display || model?.split(':')[0] || 'Ollama model';
  const runningCount = stats?.running?.length || 0;

  return (
    <div className="board-memory-meter" aria-label="Ollama memory budget">
      <div className="board-memory-meter-inner">
        <div className="board-memory-meter-copy">
          <div className="board-memory-meter-title">
            <span className="board-memory-meter-chip">Ollama</span>
            <span className="board-memory-meter-model">{modelLabel}</span>
            <span className="board-memory-meter-tickets">
              {inProgressCount} in progress
            </span>
          </div>
          <div className="board-memory-meter-stats">
            <span style={{ color }}>
              {formatGB(budgetedBytes)} budgeted
            </span>
            {systemRam > 0 && (
              <span className="board-memory-meter-divider">·</span>
            )}
            {systemRam > 0 && (
              <span className="board-memory-meter-remaining">
                {formatGB(remainingBytes)} remaining
              </span>
            )}
            {systemRam > 0 && (
              <span className="board-memory-meter-total">
                of {formatGB(systemRam)}
              </span>
            )}
          </div>
        </div>

        <div className="board-memory-meter-bar-wrap">
          <div className="board-memory-bar" aria-hidden="true">
            {loadedPct > 0 && (
              <div
                className="board-memory-bar-segment loaded"
                style={{ width: `${loadedPct}%`, background: color }}
              />
            )}
            {reservePct > 0 && (
              <div
                className="board-memory-bar-segment reserve"
                style={{ width: `${reservePct}%` }}
              />
            )}
          </div>
          <div className="board-memory-meter-meta">
            {error ? (
              <span className="board-memory-meter-error">{error} — showing estimate</span>
            ) : runningCount > 0 ? (
              <span>{formatGB(loadedBytes)} loaded now</span>
            ) : inProgressCount > 0 ? (
              <span>~{formatGB(budget.perTicketBytes)} per ticket + {formatGB(2e9)} each extra concurrent</span>
            ) : (
              <span>Idle — launch tickets to budget memory</span>
            )}
          </div>
        </div>

        <div className="board-memory-meter-pct" style={{ color }}>
          {budgetPct.toFixed(0)}%
        </div>
      </div>
    </div>
  );
}
