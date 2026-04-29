import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import {
  PRIMARY, GOLD, SUCCESS, WARNING, ERROR,
  TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE, TEXT_SECONDARY,
  CARD_BG, INPUT_BG, INPUT_BORDER, BORDER,
} from '../theme';

interface Ranking {
  rank: number;
  submission_id: string;
  project_title: string;
  elo: number;
  raw_avg: number;
  judges: number;
}

interface JudgeStat {
  judge_id: string;
  name: string;
  mean: number;
  stddev: number;
  n_projects: number;
}

export default function JudgingResultsPage() {
  const { id: hackathonId } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [rankings, setRankings] = useState<Ranking[]>([]);
  const [judgeStats, setJudgeStats] = useState<JudgeStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    loadResults();
  }, [user, hackathonId]);

  const loadResults = async () => {
    setLoading(true);
    try {
      const data = await api.getJudgingResults(hackathonId!);
      setRankings(data.rankings || []);
      setJudgeStats(data.judge_stats || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load results');
    }
    setLoading(false);
  };

  if (!user) return null;

  const goldColor = '#FFC72C';
  const silverColor = '#C0C0C0';
  const bronzeColor = '#CD7F32';

  const rankMedals: Record<number, { color: string; label: string }> = {
    1: { color: goldColor, label: '1st' },
    2: { color: silverColor, label: '2nd' },
    3: { color: bronzeColor, label: '3rd' },
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 24 }}>Judging Results</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => navigate(`/hackathons/${hackathonId}/judging`)}
            style={{
              padding: '8px 16px', fontSize: 13,
              background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6, color: TEXT_SECONDARY,
              cursor: 'pointer',
            }}>
            Judge Portal
          </button>
          <button onClick={loadResults}
            style={{
              padding: '8px 16px', fontSize: 13,
              background: PRIMARY, border: 'none', borderRadius: 6, color: TEXT_WHITE,
              cursor: 'pointer',
            }}>
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <p style={{ color: TEXT_MUTED }}>Computing rankings...</p>
      ) : error ? (
        <div style={{
          padding: 24, background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12,
          textAlign: 'center', color: TEXT_MUTED,
        }}>
          <p>{error}</p>
          <button onClick={loadResults}
            style={{
              marginTop: 12, padding: '8px 20px', background: PRIMARY, border: 'none', borderRadius: 6,
              color: TEXT_WHITE, cursor: 'pointer', fontSize: 13,
            }}>
            Try Again
          </button>
        </div>
      ) : (
        <>
          {/* Rankings */}
          <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden', marginBottom: 24 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}`, textAlign: 'left' }}>
                  <th style={{ padding: '12px 16px', color: TEXT_MUTED, fontWeight: 500, width: 60 }}>Rank</th>
                  <th style={{ padding: '12px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Project</th>
                  <th style={{ padding: '12px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>ELO</th>
                  <th style={{ padding: '12px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>Raw Avg</th>
                  <th style={{ padding: '12px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>Judges</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((r) => {
                  const medal = rankMedals[r.rank];
                  return (
                    <tr key={r.submission_id} style={{ borderBottom: '1px solid #080c1a' }}>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                          width: 32, height: 32, borderRadius: '50%',
                          background: medal ? `${medal.color}20` : INPUT_BG,
                          color: medal ? medal.color : TEXT_MUTED,
                          fontWeight: 700, fontSize: 14,
                        }}>
                          {r.rank}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: r.rank <= 3 ? 600 : 400 }}>
                        {r.project_title || 'Untitled'}
                      </td>
                      <td style={{
                        padding: '12px 16px', textAlign: 'right', fontFamily: 'monospace', fontWeight: 600,
                        color: r.elo > 1550 ? SUCCESS : r.elo < 1450 ? ERROR : TEXT_PRIMARY,
                      }}>
                        {r.elo}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: TEXT_SECONDARY }}>
                        {r.raw_avg}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: TEXT_MUTED }}>
                        {r.judges}
                      </td>
                    </tr>
                  );
                })}
                {rankings.length === 0 && (
                  <tr><td colSpan={5} style={{ textAlign: 'center', padding: 32, color: TEXT_MUTED }}>
                    No completed scores yet. Rankings appear after judges submit scores.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Judge Stats */}
          {judgeStats.length > 0 && (
            <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
              <h3 style={{ fontSize: 14, padding: '12px 16px', color: TEXT_MUTED, margin: 0, borderBottom: `1px solid ${BORDER}` }}>
                Judge Severity
              </h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${BORDER}`, textAlign: 'left' }}>
                    <th style={{ padding: '8px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Judge</th>
                    <th style={{ padding: '8px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>Mean Raw</th>
                    <th style={{ padding: '8px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>Std Dev</th>
                    <th style={{ padding: '8px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>Projects</th>
                  </tr>
                </thead>
                <tbody>
                  {judgeStats.map(j => (
                    <tr key={j.judge_id} style={{ borderBottom: '1px solid #080c1a' }}>
                      <td style={{ padding: '8px 16px' }}>{j.name}</td>
                      <td style={{
                        padding: '8px 16px', textAlign: 'right', fontFamily: 'monospace',
                        color: j.mean > 70 ? ERROR : j.mean < 40 ? WARNING : TEXT_PRIMARY,
                      }}>
                        {j.mean}
                      </td>
                      <td style={{ padding: '8px 16px', textAlign: 'right', fontFamily: 'monospace', color: TEXT_MUTED }}>
                        {j.stddev}
                      </td>
                      <td style={{ padding: '8px 16px', textAlign: 'right', color: TEXT_MUTED }}>
                        {j.n_projects}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
