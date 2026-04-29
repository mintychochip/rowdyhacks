import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getMyRegistrations, getHackathons } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { PRIMARY, ERROR, ERROR_BG20, ERROR_TEXT, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE, INPUT_BG, INPUT_BORDER, BORDER, BORDER_LIGHT } from '../theme';

interface Registration {
  id: string;
  hackathon_id: string;
  status: string;
  team_name?: string;
  registered_at: string;
  accepted_at?: string;
  checked_in_at?: string;
  qr_token?: string;
}

interface Hackathon {
  id: string;
  name: string;
}

export default function RegistrationsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [hackathons, setHackathons] = useState<Hackathon[]>([]);
  const [expandedQr, setExpandedQr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { setLoading(false); return; }
    Promise.all([
      getMyRegistrations(),
      getHackathons(),
    ])
      .then(([regData, hackData]) => {
        setRegistrations(regData.registrations || []);
        setHackathons(hackData || []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user]);

  const getHackathonName = (hackathonId: string): string => {
    const hack = hackathons.find(h => h.id === hackathonId);
    return hack ? hack.name : 'Unknown Hackathon';
  };

  if (!user) {
    return (
      <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
        Please log in to view registrations.
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
        Loading...
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 40 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <h1 style={{ fontSize: 24 }}>My Registrations</h1>
        <button
          onClick={() => navigate('/hackathons')}
          style={{
            padding: '10px 20px',
            background: PRIMARY,
            border: 'none',
            borderRadius: 8,
            color: TEXT_WHITE,
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Register for Hackathon
        </button>
      </div>

      {error && (
        <div style={{
          background: ERROR_BG20,
          border: `1px solid ${ERROR}`,
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
          color: ERROR_TEXT,
          fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {!loading && registrations.length === 0 && (
        <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
          <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.3 }}>--</div>
          <div style={{ fontSize: 16, marginBottom: 8 }}>No registrations yet</div>
          <div style={{ fontSize: 13, marginBottom: 20 }}>
            Browse hackathons to register for one.
          </div>
          <button
            onClick={() => navigate('/hackathons')}
            style={{
              padding: '10px 24px',
              background: PRIMARY,
              border: 'none',
              borderRadius: 8,
              color: TEXT_WHITE,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Browse Hackathons
          </button>
        </div>
      )}

      {registrations.map(reg => (
        <div
          key={reg.id}
          style={{
            background: INPUT_BG,
            border: `1px solid ${BORDER_LIGHT}`,
            borderRadius: 12,
            padding: 18,
            marginBottom: 12,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8 }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontSize: 13, color: PRIMARY, marginBottom: 2, fontWeight: 500 }}>
                {getHackathonName(reg.hackathon_id)}
              </div>
              <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>
                {reg.team_name || 'Solo Participant'}
              </div>
              <div style={{ fontSize: 13, color: TEXT_MUTED }}>
                Registered: {new Date(reg.registered_at).toLocaleDateString()}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <StatusBadge status={reg.status} />
            </div>
          </div>

          {reg.qr_token && (
            <div style={{ marginTop: 12 }}>
              <button
                onClick={() => setExpandedQr(expandedQr === reg.id ? null : reg.id)}
                style={{
                  background: 'none',
                  border: `1px solid ${INPUT_BORDER}`,
                  borderRadius: 6,
                  padding: '4px 12px',
                  color: TEXT_MUTED,
                  cursor: 'pointer',
                  fontSize: 12,
                }}
              >
                {expandedQr === reg.id ? 'Hide QR Token' : 'Show QR Token'}
              </button>
              {expandedQr === reg.id && (
                <div style={{
                  marginTop: 8,
                  padding: '8px 12px',
                  background: '#080c1a',
                  borderRadius: 6,
                  border: `1px solid ${BORDER_LIGHT}`,
                  fontFamily: 'monospace',
                  fontSize: 12,
                  color: TEXT_MUTED,
                  wordBreak: 'break-all',
                }}>
                  {reg.qr_token}
                </div>
              )}
            </div>
          )}

          <div style={{ marginTop: 12 }}>
            <button
              onClick={() => navigate(`/registrations/${reg.id}`)}
              style={{
                padding: '8px 16px',
                background: PRIMARY,
                border: 'none',
                borderRadius: 6,
                color: TEXT_WHITE,
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              View Details
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
