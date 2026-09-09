import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { listProviderChoices, updateTicketProperties } from '../services/api';
import ModelCardPicker from './ModelCardPicker';
import { PROVIDERS } from '../utils/modelPicker';

const TSHIRT_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];

export default function TicketPropertiesModal({
  ticket,
  projectId,
  onClose,
  onSaved,
}) {
  const [providerChoices, setProviderChoices] = useState(null);
  const [provider, setProvider] = useState(ticket?.assigned_provider || 'anthropic');
  const [model, setModel] = useState(ticket?.assigned_model || '');
  const [fixVersion, setFixVersion] = useState(ticket?.fix_version || '');
  const [tShirtSize, setTShirtSize] = useState(ticket?.t_shirt_size || '');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listProviderChoices().then(setProviderChoices).catch(() => setProviderChoices(null));
  }, []);

  useEffect(() => {
    if (!ticket) return;
    setProvider(ticket.assigned_provider || 'anthropic');
    setModel(ticket.assigned_model || '');
    setFixVersion(ticket.fix_version || '');
    setTShirtSize(ticket.t_shirt_size || '');
  }, [ticket]);

  if (!ticket || !projectId) return null;

  const providerAvailable = (key) => providerChoices?.providers?.[key]?.available !== false;

  const handleProviderChange = (next) => {
    if (!providerAvailable(next)) return;
    setProvider(next);
    const models = providerChoices?.providers?.[next]?.models ?? [];
    const first = models.find(m => m.selectable !== false);
    setModel(first?.id || '');
  };

  const handleSave = async () => {
    setBusy(true);
    try {
      const updated = await updateTicketProperties(projectId, ticket.id, {
        assigned_provider: provider,
        assigned_model: model,
        fix_version: fixVersion.trim() || null,
        t_shirt_size: tShirtSize.trim().toUpperCase() || null,
      });
      onSaved?.(updated);
      onClose();
    } catch (e) {
      window.alert(e.response?.data?.detail || e.message || 'Failed to save ticket properties');
    } finally {
      setBusy(false);
    }
  };

  const recFix = ticket.recommended_fix_version;
  const recSize = ticket.recommended_t_shirt_size;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal ticket-props-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">
            Properties — {ticket.ticket_key || ticket.id}
          </span>
          <button className="icon-btn" type="button" onClick={onClose}>
            <X size={22} color="#e6edf3" />
          </button>
        </div>

        <div className="ticket-props-body">
          <div className="ticket-props-field">
            <label className="label" htmlFor="ticket-fix-version">Fix version</label>
            <input
              id="ticket-fix-version"
              className="input"
              value={fixVersion}
              onChange={e => setFixVersion(e.target.value)}
              placeholder={recFix ? `Recommended: ${recFix}` : 'e.g. 26.1.0'}
            />
            {recFix && !fixVersion && (
              <button
                type="button"
                className="ticket-props-apply-rec"
                onClick={() => setFixVersion(recFix)}
              >
                Use recommended: {recFix}
              </button>
            )}
          </div>

          <div className="ticket-props-field">
            <label className="label" htmlFor="ticket-tshirt">T-shirt size</label>
            <select
              id="ticket-tshirt"
              className="input"
              value={tShirtSize}
              onChange={e => setTShirtSize(e.target.value)}
            >
              <option value="">Not set{recSize ? ` (rec: ${recSize})` : ''}</option>
              {TSHIRT_SIZES.map(size => (
                <option key={size} value={size}>{size}</option>
              ))}
            </select>
            {recSize && !tShirtSize && (
              <button
                type="button"
                className="ticket-props-apply-rec ticket-props-apply-rec-size"
                onClick={() => setTShirtSize(recSize)}
              >
                Use recommended: {recSize}
              </button>
            )}
          </div>

          <div className="label">Coding model</div>
          <div className="provider-row ticket-props-providers">
            {PROVIDERS.map(p => {
              const available = providerAvailable(p.key);
              const selected = provider === p.key;
              return (
                <button
                  key={p.key}
                  type="button"
                  className={`provider-card${selected ? ' selected' : ''}${!available ? ' disabled' : ''}`}
                  onClick={() => handleProviderChange(p.key)}
                >
                  <div className="provider-icon">{p.icon}</div>
                  <div className={`provider-label${selected ? ' selected' : ''}`}>{p.label}</div>
                </button>
              );
            })}
          </div>

          {providerChoices ? (
            <ModelCardPicker
              provider={provider}
              choices={providerChoices}
              tierLabels={providerChoices.tier_labels}
              selectedModel={model}
              onSelectModel={setModel}
            />
          ) : (
            <div className="hint">Loading model options…</div>
          )}
        </div>

        <div className="ticket-props-footer">
          <button type="button" className="btn-outline" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={handleSave} disabled={busy || !model}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
