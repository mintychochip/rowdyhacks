import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { PRIMARY, TEXT_MUTED, TEXT_WHITE, SPACE, RADIUS } from '../theme';

export default function JudgeRedirect() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [hackathonId, setHackathonId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) { setLoading(false); return; }
    api.getHackathons().then(hacks => {
      if (hacks && hacks.length > 0) {
        setHackathonId(hacks[0].id);
      }
    }).finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    if (hackathonId) {
      navigate(`/hackathons/${hackathonId}/judging`, { replace: true });
    }
  }, [hackathonId, navigate]);

  if (!user) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
        Please <Link to="/auth" style={{ color: PRIMARY }}>sign in</Link> as a judge.
      </div>
    );
  }

  if (loading) return <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>Loading...</div>;

  if (!hackathonId) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
        No active hackathon found.
      </div>
    );
  }

  return null;
}
