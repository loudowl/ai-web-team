import { useEffect, useRef, useState } from 'react';
import { Download, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { streamOllamaPull } from '../utils/ollamaPull';

const PHASE = {
  PROMPT: 'prompt',
  PULLING: 'pulling',
  READY: 'ready',
  ERROR: 'error',
};

export default function OllamaPullModal({
  open,
  info,
  ticketLabel,
  onClose,
  onReady,
}) {
  const [phase, setPhase] = useState(PHASE.PROMPT);
  const [status, setStatus] = useState('');
  const [pct, setPct] = useState(0);
  const [error, setError] = useState('');
  const abortRef = useRef(null);

  useEffect(() => {
    if (!open) {
      setPhase(PHASE.PROMPT);
      setStatus('');
      setPct(0);
      setError('');
      abortRef.current?.abort();
      abortRef.current = null;
    }
  }, [open, info?.model]);

  if (!open || !info) return null;

  const display = info.display || info.model || 'Model';
  const pullTag = info.pull_tag || (info.model || '').split(':')[0];
  const ramHint = info.ram_hint;

  const startPull = async () => {
    setPhase(PHASE.PULLING);
    setStatus('Starting download…');
    setPct(0);
    setError('');
    abortRef.current = new AbortController();

    try {
      await streamOllamaPull(pullTag, {
        signal: abortRef.current.signal,
        onProgress: ({ status: s, pct: p }) => {
          setStatus(s || 'Downloading…');
          setPct(p || 0);
        },
      });
      setPhase(PHASE.READY);
      setStatus('Model installed and ready.');
      setPct(100);
      onReady?.();
    } catch (e) {
      setPhase(PHASE.ERROR);
      setError(e.message || 'Download failed');
    }
  };

  const handleClose = () => {
    abortRef.current?.abort();
    onClose?.();
  };

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal ollama-pull-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Download coding model</span>
          <button type="button" className="icon-btn" onClick={handleClose} aria-label="Close">
            <X size={22} color="#e6edf3" />
          </button>
        </div>

        <div className="modal-body ollama-pull-body">
          <p className="ollama-pull-lead">
            <strong>{display}</strong> is not installed in Ollama yet.
            {ticketLabel ? ` It is required to run ${ticketLabel}.` : null}
          </p>
          {ramHint && <p className="ollama-pull-hint">Estimated memory: {ramHint}</p>}
          {info.pull_command && (
            <code className="ollama-pull-command">{info.pull_command}</code>
          )}

          {phase === PHASE.PROMPT && (
            <div className="ollama-pull-actions">
              <button type="button" className="btn-outline" onClick={handleClose}>
                Cancel
              </button>
              <button type="button" className="btn-push" onClick={startPull}>
                <Download size={16} />
                Download &amp; install
              </button>
            </div>
          )}

          {phase === PHASE.PULLING && (
            <div className="pull-progress ollama-pull-progress">
              <div className="pull-status">{status || 'Downloading…'}</div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${pct}%` }} />
              </div>
              <div className="pull-pct">{pct}%</div>
              <p className="ollama-pull-wait">Large models can take several minutes. Keep this tab open.</p>
            </div>
          )}

          {phase === PHASE.READY && (
            <div className="ollama-pull-ready">
              <CheckCircle2 size={20} color="#3fb950" />
              <span>Ready to proceed — starting your ticket run…</span>
            </div>
          )}

          {phase === PHASE.ERROR && (
            <div className="ollama-pull-error">
              <AlertCircle size={18} color="#f85149" />
              <span>{error}</span>
              <div className="ollama-pull-actions">
                <button type="button" className="btn-outline" onClick={handleClose}>Close</button>
                <button type="button" className="btn-push" onClick={startPull}>Retry download</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
