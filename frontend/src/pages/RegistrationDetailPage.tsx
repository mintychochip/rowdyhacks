import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { getRegistration } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import QRCodeDisplay from '../components/QRCodeDisplay';
import WalletButtons from '../components/WalletButtons';
import { PRIMARY, ERROR_TEXT, TEXT_PRIMARY, TEXT_MUTED, INPUT_BG, INPUT_BORDER, BORDER_LIGHT, STATUS_ACCEPTED, STATUS_REJECTED, INFO } from '../theme';

interface Registration {
  id: string;
  hackathon_id: string;
  status: string;
  team_name?: string;
  team_members?: string[];
  registered_at: string;
  accepted_at?: string;
  checked_in_at?: string;
  rejected_at?: string;
  qr_token?: string;
}

export default function RegistrationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isMobile } = useMediaQuery();
  const [reg, setReg] = useState<Registration | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id || !user) { setLoading(false); return; }
    getRegistration(id)
      .then(async (data) => {
        setReg(data);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, user]);

  if (!user) {
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? 30 : 60, color: TEXT_MUTED }}>
        Please log in.
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? 30 : 60, color: TEXT_MUTED }}>
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? 30 : 60 }}>
        <div style={{ color: ERROR_TEXT, marginBottom: 16 }}>{error}</div>
        <button
          onClick={() => navigate('/registrations')}
          style={{
            padding: '10px 20px',
            background: PRIMARY,
            border: 'none',
            borderRadius: 8,
            color: '#fff',
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          Back to Registrations
        </button>
      </div>
    );
  }

  if (!reg) {
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? 30 : 60, color: TEXT_MUTED }}>
        Registration not found.
      </div>
    );
  }

  const scanUrl = reg.qr_token
    ? `${window.location.origin}/api/checkin/scan?token=${reg.qr_token}`
    : '';

  return (
    <div style={{ maxWidth: 520, margin: '0 auto', padding: isMobile ? 14 : 40 }}>
      <button
        onClick={() => navigate('/registrations')}
        style={{
          background: 'none',
          border: `1px solid ${INPUT_BORDER}`,
          borderRadius: 6,
          padding: '6px 14px',
          color: TEXT_MUTED,
          cursor: 'pointer',
          fontSize: 13,
          marginBottom: 20,
        }}
      >
        &larr; Back to Registrations
      </button>

      <div style={{
        background: INPUT_BG,
        border: `1px solid ${BORDER_LIGHT}`,
        borderRadius: 12,
        padding: 28,
        textAlign: 'center',
      }}>
        <StatusBadge status={reg.status} />

        <h1 style={{ fontSize: 24, marginTop: 16, marginBottom: 4 }}>
          {reg.team_name || 'Solo Participant'}
        </h1>

        {reg.team_members && reg.team_members.length > 0 && (
          <p style={{ color: TEXT_MUTED, fontSize: 14, marginTop: 8 }}>
            Team: {reg.team_members.join(', ')}
          </p>
        )}

        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13 }}>
          <div style={{ color: TEXT_MUTED }}>
            Registered: {new Date(reg.registered_at).toLocaleDateString()}
          </div>
          {reg.accepted_at && (
            <div style={{ color: STATUS_ACCEPTED }}>
              Accepted: {new Date(reg.accepted_at).toLocaleDateString()}
            </div>
          )}
          {reg.rejected_at && (
            <div style={{ color: STATUS_REJECTED }}>
              Rejected: {new Date(reg.rejected_at).toLocaleDateString()}
            </div>
          )}
          {reg.checked_in_at && (
            <div style={{ color: INFO }}>
              Checked in: {new Date(reg.checked_in_at).toLocaleString()}
            </div>
          )}
        </div>

        {reg.status === 'accepted' && reg.qr_token && (
          <>
            <div style={{ marginTop: 24, marginBottom: 24, display: 'flex', justifyContent: 'center' }}>
              <QRCodeDisplay token={scanUrl} size={280} />
            </div>

            <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 16, wordBreak: 'break-all', fontFamily: "'Space Mono', monospace" }}>
              Token: {reg.qr_token}
            </div>

            <WalletButtons />
          </>
        )}
      </div>
    </div>
  );
}
