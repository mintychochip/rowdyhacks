import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { getMyRegistrations, getHackathons } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import { PRIMARY, SUCCESS, ERROR_TEXT, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE, INPUT_BG, INPUT_BORDER, CARD_BG, BORDER, BORDER_LIGHT, TYPO, SPACE, RADIUS } from '../theme';

interface Registration {
  id: string; hackathon_id: string; status: string;
  team_name?: string; registered_at: string; accepted_at?: string; checked_in_at?: string;
  qr_token?: string;
  linkedin_url?: string; github_url?: string; resume_url?: string;
  experience_level?: string; t_shirt_size?: string; phone?: string;
  dietary_restrictions?: string; what_build?: string; why_participate?: string;
}

interface Hackathon { id: string; name: string; }

export default function RegistrationsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [hackathons, setHackathons] = useState<Hackathon[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { setLoading(false); return; }
    Promise.all([getMyRegistrations(), getHackathons()])
      .then(([regData, hackData]) => {
        setRegistrations(regData.registrations || []);
        setHackathons(hackData || []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user]);

  const getHackathonName = (id: string) => hackathons.find(h => h.id === id)?.name || 'Unknown';

  if (!user) return <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>Please log in.</div>;
  if (loading) return <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>Loading...</div>;

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      <h1 style={{ ...TYPO.h1, marginBottom: SPACE.lg }}>Your Application</h1>

      {error && <div style={{ background: '#ff444420', border: '1px solid #ff4444', borderRadius: 8, padding: 12, marginBottom: 16, color: ERROR_TEXT, fontSize: 14 }}>{error}</div>}

      {registrations.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, color: TEXT_MUTED }}>
          <p style={{ fontSize: 16, marginBottom: 12 }}>You haven't applied yet.</p>
          <Link to="/apply" style={{ color: PRIMARY, fontWeight: 600, textDecoration: 'none' }}>Apply now &rarr;</Link>
        </div>
      )}

      {registrations.map(reg => (
        <div key={reg.id} style={{
          background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
          padding: SPACE.lg, marginBottom: SPACE.md,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: SPACE.sm }}>
            <div>
              <div style={{ fontSize: 12, color: TEXT_MUTED, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>
                {getHackathonName(reg.hackathon_id)}
              </div>
              <div style={{ fontWeight: 600, fontSize: 17 }}>
                {reg.team_name || user?.name}
              </div>
              <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>
                Applied {new Date(reg.registered_at).toLocaleDateString()}
                {reg.accepted_at && ` · Accepted ${new Date(reg.accepted_at).toLocaleDateString()}`}
                {reg.checked_in_at && ` · Checked in ${new Date(reg.checked_in_at).toLocaleString()}`}
              </div>
            </div>
            <StatusBadge status={reg.status} />
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: SPACE.sm }}>
            <button onClick={() => navigate(`/hackathons/${reg.hackathon_id}`)}
              style={{ padding: '8px 16px', background: PRIMARY, border: 'none', borderRadius: 6, color: TEXT_WHITE, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
              View Application
            </button>
            {(reg.status === 'accepted' || reg.status === 'checked_in') && (
              <button onClick={() => navigate(`/hackathons/${reg.hackathon_id}/hacker-dashboard`)}
                style={{ padding: '8px 16px', background: SUCCESS, border: 'none', borderRadius: 6, color: '#000', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                Live Dashboard
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
