import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import {
  PRIMARY, PRIMARY_BG20, CYAN, CYAN_BG20, GOLD, GOLD_BG20,
  SUCCESS, SUCCESS_BG20, WARNING, WARNING_BG20,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, INPUT_BORDER, BORDER,
  TYPO, SPACE, RADIUS,
} from '../theme';

export default function HackathonSetup() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [hackathon, setHackathon] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [regCount, setRegCount] = useState(0);
  const [loading, setLoading] = useState(true);

  // Create form state (only when no hackathon exists)
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    loadData();
  }, [user]);

  const loadData = async () => {
    setLoading(true);
    try {
      const hackathons = await api.getHackathons();
      if (hackathons.length > 0) {
        const h = hackathons[0];
        setHackathon(h);
        // Load stats and registrations in parallel
        const [s, regs] = await Promise.all([
          api.getHackathonStats(h.id).catch(() => null),
          api.getRegistrations({ hackathon_id: h.id }).catch(() => ({ total: 0 })),
        ]);
        setStats(s);
        setRegCount(regs.total ?? 0);
      }
    } catch {}
    setLoading(false);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createHackathon({ name, start_date: startDate, end_date: endDate, description: description || undefined });
      setName(''); setDescription(''); setStartDate(''); setEndDate('');
      loadData();
    } catch {}
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl }}>
        <p style={{ color: TEXT_MUTED }}>Loading...</p>
      </div>
    );
  }

  // No hackathon yet — show create form
  if (!hackathon) {
    return (
      <div style={{ maxWidth: 640, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
        <div style={{ textAlign: 'center', marginBottom: SPACE.xl }}>
          <div style={{ fontSize: 48, marginBottom: SPACE.md }}>🚀</div>
          <h2 style={{ ...TYPO.h1, marginBottom: SPACE.sm }}>Create Your Hackathon</h2>
          <p style={{ color: TEXT_SECONDARY }}>Set up your hackathon event to get started.</p>
        </div>
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg }}>
          <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: SPACE.md }}>
            <div>
              <label style={{ display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 4 }}>Name</label>
              <input value={name} onChange={e => setName(e.target.value)} required
                style={{ width: '100%', padding: '10px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 8, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box' }} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: SPACE.md }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 4 }}>Start Date</label>
                <input type="datetime-local" value={startDate} onChange={e => setStartDate(e.target.value)} required
                  style={{ width: '100%', padding: '10px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 8, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 4 }}>End Date</label>
                <input type="datetime-local" value={endDate} onChange={e => setEndDate(e.target.value)} required
                  style={{ width: '100%', padding: '10px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 8, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box' }} />
              </div>
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 4 }}>Description</label>
              <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3}
                style={{ width: '100%', padding: '10px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 8, color: TEXT_PRIMARY, fontSize: 14, resize: 'vertical', boxSizing: 'border-box' }} />
            </div>
            <button type="submit"
              style={{ padding: '12px 24px', background: PRIMARY, border: 'none', borderRadius: 8, color: TEXT_WHITE, fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>
              Create Hackathon
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Hackathon overview
  const start = new Date(hackathon.start_date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  const end = new Date(hackathon.end_date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  const actionCards = user?.role === 'organizer' ? [
    { label: 'Registrations', desc: 'Review, accept, and manage hacker applications', icon: 'group', color: SUCCESS, bg: SUCCESS_BG20, to: `/hackathons/${hackathon.id}/registrations` },
    { label: 'Judging Setup', desc: 'Create rubric, assign judges, configure scoring', icon: 'gavel', color: GOLD, bg: GOLD_BG20, to: `/hackathons/${hackathon.id}/judging/setup` },
    { label: 'Leaderboard', desc: 'View ELO rankings and results', icon: 'leaderboard', color: CYAN, bg: CYAN_BG20, to: `/hackathons/${hackathon.id}/leaderboard` },
    { label: 'Projects', desc: 'Browse submitted projects and risk scores', icon: 'inventory_2', color: '#ec4899', bg: '#ec489920', to: `/hackathons/${hackathon.id}/projects` },
    { label: 'Tracks', desc: 'Challenge tracks, criteria, and prizes', icon: 'route', color: '#f97316', bg: '#f9731620', to: `/hackathons/${hackathon.id}/tracks` },
    { label: 'Settings', desc: 'WiFi, Discord, schedule, and event config', icon: 'settings', color: '#a78bfa', bg: '#a78bfa20', to: `/hackathons/${hackathon.id}/settings` },
  ] : [
    { label: 'Register', desc: 'Sign up for this hackathon', icon: 'how_to_reg', color: SUCCESS, bg: SUCCESS_BG20, to: `/hackathons/${hackathon.id}/register` },
    { label: 'Tracks', desc: 'Explore challenge tracks and prizes', icon: 'route', color: '#f97316', bg: '#f9731620', to: `/hackathons/${hackathon.id}/tracks` },
    { label: 'Leaderboard', desc: 'See who\'s winning', icon: 'leaderboard', color: CYAN, bg: CYAN_BG20, to: `/hackathons/${hackathon.id}/leaderboard` },
  ];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      {/* Hero */}
      <div style={{
        background: `linear-gradient(135deg, ${PRIMARY_BG20} 0%, ${CYAN_BG20} 100%)`,
        border: `1px solid ${BORDER}`,
        borderRadius: RADIUS.lg,
        padding: isMobile ? SPACE.lg : SPACE.xl,
        marginBottom: SPACE.xl,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.md, marginBottom: SPACE.md }}>
          <div style={{ fontSize: 40 }}>🛸</div>
          <div>
            <h1 style={{ ...TYPO.h1, margin: 0, fontSize: isMobile ? 24 : 32 }}>{hackathon.name}</h1>
            <p style={{ color: TEXT_SECONDARY, marginTop: 4 }}>{start} – {end}</p>
          </div>
        </div>
        {hackathon.description && (
          <p style={{ color: TEXT_MUTED, lineHeight: 1.6 }}>{hackathon.description}</p>
        )}
      </div>

      {/* Stat Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
        gap: SPACE.md,
        marginBottom: SPACE.xl,
      }}>
        {[
          { label: 'Registrations', value: regCount, color: CYAN },
          { label: 'Submissions', value: stats?.total_submissions ?? 0, color: PRIMARY },
          { label: 'Checked In', value: stats?.by_verdict ? (stats.by_verdict.clean ?? 0) + (stats.by_verdict.review ?? 0) + (stats.by_verdict.flagged ?? 0) : 0, color: SUCCESS },
          { label: 'Avg Risk Score', value: stats?.avg_risk_score ? Math.round(stats.avg_risk_score) : '–', color: WARNING },
        ].map(s => (
          <div key={s.label} style={{
            background: CARD_BG, border: `1px solid ${BORDER}`,
            borderRadius: RADIUS.md, padding: SPACE.md, textAlign: 'center',
          }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Action Cards */}
      <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>
        {user?.role === 'organizer' ? 'Organizer Tools' : 'Quick Actions'}
      </h3>
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',
        gap: SPACE.md,
      }}>
        {actionCards.map(card => (
          <Link
            key={card.label}
            to={card.to}
            style={{
              background: CARD_BG,
              border: `1px solid ${BORDER}`,
              borderRadius: RADIUS.md,
              padding: SPACE.md,
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'flex-start',
              gap: SPACE.sm,
              transition: 'border-color 0.2s, transform 0.2s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = card.color; (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = BORDER; (e.currentTarget as HTMLElement).style.transform = ''; }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 24, color: card.color }}>{card.icon}</span>
            <div>
              <div style={{ fontWeight: 600, color: TEXT_PRIMARY, marginBottom: 2 }}>{card.label}</div>
              <div style={{ fontSize: 12, color: TEXT_MUTED }}>{card.desc}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
