import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { PRIMARY, SUCCESS, SUCCESS_BG10, WARNING, WARNING_BG10, ERROR, ERROR_BG10, ERROR_TEXT, TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, TEXT_WHITE, CARD_BG, INPUT_BG, INPUT_BORDER, BORDER, TYPO, SPACE, RADIUS, SHADOW } from '../theme';

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string }> = {
    completed: { bg: SUCCESS_BG10, color: SUCCESS },
    failed: { bg: ERROR_BG10, color: ERROR },
    analyzing: { bg: WARNING_BG10, color: WARNING },
    pending: { bg: 'rgba(245,158,11,0.1)', color: '#f59e0b' },
  };
  const s = map[status] || { bg: '#333', color: '#888' };
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: RADIUS.full,
      fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5,
      background: s.bg, color: s.color,
    }}>
      {status}
    </span>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const map: Record<string, { color: string; label: string }> = {
    clean: { color: SUCCESS, label: 'Clean' },
    review: { color: WARNING, label: 'Review' },
    flagged: { color: ERROR, label: 'Flagged' },
  };
  const v = map[verdict] || { color: TEXT_DIM, label: verdict || 'Unknown' };
  return <span style={{ fontSize: 12, fontWeight: 600, color: v.color }}>{v.label}</span>;
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [hackathons, setHackathons] = useState<any[]>([]);
  const [selectedHackathon, setSelectedHackathon] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    api.getHackathons().then(setHackathons).catch(() => {});
    loadSubmissions();
  }, [user, selectedHackathon, filterStatus, page]);

  const loadSubmissions = async () => {
    setLoading(true);
    try {
      const params: any = { page };
      if (selectedHackathon) params.hackathon_id = selectedHackathon;
      if (filterStatus) params.status = filterStatus;
      const data = await api.getDashboard(params);
      setSubmissions(data.submissions);
      setTotal(data.total);
    } catch {} finally { setLoading(false); }
  };

  const stats = [
    { label: 'Total', value: total, color: PRIMARY },
    { label: 'Clean', value: submissions.filter(s => s.verdict === 'clean').length, color: SUCCESS },
    { label: 'Review', value: submissions.filter(s => s.verdict === 'review').length, color: WARNING },
    { label: 'Flagged', value: submissions.filter(s => s.verdict === 'flagged').length, color: ERROR },
  ];

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: SPACE.lg }}>
        <div>
          <h1 data-mobile-h1 style={{ ...TYPO.h1, color: TEXT_PRIMARY, marginBottom: SPACE.xs }}>Dashboard</h1>
          <p style={{ ...TYPO['body-sm'], color: TEXT_MUTED }}>
            {total} submissions across {hackathons.length} hackathons
          </p>
        </div>
        <Link to="/hackathons" style={{
          padding: '8px 18px', background: PRIMARY, borderRadius: RADIUS.sm,
          color: TEXT_WHITE, textDecoration: 'none', ...TYPO['body-sm'], fontWeight: 600,
        }}>
          + New Hackathon
        </Link>
      </div>

      {/* Stat Cards */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: SPACE.md, marginBottom: SPACE.lg,
      }}>
        {stats.map(stat => (
          <div key={stat.label} style={{
            background: CARD_BG, border: `1px solid ${BORDER}`,
            borderRadius: RADIUS.lg, padding: '20px 24px',
            boxShadow: SHADOW.card,
          }}>
            <div style={{ ...TYPO['label-caps'], color: TEXT_MUTED, marginBottom: 8 }}>
              {stat.label}
            </div>
            <div style={{ ...TYPO.h1, color: stat.color, fontSize: 36 }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{
        display: 'flex', gap: SPACE.sm + 4, marginBottom: SPACE.md, flexWrap: 'wrap', alignItems: 'center',
        background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: `${SPACE.md}px ${SPACE.lg}px`,
      }}>
        <span style={{ ...TYPO['label-caps'], color: TEXT_MUTED, marginRight: SPACE.sm }}>FILTERS</span>
        <select value={selectedHackathon} onChange={e => { setSelectedHackathon(e.target.value); setPage(1); }}
          style={{
            padding: '8px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
            borderRadius: RADIUS.sm, color: '#fff', fontSize: 13, outline: 'none', fontFamily: 'inherit', minWidth: 160,
          }}>
          <option value="">All Hackathons</option>
          {hackathons.map((h: any) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <select value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1); }}
          style={{
            padding: '8px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
            borderRadius: RADIUS.sm, color: '#fff', fontSize: 13, outline: 'none', fontFamily: 'inherit',
          }}>
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="analyzing">Analyzing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <div style={{ flex: 1 }} />
        <span style={{ ...TYPO['body-sm'], color: TEXT_DIM }}>{total} results</span>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>Loading...</div>
      ) : (
        <div style={{
          background: CARD_BG, border: `1px solid ${BORDER}`,
          borderRadius: RADIUS.lg, overflow: 'hidden', boxShadow: SHADOW.card,
        }}>
          <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${BORDER}`, background: 'rgba(255,255,255,0.02)' }}>
                {['Project', 'Status', 'Risk Score', 'Verdict', 'Date'].map(h => (
                  <th key={h} style={{
                    padding: '12px 20px', ...TYPO['label-caps'],
                    color: TEXT_MUTED, textAlign: 'left',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {submissions.map(sub => (
                <tr key={sub.id} onClick={() => navigate(`/report/${sub.id}`)}
                  style={{
                    borderBottom: `1px solid ${BORDER}`,
                    cursor: 'pointer', transition: 'background 0.12s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(26,92,231,0.06)')}
                  onMouseLeave={e => (e.currentTarget.style.background = '')}>
                  <td style={{ padding: '14px 20px', ...TYPO['body-sm'], fontWeight: 500, color: TEXT_PRIMARY }}>
                    {sub.project_title || (sub.devpost_url ? new URL(sub.devpost_url).pathname.split('/').pop() : 'Untitled')}
                  </td>
                  <td style={{ padding: '14px 20px' }}><StatusBadge status={sub.status} /></td>
                  <td style={{
                    padding: '14px 20px', fontFamily: "'Space Mono', monospace", fontSize: 15, fontWeight: 700,
                    color: (sub.risk_score ?? 0) <= 30 ? SUCCESS : (sub.risk_score ?? 0) <= 60 ? WARNING : ERROR,
                  }}>
                    {sub.risk_score ?? '—'}
                  </td>
                  <td style={{ padding: '14px 20px' }}><VerdictBadge verdict={sub.verdict} /></td>
                  <td style={{ padding: '14px 20px', ...TYPO['body-sm'], color: TEXT_MUTED }}>
                    {sub.created_at ? new Date(sub.created_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          {submissions.length === 0 && (
            <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
              <span className="material-symbols-outlined" style={{ fontSize: 36, display: 'block', marginBottom: 12, color: TEXT_DIM }}>inbox</span>
              <div style={{ ...TYPO['body-lg'], marginBottom: 4 }}>No submissions yet</div>
              <div style={{ ...TYPO['body-sm'] }}>Analyze a Devpost URL to get started</div>
            </div>
          )}
          {total > 20 && (
            <div style={{
              display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12,
              padding: '14px 0', borderTop: `1px solid ${BORDER}`,
            }}>
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                style={{
                  padding: '6px 16px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
                  borderRadius: RADIUS.sm, color: '#fff', fontFamily: 'inherit',
                  cursor: page <= 1 ? 'not-allowed' : 'pointer', opacity: page <= 1 ? 0.4 : 1, fontSize: 13,
                }}>
                Previous
              </button>
              <span style={{ ...TYPO['body-sm'], color: TEXT_MUTED }}>Page {page} of {Math.ceil(total / 20)}</span>
              <button disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}
                style={{
                  padding: '6px 16px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
                  borderRadius: RADIUS.sm, color: '#fff', fontFamily: 'inherit',
                  cursor: page * 20 >= total ? 'not-allowed' : 'pointer', opacity: page * 20 >= total ? 0.4 : 1, fontSize: 13,
                }}>
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
