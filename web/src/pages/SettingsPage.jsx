import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Trash2 } from 'lucide-react';
import { listModels, deleteModel } from '../services/api';
import { streamOllamaPull } from '../utils/ollamaPull';
import OllamaMemoryMeter from '../components/OllamaMemoryMeter';

function ModelRow({ model, onDelete }) {
  const sizeGB = model.size ? (model.size / 1e9).toFixed(1) + ' GB' : '';
  return (
    <div className="settings-row">
      <div style={{ flex: 1 }}>
        <div className="model-name">{model.name}</div>
        {sizeGB ? <div className="model-meta">{sizeGB}</div> : null}
      </div>
      <button className="delete-btn" onClick={() => onDelete(model.name)}>
        <Trash2 size={16} />
      </button>
    </div>
  );
}

function PullProgress({ model, onDone }) {
  const [status, setStatus] = useState('Starting pull...');
  const [pct, setPct]       = useState(0);

  useEffect(() => {
    let cancelled = false;
    streamOllamaPull(model, {
      onProgress: ({ status: s, pct: p }) => {
        if (cancelled) return;
        setStatus(s || '');
        setPct(p || 0);
      },
    })
      .then(() => { if (!cancelled) onDone(); })
      .catch(e => {
        window.alert('Pull failed: ' + e.message);
        if (!cancelled) onDone();
      });

    return () => { cancelled = true; };
  }, [model, onDone]);

  return (
    <div className="pull-progress">
      <div className="pull-status">{status}</div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="pull-pct">{pct}%</div>
    </div>
  );
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const [models, setModels]       = useState(null);
  const [pullModel, setPullModel] = useState('');
  const [pulling, setPulling]     = useState(false);
  const [loading, setLoading]     = useState(true);

  const load = () => {
    setLoading(true);
    listModels().then(m => { setModels(m); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (modelName) => {
    if (!window.confirm(`Remove ${modelName} from Ollama?`)) return;
    try {
      await deleteModel(modelName);
      load();
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message);
    }
  };

  const startPull = () => {
    if (!pullModel.trim()) return;
    setPulling(true);
  };

  return (
    <div className="screen">
      <div className="navbar">
        <button className="icon-btn" onClick={() => navigate(-1)}>
          <ChevronLeft size={24} color="#58a6ff" />
        </button>
        <span className="nav-title">Settings &amp; Models</span>
        <span className="spacer-40" />
      </div>

      <div className="content">
        <div className="section">AI Providers</div>
        {models?.providers ? Object.entries(models.providers).map(([key, info]) => (
          <div key={key} className="settings-row">
            <span className="dot" style={{ background: info.available ? '#3fb950' : '#f85149' }} />
            <div style={{ flex: 1 }}>
              <div className="provider-name">{key.charAt(0).toUpperCase() + key.slice(1)}</div>
              <div className="provider-model">{info.model}</div>
            </div>
            <span className="provider-status" style={{ color: info.available ? '#3fb950' : '#f85149' }}>
              {info.available ? 'Ready' : 'No key'}
            </span>
          </div>
        )) : loading ? <div className="center-row"><span className="spinner blue" /></div> : null}

        <div className="section">Ollama Memory</div>
        <OllamaMemoryMeter />

        <div className="section">Ollama Models</div>
        {loading ? (
          <div className="center-row" style={{ marginTop: 16 }}><span className="spinner blue" /></div>
        ) : models?.ollama?.length ? (
          models.ollama.map(m => <ModelRow key={m.name} model={m} onDelete={handleDelete} />)
        ) : (
          <div className="empty-italic">No models installed. Pull one below.</div>
        )}

        <div className="section">Pull New Model</div>
        <div className="pull-row">
          <input
            className="input"
            placeholder="e.g. llama3.2, mistral, codellama"
            value={pullModel}
            onChange={e => setPullModel(e.target.value)}
            autoCapitalize="none"
            autoCorrect="off"
          />
          <button className="pull-btn" onClick={startPull} disabled={pulling}>
            {pulling ? <span className="spinner" /> : 'Pull'}
          </button>
        </div>

        {pulling && (
          <PullProgress
            model={pullModel.trim()}
            onDone={() => { setPulling(false); setPullModel(''); load(); }}
          />
        )}

        <div className="hint">
          Popular models: llama3.2 (fast), mistral (balanced), codellama (code), deepseek-coder (code), phi3 (lightweight)
        </div>

        <div className="section">Backend URL</div>
        <div className="config-value">{import.meta.env.VITE_API_URL || 'http://localhost:3001'}</div>
        <div className="hint">Set VITE_API_URL in your .env file to change.</div>
      </div>
    </div>
  );
}
