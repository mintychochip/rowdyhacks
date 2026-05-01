import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { PRIMARY, GOLD, SUCCESS, WARNING, ERROR, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE, CARD_BG, INPUT_BG, INPUT_BORDER, BORDER, STATUS_ACCEPTED } from '../theme';

export default function HackathonSetup() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [hackathons, setHackathons] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    loadHackathons();
  }, [user]);

  const loadHackathons = () => {
    api.getHackathons().then(setHackathons).catch(() => {});
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createHackathon({ name, start_date: startDate, end_date: endDate, description: description || undefined });
      setName(''); setDescription(''); setStartDate(''); setEndDate('');
      loadHackathons();
    } catch {}
  };

  const handleViewStats = async (id: string) => {
    try {
      const data = await api.getHackathonStats(id);
      setStats(data);
    } catch {}
  };

  const STATS_COLORS = { Clean: SUCCESS, Review: WARNING, Flagged: ERROR };

  return (
    <div>
      <h2 data-mobile-h1 style={{ fontSize: 24, marginBottom: 20 }}>Hackathons</h2>

      {hackathons.length === 0 && (
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, marginBottom: 16 }}>Create New Hackathon</h3>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Name</label>
              <input value={name} onChange={e => setName(e.target.value)} required
                style={{ padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14 }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Start Date</label>
              <input type="datetime-local" value={startDate} onChange={e => setStartDate(e.target.value)} required
                style={{ padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14 }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>End Date</label>
              <input type="datetime-local" value={endDate} onChange={e => setEndDate(e.target.value)} required
                style={{ padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14 }} />
            </div>
            <div style={{ width: '100%' }}>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Description (optional)</label>
              <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
                placeholder="Describe the hackathon..."
                style={{ padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14, width: '100%', resize: 'vertical', minWidth: 200 }} />
            </div>
            <button type="submit"
              style={{ padding: '8px 20px', background: PRIMARY, border: 'none', borderRadius: 6, color: TEXT_WHITE, fontSize: 14, cursor: 'pointer', height: 38 }}>
              Create
            </button>
          </form>
        </div>
      )}

      {stats && (
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, marginBottom: 12 }}>Statistics</h3>
          <div style={{ display: 'flex', gap: 24 }}>
            <div><span style={{ color: TEXT_MUTED }}>Total: </span><strong>{stats.total_submissions}</strong></div>
            <div><span style={{ color: TEXT_MUTED }}>Completed: </span><strong>{stats.completed}</strong></div>
            <div><span style={{ color: TEXT_MUTED }}>Avg Risk: </span><strong>{stats.avg_risk_score}</strong></div>
            {Object.entries(STATS_COLORS).map(([label, color]) => (
              <div key={label}><span style={{ color }}>{label}: {stats.by_verdict?.[label.toLowerCase()] ?? 0}</span></div>
            ))}
          </div>
          <button onClick={() => setStats(null)} style={{ marginTop: 12, background: 'none', border: 'none', color: TEXT_MUTED, cursor: 'pointer', fontSize: 13 }}>Dismiss</button>
        </div>
      )}

      <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${BORDER}`, textAlign: 'left' }}>
              <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Name</th>
              <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Start</th>
              <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>End</th>
              <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {hackathons.map(h => (
              <tr key={h.id} style={{ borderBottom: '1px solid #080c1a' }}>
                <td style={{ padding: '10px 16px' }}>
                  <Link to={`/hackathons/${h.id}`} style={{ color: PRIMARY, textDecoration: 'none', fontWeight: 600 }}>
                    {h.name}
                  </Link>
                </td>
                <td style={{ padding: '10px 16px', color: TEXT_MUTED }}>{new Date(h.start_date).toLocaleDateString()}</td>
                <td style={{ padding: '10px 16px', color: TEXT_MUTED }}>{new Date(h.end_date).toLocaleDateString()}</td>
                <td style={{ padding: '10px 16px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <Link to={`/hackathons/${h.id}/register`}
                    style={{ background: PRIMARY, border: 'none', borderRadius: 6, padding: '4px 12px', color: TEXT_WHITE, textDecoration: 'none', cursor: 'pointer', fontSize: 12 }}>
                    Register
                  </Link>
                  {user?.role === 'organizer' && (
                    <Link to={`/hackathons/${h.id}/registrations`}
                      style={{ background: `${STATUS_ACCEPTED}20`, border: `1px solid ${STATUS_ACCEPTED}`, borderRadius: 6, padding: '4px 12px', color: STATUS_ACCEPTED, textDecoration: 'none', cursor: 'pointer', fontSize: 12 }}>
                      Manage
                    </Link>
                  )}
                  {user?.role === 'organizer' && (
                    <Link to={`/hackathons/${h.id}/judging/setup`}
                      style={{ background: `${GOLD}20`, border: `1px solid ${GOLD}`, borderRadius: 6, padding: '4px 12px', color: GOLD, textDecoration: 'none', cursor: 'pointer', fontSize: 12 }}>
                      Judging
                    </Link>
                  )}
                  {(user?.role === 'judge' || user?.role === 'organizer') && (
                    <Link to={`/hackathons/${h.id}/judging`}
                      style={{ background: `${PRIMARY}20`, border: `1px solid ${PRIMARY}`, borderRadius: 6, padding: '4px 12px', color: PRIMARY, textDecoration: 'none', cursor: 'pointer', fontSize: 12 }}>
                      {user?.role === 'organizer' ? 'Score' : 'Judge'}
                    </Link>
                  )}
                  <button onClick={() => handleViewStats(h.id)}
                    style={{ background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, padding: '4px 12px', color: TEXT_MUTED, cursor: 'pointer', fontSize: 12 }}>
                    Stats
                  </button>
                </td>
              </tr>
            ))}
            {hackathons.length === 0 && (
              <tr><td colSpan={4} style={{ textAlign: 'center', padding: 24, color: TEXT_MUTED }}>No hackathons created yet.</td></tr>
            )}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}
