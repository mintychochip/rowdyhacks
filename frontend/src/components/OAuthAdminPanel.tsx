import { useEffect, useState } from 'react';
import * as api from '../services/api';
import {
  CARD_BG, INPUT_BG, PRIMARY, SUCCESS, SUCCESS_BG10,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  BORDER, BORDER_LIGHT, INPUT_BORDER, ERROR, ERROR_TEXT, ERROR_BG10, ERROR_BORDER30,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface OAuthProvider {
  name: string;
  display_name: string;
  client_id: string;
  is_active: boolean;
}

export default function OAuthAdminPanel() {
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  const [preset, setPreset] = useState('github');
  const [name, setName] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [adding, setAdding] = useState(false);

  const loadProviders = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.request('/admin/oauth/providers');
      setProviders(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load providers');
    }
    setLoading(false);
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const handleAdd = async () => {
    if (!name.trim() || !clientId.trim() || !clientSecret.trim()) {
      setActionError('Name, Client ID, and Client Secret are required');
      return;
    }
    setAdding(true);
    setActionError('');
    setActionSuccess('');
    try {
      await api.request('/admin/oauth/providers', {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          display_name: name.trim(),
          client_id: clientId.trim(),
          client_secret: clientSecret.trim(),
          preset: preset,
        }),
      });
      setActionSuccess('Provider added successfully');
      setName('');
      setClientId('');
      setClientSecret('');
      setPreset('github');
      await loadProviders();
      setTimeout(() => setActionSuccess(''), 3000);
    } catch (e: any) {
      setActionError(e.message || 'Failed to add provider');
    }
    setAdding(false);
  };

  const handleDeactivate = async (providerName: string) => {
    setActionError('');
    setActionSuccess('');
    try {
      await api.request(`/admin/oauth/providers/${providerName}`, { method: 'DELETE' });
      setActionSuccess(`Provider "${providerName}" deactivated`);
      await loadProviders();
      setTimeout(() => setActionSuccess(''), 3000);
    } catch (e: any) {
      setActionError(e.message || 'Failed to deactivate provider');
    }
  };

  return (
    <div style={{
      background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
      padding: SPACE.lg, marginBottom: SPACE.md,
    }}>
      <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>OAuth Providers</h3>

      {error && (
        <div style={{
          background: ERROR_BG10, border: `1px solid ${ERROR}`, borderRadius: RADIUS.md,
          padding: '10px 16px', marginBottom: SPACE.md, color: ERROR_TEXT, fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {actionError && (
        <div style={{
          background: ERROR_BG10, border: `1px solid ${ERROR}`, borderRadius: RADIUS.md,
          padding: '10px 16px', marginBottom: SPACE.md, color: ERROR_TEXT, fontSize: 14,
        }}>
          {actionError}
        </div>
      )}

      {actionSuccess && (
        <div style={{
          background: SUCCESS_BG10, border: `1px solid ${SUCCESS}`, borderRadius: RADIUS.md,
          padding: '10px 16px', marginBottom: SPACE.md, color: SUCCESS, fontSize: 14,
        }}>
          {actionSuccess}
        </div>
      )}

      {loading ? (
        <p style={{ color: TEXT_MUTED, fontSize: 14 }}>Loading providers...</p>
      ) : providers.length === 0 ? (
        <p style={{ color: TEXT_MUTED, fontSize: 14 }}>No OAuth providers configured yet.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm, marginBottom: SPACE.lg }}>
          {providers.map((provider) => (
            <div key={provider.name} style={{
              padding: SPACE.md, background: INPUT_BG, borderRadius: RADIUS.md,
              border: `1px solid ${BORDER_LIGHT}`, display: 'flex',
              justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <div style={{ fontWeight: 600, color: TEXT_PRIMARY, fontSize: 14 }}>
                  {provider.display_name || provider.name}
                </div>
                <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>
                  {provider.name} · {provider.is_active ? 'Active' : 'Inactive'} · Client ID: {provider.client_id}
                </div>
              </div>
              <button
                onClick={() => handleDeactivate(provider.name)}
                style={{
                  padding: '6px 14px', background: ERROR, border: 'none',
                  borderRadius: RADIUS.sm, color: TEXT_WHITE, fontSize: 13,
                  fontWeight: 600, cursor: 'pointer',
                }}
              >
                Deactivate
              </button>
            </div>
          ))}
        </div>
      )}

      <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: SPACE.md }}>
        <h4 style={{ ...TYPO.h3, marginBottom: SPACE.md, fontSize: 14 }}>Add Provider</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: SPACE.md }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Preset</label>
            <select
              value={preset}
              onChange={(e) => setPreset(e.target.value)}
              style={{
                width: '100%', padding: '10px 14px', background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
                color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
              }}
            >
              <option value="github">GitHub</option>
              <option value="google">Google</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. github"
              style={{
                width: '100%', padding: '10px 14px', background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
                color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Client ID</label>
            <input
              type="text"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="OAuth client ID"
              style={{
                width: '100%', padding: '10px 14px', background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
                color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Client Secret</label>
            <input
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder="OAuth client secret"
              style={{
                width: '100%', padding: '10px 14px', background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
                color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
              }}
            />
          </div>
        </div>
        <button
          onClick={handleAdd}
          disabled={adding}
          style={{
            marginTop: SPACE.md, padding: '10px 24px', background: PRIMARY,
            border: 'none', borderRadius: RADIUS.md, color: TEXT_WHITE,
            fontSize: 14, fontWeight: 600, cursor: adding ? 'not-allowed' : 'pointer',
            opacity: adding ? 0.6 : 1,
          }}
        >
          {adding ? 'Adding...' : 'Add Provider'}
        </button>
      </div>
    </div>
  );
}
