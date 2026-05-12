import { useEffect, useState } from 'react';
import * as api from '../services/api';
import {
  CARD_BG, INPUT_BG, PRIMARY, SUCCESS, SUCCESS_BG10,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  BORDER, BORDER_LIGHT, INPUT_BORDER, ERROR, ERROR_TEXT, ERROR_BG10, ERROR_BORDER30,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface InviteCode {
  code: string;
  role: string;
  uses_remaining: number;
  expires_at: string | null;
  created_at: string;
}

interface InviteCodeManagerProps {
  hackathonId: string;
}

export default function InviteCodeManager({ hackathonId }: InviteCodeManagerProps) {
  const [codes, setCodes] = useState<InviteCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  const [count, setCount] = useState(10);
  const [role, setRole] = useState('participant');
  const [generating, setGenerating] = useState(false);

  const loadCodes = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.request(`/hackathons/${hackathonId}/invites`);
      setCodes(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load invite codes');
    }
    setLoading(false);
  };

  useEffect(() => {
    if (hackathonId) {
      loadCodes();
    }
  }, [hackathonId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setActionError('');
    setActionSuccess('');
    try {
      const res = await api.request(`/hackathons/${hackathonId}/invites`, {
        method: 'POST',
        body: JSON.stringify({ count, role }),
      });
      setActionSuccess(`Generated ${res.count} invite code(s)`);
      setCount(10);
      setRole('participant');
      await loadCodes();
      setTimeout(() => setActionSuccess(''), 3000);
    } catch (e: any) {
      setActionError(e.message || 'Failed to generate invite codes');
    }
    setGenerating(false);
  };

  const handleRevoke = async (code: string) => {
    setActionError('');
    setActionSuccess('');
    try {
      await api.request(`/hackathons/invites/${code}`, { method: 'DELETE' });
      setActionSuccess(`Invite code ${code} revoked`);
      await loadCodes();
      setTimeout(() => setActionSuccess(''), 3000);
    } catch (e: any) {
      setActionError(e.message || 'Failed to revoke invite code');
    }
  };

  return (
    <div style={{
      background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
      padding: SPACE.lg, marginBottom: SPACE.md,
    }}>
      <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>Invite Codes</h3>

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
        <p style={{ color: TEXT_MUTED, fontSize: 14 }}>Loading invite codes...</p>
      ) : codes.length === 0 ? (
        <p style={{ color: TEXT_MUTED, fontSize: 14 }}>No invite codes generated yet.</p>
      ) : (
        <div style={{ marginBottom: SPACE.lg, overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                <th style={{ textAlign: 'left', padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_MUTED, fontSize: 12, fontWeight: 600 }}>Code</th>
                <th style={{ textAlign: 'left', padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_MUTED, fontSize: 12, fontWeight: 600 }}>Role</th>
                <th style={{ textAlign: 'left', padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_MUTED, fontSize: 12, fontWeight: 600 }}>Uses Left</th>
                <th style={{ textAlign: 'left', padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_MUTED, fontSize: 12, fontWeight: 600 }}>Expires</th>
                <th style={{ textAlign: 'right', padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_MUTED, fontSize: 12, fontWeight: 600 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {codes.map((code) => (
                <tr key={code.code} style={{ borderBottom: `1px solid ${BORDER_LIGHT}` }}>
                  <td style={{ padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_PRIMARY, fontFamily: 'monospace', fontSize: 13 }}>
                    {code.code}
                  </td>
                  <td style={{ padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_PRIMARY }}>
                    {code.role}
                  </td>
                  <td style={{ padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_PRIMARY }}>
                    {code.uses_remaining}
                  </td>
                  <td style={{ padding: `${SPACE.sm}px ${SPACE.md}px`, color: TEXT_SECONDARY }}>
                    {code.expires_at ? new Date(code.expires_at).toLocaleDateString() : 'Never'}
                  </td>
                  <td style={{ padding: `${SPACE.sm}px ${SPACE.md}px`, textAlign: 'right' }}>
                    <button
                      onClick={() => handleRevoke(code.code)}
                      style={{
                        padding: '4px 10px', background: ERROR, border: 'none',
                        borderRadius: RADIUS.sm, color: TEXT_WHITE, fontSize: 12,
                        fontWeight: 600, cursor: 'pointer',
                      }}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: SPACE.md }}>
        <h4 style={{ ...TYPO.h3, marginBottom: SPACE.md, fontSize: 14 }}>Generate Codes</h4>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: SPACE.md }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Count</label>
            <input
              type="number"
              min={1}
              max={100}
              value={count}
              onChange={(e) => setCount(Math.max(1, Math.min(100, Number(e.target.value))))}
              style={{
                width: '100%', padding: '10px 14px', background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
                color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={{
                width: '100%', padding: '10px 14px', background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
                color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
              }}
            >
              <option value="participant">Participant</option>
              <option value="judge">Judge</option>
            </select>
          </div>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          style={{
            marginTop: SPACE.md, padding: '10px 24px', background: PRIMARY,
            border: 'none', borderRadius: RADIUS.md, color: TEXT_WHITE,
            fontSize: 14, fontWeight: 600, cursor: generating ? 'not-allowed' : 'pointer',
            opacity: generating ? 0.6 : 1,
          }}
        >
          {generating ? 'Generating...' : 'Generate'}
        </button>
      </div>
    </div>
  );
}
