import { useState, useEffect } from 'react';
import { getLinkedAccounts, unlinkProvider, getOAuthLinkUrl } from '../services/api';
import { CARD_BG, TEXT_PRIMARY, TEXT_MUTED, BORDER, INPUT_BORDER, ERROR_TEXT, SUCCESS, TYPO, RADIUS, SPACE } from '../theme';
import { useToast } from '../contexts/ToastContext';

type LinkedState = {
  linked: string[];
  has_password: boolean;
};

const PROVIDER_INFO: Record<string, { label: string; icon: string }> = {
  google: { label: 'Google', icon: 'login' },
  github: { label: 'GitHub', icon: 'code' },
  discord: { label: 'Discord', icon: 'chat' },
  apple: { label: 'Apple', icon: 'fingerprint' },
};

export default function LinkedAccounts() {
  const [state, setState] = useState<LinkedState | null>(null);
  const [loading, setLoading] = useState(true);
  const [unlinking, setUnlinking] = useState<string | null>(null);
  const { showToast } = useToast();

  const fetchState = async () => {
    try {
      const data = await getLinkedAccounts();
      setState(data);
    } catch {
      // Not authenticated or error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchState(); }, []);

  const handleUnlink = async (provider: string) => {
    setUnlinking(provider);
    try {
      await unlinkProvider(provider);
      setState(prev => prev ? { ...prev, linked: prev.linked.filter(p => p !== provider) } : prev);
      showToast(`${PROVIDER_INFO[provider]?.label || provider} disconnected.`);
    } catch (err: any) {
      showToast(err.message || 'Failed to disconnect.');
    } finally {
      setUnlinking(null);
    }
  };

  if (loading) return <div style={{ color: TEXT_MUTED }}>Loading...</div>;
  if (!state) return null;

  const canUnlink = (provider: string) => {
    const otherLinked = state.linked.filter(p => p !== provider);
    return otherLinked.length > 0 || state.has_password;
  };

  return (
    <div style={{ marginTop: SPACE.lg }}>
      <h3 style={{ ...TYPO.h3, color: TEXT_PRIMARY, marginBottom: SPACE.md }}>Linked Accounts</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
        {Object.entries(PROVIDER_INFO).map(([provider, info]) => {
          const isLinked = state.linked.includes(provider);
          return (
            <div key={provider} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 16px', background: CARD_BG, border: `1px solid ${BORDER}`,
              borderRadius: RADIUS.md,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 24, color: TEXT_PRIMARY }}>
                  {info.icon}
                </span>
                <div>
                  <div style={{ fontWeight: 600, color: TEXT_PRIMARY }}>{info.label}</div>
                  <div style={{ fontSize: 13, color: isLinked ? SUCCESS : TEXT_MUTED }}>
                    {isLinked ? 'Connected' : 'Not connected'}
                  </div>
                </div>
              </div>
              {isLinked ? (
                <button
                  onClick={() => handleUnlink(provider)}
                  disabled={!canUnlink(provider) || unlinking === provider}
                  title={!canUnlink(provider) ? 'Set a password before disconnecting your only login method' : `Disconnect ${info.label}`}
                  style={{
                    background: 'none', border: `1px solid ${!canUnlink(provider) ? BORDER : '#ff4444'}`,
                    borderRadius: RADIUS.sm, padding: '4px 12px',
                    cursor: !canUnlink(provider) ? 'not-allowed' : 'pointer',
                    color: !canUnlink(provider) ? TEXT_MUTED : ERROR_TEXT,
                    fontSize: 13, opacity: !canUnlink(provider) ? 0.5 : 1,
                  }}
                >
                  {unlinking === provider ? '...' : 'Disconnect'}
                </button>
              ) : (
                <a
                  href={getOAuthLinkUrl(provider)}
                  style={{
                    background: 'none', border: `1px solid ${INPUT_BORDER}`,
                    borderRadius: RADIUS.sm, padding: '4px 12px', cursor: 'pointer',
                    color: TEXT_PRIMARY, fontSize: 13, textDecoration: 'none',
                  }}
                >
                  Connect
                </a>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
