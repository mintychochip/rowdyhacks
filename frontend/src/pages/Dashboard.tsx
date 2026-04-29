import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { PRIMARY, SUCCESS, SUCCESS_BG20, WARNING, WARNING_BG20, ERROR, ERROR_BG20, TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, TEXT_WHITE, CARD_BG, INPUT_BG, INPUT_BORDER, BORDER } from '../theme';

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

  const handleRunSimilarity = async () => {
    if (!selectedHackathon) return;
    try {
      await api.runSimilarity(selectedHackathon);
      loadSubmissions();
    } catch {}
  };

  const stats = {
    total: submissions.length,
    clean: submissions.filter(s => s.verdict === 'clean').length,
    flagged: submissions.filter(s => s.verdict === 'flagged').length,
    review: submissions.filter(s => s.verdict === 'review').length,
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700 }}>Dashboard</h2>
        <Link to="/hackathons" style={{ color: PRIMARY, textDecoration: 'none', fontSize: 13, fontWeight: 500 }}>+ New Hackathon</Link>
      </div>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'Total', value: stats.total, color: PRIMARY },
          { label: 'Clean', value: stats.clean, color: SUCCESS },
          { label: 'Review', value: stats.review, color: WARNING },
          { label: 'Flagged', value: stats.flagged, color: ERROR },
        ].map(stat => (
          <div key={stat.label} style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 10, padding: '16px 20px', textAlign: 'center' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: stat.color }}>{stat.value}</div>
            <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2, textTransform: 'uppercase', letterSpacing: 1 }}>{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <select value={selectedHackathon} onChange={e => { setSelectedHackathon(e.target.value); setPage(1); }}
          style={{ padding: '9px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 8, color: '#fff', fontSize: 13, outline: 'none', minWidth: 160 }}>
          <option value="">All Hackathons</option>
          {hackathons.map((h: any) => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <select value={filterStatus} onChange={e => { setFilterStatus(e.target.value); setPage(1); }}
          style={{ padding: '9px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 8, color: '#fff', fontSize: 13, outline: 'none' }}>
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="analyzing">Analyzing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: TEXT_DIM }}>{total} results</span>
        <button onClick={handleRunSimilarity} disabled={!selectedHackathon}
          style={{ padding: '9px 18px', background: selectedHackathon ? WARNING : INPUT_BG, border: 'none', borderRadius: 8, color: selectedHackathon ? '#000' : TEXT_DIM, fontSize: 12, fontWeight: 600, cursor: selectedHackathon ? 'pointer' : 'not-allowed' }}>
          Run Similarity Check
        </button>
      </div>

      {/* Table */}
      {loading ? <div style={{ color: TEXT_MUTED, textAlign: 'center', padding: 60 }}>Loading...</div> : (
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                {['Project', 'Status', 'Risk Score', 'Verdict', 'Date'].map(h => (
                  <th key={h} style={{ padding: '12px 16px', color: TEXT_MUTED, fontWeight: 500, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.5, textAlign: 'left' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {submissions.map(sub => (
                <tr key={sub.id} onClick={() => navigate(`/report/${sub.id}`)}
                  style={{ borderBottom: '1px solid #111', cursor: 'pointer', transition: 'background 0.15s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#0d1433')}
                  onMouseLeave={e => (e.currentTarget.style.background = '')}>
                  <td style={{ padding: '12px 16px', fontWeight: 500 }}>{sub.project_title || new URL(sub.devpost_url).pathname.split('/').pop() || 'Untitled'}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{
                      padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 600,
                      background: sub.status === 'completed' ? SUCCESS_BG20 : sub.status === 'failed' ? ERROR_BG20 : sub.status === 'analyzing' ? WARNING_BG20 : '#333',
                      color: sub.status === 'completed' ? SUCCESS : sub.status === 'failed' ? ERROR : sub.status === 'analyzing' ? WARNING : '#888',
                    }}>{sub.status}</span>
                  </td>
                  <td style={{ padding: '12px 16px', fontWeight: 700, fontSize: 16, color: (sub.risk_score ?? 0) <= 30 ? SUCCESS : (sub.risk_score ?? 0) <= 60 ? WARNING : ERROR }}>
                    {sub.risk_score ?? '—'}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    {sub.verdict === 'clean' && <span style={{ color: SUCCESS, fontSize: 12, fontWeight: 600 }}>Clean</span>}
                    {sub.verdict === 'review' && <span style={{ color: WARNING, fontSize: 12, fontWeight: 600 }}>Review</span>}
                    {sub.verdict === 'flagged' && <span style={{ color: ERROR, fontSize: 12, fontWeight: 600 }}>Flagged</span>}
                  </td>
                  <td style={{ padding: '12px 16px', color: TEXT_MUTED, fontSize: 12 }}>
                    {sub.created_at ? new Date(sub.created_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {submissions.length === 0 && (
            <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
              <div style={{ fontSize: 16, marginBottom: 4 }}>No submissions yet</div>
              <div style={{ fontSize: 13 }}>Analyze a Devpost URL to get started</div>
            </div>
          )}
          {total > 20 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '16px 0', borderTop: `1px solid ${BORDER}` }}>
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                style={{ padding: '6px 16px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', cursor: page <= 1 ? 'not-allowed' : 'pointer', opacity: page <= 1 ? 0.4 : 1, fontSize: 13 }}>
                Prev
              </button>
              <span style={{ color: TEXT_MUTED, fontSize: 13 }}>Page {page} of {Math.ceil(total / 20)}</span>
              <button disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}
                style={{ padding: '6px 16px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', cursor: page * 20 >= total ? 'not-allowed' : 'pointer', opacity: page * 20 >= total ? 0.4 : 1, fontSize: 13 }}>
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
