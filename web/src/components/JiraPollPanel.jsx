import { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Play, Square, Radio, RotateCcw } from 'lucide-react';
import {
  getJiraPollStatus,
  listJiraBoards,
  reassignJiraPollModels,
  resetJiraBoard,
  startJiraPoll,
  stopJiraPoll,
  syncJiraPoll,
} from '../services/api';

export default function JiraPollPanel({ projectId, onSynced, reassignAllProjects = false }) {
  const [status, setStatus] = useState(null);
  const [boards, setBoards] = useState([]);
  const [boardId, setBoardId] = useState('');
  const [projectKey, setProjectKey] = useState('');
  const [jql, setJql] = useState('');
  const [intervalSec, setIntervalSec] = useState(300);
  const [noLocalModels, setNoLocalModels] = useState(false);
  const [busy, setBusy] = useState('');
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!projectId) return;
    try {
      const s = await getJiraPollStatus(projectId);
      setStatus(s);
      setBoardId(s.board_id || '');
      setProjectKey(s.project_key || '');
      setJql(s.jql || '');
      setIntervalSec(s.interval_sec || 300);
      setNoLocalModels(!!s.no_local_models);
      setError('');
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load poll status');
    }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!status?.configured) {
      setBoards([]);
      return undefined;
    }
    listJiraBoards(projectKey || undefined)
      .then(setBoards)
      .catch(() => setBoards([]));
    return undefined;
  }, [projectKey, status?.configured]);

  useEffect(() => {
    if (!boards.length || boardId) return;
    const key = (projectKey || status?.project_key || '').toUpperCase();
    const preferred = boards.find(b => b.project_key === key && b.type === 'kanban')
      || boards.find(b => b.project_key === key && b.type === 'scrum')
      || boards.find(b => b.project_key === key)
      || boards[0];
    if (preferred?.id != null) setBoardId(String(preferred.id));
  }, [boards, boardId, projectKey, status?.project_key]);

  const pollPayload = () => ({
    board_id: boardId || undefined,
    project_key: projectKey || undefined,
    jql: jql || undefined,
    interval_sec: intervalSec,
    no_local_models: noLocalModels,
    reassign_all_projects: reassignAllProjects,
  });

  const run = async (action) => {
    if (!projectId) return;
    if (action === 'reset') {
      const ok = window.confirm(
        'Delete every ticket on this board and re-import from Jira To Do?\n\n'
        + 'Tickets without a fix version will land in Pre assessed.',
      );
      if (!ok) return;
    }
    setBusy(action);
    setError('');
    const payload = pollPayload();
    try {
      let result;
      if (action === 'sync') result = await syncJiraPoll(projectId, payload);
      else if (action === 'reset') result = await resetJiraBoard(projectId, payload);
      else if (action === 'start') result = await startJiraPoll(projectId, payload);
      else if (action === 'stop') result = await stopJiraPoll(projectId);
      setLastResult(result?.initial_sync || result?.reassign || result);
      await load();
      onSynced?.();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Poll action failed');
    } finally {
      setBusy('');
    }
  };

  const handleNoLocalModelsChange = async (checked) => {
    setNoLocalModels(checked);
    if (!projectId || busy) return;
    setBusy('reassign');
    setError('');
    try {
      const result = await reassignJiraPollModels(projectId, {
        no_local_models: checked,
        reassign_all_projects: reassignAllProjects,
      });
      if (checked && result?.reassigned_count > 0) {
        setLastResult(result);
      }
      await load();
      onSynced?.();
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to update model policy');
      setNoLocalModels(!checked);
    } finally {
      setBusy('');
    }
  };

  if (!projectId) return null;

  return (
    <section className="jira-poll-panel">
      <div className="jira-poll-head">
        <div>
          <span className="section-label">JIRA TO DO SYNC</span>
          <p className="jira-poll-copy">
            Poll your Jira board&apos;s To Do column, ingest issues locally, and auto-assign coding models by complexity.
            Set your project key and board id from Jira Software (Board settings → board URL).
          </p>
        </div>
        {status?.active && (
          <span className="jira-poll-live">
            <Radio size={12} /> Polling
          </span>
        )}
      </div>

      {!status?.configured && (
        <div className="jira-poll-warn">
          Set `JIRA_BASE_URL`, `JIRA_EMAIL`, and `JIRA_API_TOKEN` in backend `.env` to enable polling.
        </div>
      )}

      <div className="jira-poll-fields">
        <label className="jira-poll-field">
          <span>Project key</span>
          <input className="input" value={projectKey} onChange={e => setProjectKey(e.target.value.toUpperCase())} placeholder="PROJ" />
        </label>
        <label className="jira-poll-field">
          <span>Board</span>
          <select className="input" value={boardId} onChange={e => setBoardId(e.target.value)}>
            <option value="">JQL only / default</option>
            {boards.map(b => (
              <option key={b.id} value={String(b.id)}>{b.name} ({b.project_key || b.type})</option>
            ))}
          </select>
        </label>
        <label className="jira-poll-field jira-poll-field-wide">
          <span>To Do JQL (optional)</span>
          <input className="input" value={jql} onChange={e => setJql(e.target.value)} placeholder='statusCategory = "To Do" AND project = PROJ' />
        </label>
        <label className="jira-poll-field">
          <span>Interval (sec)</span>
          <input className="input" type="number" min={30} max={3600} value={intervalSec} onChange={e => setIntervalSec(Number(e.target.value) || 300)} />
        </label>
      </div>

      <div className="jira-poll-actions">
        <button type="button" className="dash-action" disabled={!!busy || !status?.configured} onClick={() => run('sync')}>
          <RefreshCw size={14} className={busy === 'sync' ? 'spin-icon' : ''} />
          Sync now
        </button>
        <button type="button" className="dash-action dash-action-danger" disabled={!!busy || !status?.configured} onClick={() => run('reset')}>
          <RotateCcw size={14} className={busy === 'reset' ? 'spin-icon' : ''} />
          Reset board
        </button>
        <label className="jira-poll-checkbox">
          <input
            type="checkbox"
            checked={noLocalModels}
            disabled={!!busy || !status?.configured}
            onChange={e => handleNoLocalModelsChange(e.target.checked)}
          />
          <span>No local models</span>
        </label>
        <button type="button" className="dash-action dash-action-primary" disabled={!!busy || !status?.configured || status?.active} onClick={() => run('start')}>
          <Play size={14} />
          Start polling
        </button>
        <button type="button" className="dash-action" disabled={!!busy || !status?.active} onClick={() => run('stop')}>
          <Square size={14} />
          Stop
        </button>
      </div>

      {status?.last_poll_at && (
        <div className="jira-poll-meta">Last poll: {new Date(status.last_poll_at).toLocaleString()}</div>
      )}

      {lastResult && (
        <div className="jira-poll-result">
          {lastResult.found != null && (
            <>
              {lastResult.reset ? `Removed ${lastResult.deleted ?? 0} · ` : ''}
              Found {lastResult.found ?? 0} · Added {lastResult.added?.length ?? 0}
              {(lastResult.updated?.length ?? 0) > 0 ? ` · Updated ${lastResult.updated.length}` : ''}
              {' · Skipped '}{lastResult.skipped?.length ?? 0}
            </>
          )}
          {lastResult.reassigned_count != null && (
            <>Reassigned {lastResult.reassigned_count} To Do ticket{lastResult.reassigned_count === 1 ? '' : 's'} to cloud models</>
          )}
          {(lastResult.added || []).slice(0, 5).map(t => (
            <div key={t.ticket_id} className="jira-poll-added">
              {t.ticket_key} → {t.complexity_tier} / {t.assigned_model}
            </div>
          ))}
          {(lastResult.reassigned || []).slice(0, 5).map(t => (
            <div key={t.ticket_id} className="jira-poll-added">
              {t.ticket_key} → {t.complexity_tier} / {t.assigned_model}
            </div>
          ))}
        </div>
      )}

      {error && <div className="jira-poll-error">{error}</div>}
    </section>
  );
}
