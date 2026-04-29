import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReportCard from '../components/ReportCard';
import CheckResultRow from '../components/CheckResultRow';
import * as api from '../services/api';
import { PRIMARY, ERROR_TEXT, TEXT_MUTED, INPUT_BG, INPUT_BORDER } from '../theme';

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    const token = localStorage.getItem('anonymous_token') || undefined;
    api.getCheckReport(id, token)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div style={{ textAlign: 'center', padding: 40, color: TEXT_MUTED }}>Loading report...</div>;
  if (error) return <div style={{ textAlign: 'center', padding: 40, color: ERROR_TEXT }}>{error}</div>;
  if (!data) return null;

  const sub = data.submission;

  return (
    <div>
      <Link to="/" style={{ color: PRIMARY, textDecoration: 'none', fontSize: 14, marginBottom: 16, display: 'inline-block' }}>&larr; Back</Link>
      <ReportCard
        projectTitle={sub.project_title}
        riskScore={sub.risk_score ?? 0}
        verdict={sub.verdict ?? 'unknown'}
        categories={(data.check_results || []).map((cr: any) => ({
          category: cr.check_category,
          score: cr.score,
        }))}
      />
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h3 style={{ fontSize: 18 }}>Check Details</h3>
        <button onClick={() => {
          navigator.clipboard.writeText(JSON.stringify(data, null, 2));
        }} style={{ background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, padding: '6px 14px', color: TEXT_MUTED, cursor: 'pointer', fontSize: 13 }}>
          Copy JSON
        </button>
      </div>
      {(data.check_results || []).map((cr: any) => (
        <CheckResultRow key={cr.check_name} check={cr} />
      ))}
    </div>
  );
}
