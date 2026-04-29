import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { registerForHackathon } from '../services/api';
import { PRIMARY, PRIMARY_DISABLED, ERROR_TEXT, TEXT_MUTED, INPUT_BORDER } from '../theme';

export default function RegisterPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [teamName, setTeamName] = useState('');
  const [members, setMembers] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!user) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <p style={{ color: TEXT_MUTED }}>Please log in to register.</p>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const memberList = members.split(',').map(m => m.trim()).filter(Boolean);
      await registerForHackathon(id, {
        team_name: teamName || undefined,
        team_members: memberList.length > 0 ? memberList : undefined,
      });
      navigate('/registrations');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%', padding: '10px 12px', background: '#0d1433', border: `1px solid ${INPUT_BORDER}`,
    borderRadius: 8, color: '#fff', fontSize: 14, boxSizing: 'border-box' as const,
  };

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: 40 }}>
      <h1 style={{ fontSize: 24, marginBottom: 24 }}>Register for Hackathon</h1>
      {error && <div style={{ color: ERROR_TEXT, marginBottom: 16 }}>{error}</div>}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, color: TEXT_MUTED, fontSize: 14 }}>Team Name (optional)</label>
          <input type="text" value={teamName} onChange={e => setTeamName(e.target.value)} maxLength={200}
            style={inputStyle} placeholder="My Awesome Team" />
        </div>
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: 'block', marginBottom: 6, color: TEXT_MUTED, fontSize: 14 }}>Team Members (comma-separated, optional)</label>
          <input type="text" value={members} onChange={e => setMembers(e.target.value)}
            style={inputStyle} placeholder="Alice, Bob, Charlie" />
        </div>
        <button type="submit" disabled={loading} style={{
          width: '100%', padding: '12px 0', background: loading ? PRIMARY_DISABLED : PRIMARY,
          border: 'none', borderRadius: 8, color: '#fff', fontSize: 16, fontWeight: 600, cursor: 'pointer',
        }}>
          {loading ? 'Registering...' : 'Register'}
        </button>
      </form>
    </div>
  );
}
