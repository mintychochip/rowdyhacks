import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { Card } from '../components/Primitives';
import {
  PRIMARY, SUCCESS, ERROR, WARNING,
  TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY,
  INPUT_BG, BORDER, CARD_BG,
  TYPO, SPACE, RADIUS, SHADOW,
} from '../theme';

interface Ranking {
  rank: number;
  submission_id: string;
  project_title: string;
  score: number;
  score_se: number;
  raw_avg: number;
  judges: number;
}

interface JudgeStat {
  judge_id: string;
  name: string;
  severity: number;
  precision: number;
  sigma: number;
  mean_raw: number;
  n_projects: number;
}

const GOLD_C = '#FFC72C';
const SILVER_C = '#C0C0C0';
const BRONZE_C = '#CD7F32';

const medalDef: Record<number, { color: string; bg: string; border: string }> = {
  1: { color: GOLD_C, bg: '#FFC72C18', border: '#FFC72C40' },
  2: { color: SILVER_C, bg: '#C0C0C018', border: '#C0C0C040' },
  3: { color: BRONZE_C, bg: '#CD7F3218', border: '#CD7F3240' },
};

export default function JudgingResultsPage() {
  const { id: hackathonId } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [rankings, setRankings] = useState<Ranking[]>([]);
  const [judgeStats, setJudgeStats] = useState<JudgeStat[]>([]);
  const [leaderboardPublic, setLeaderboardPublic] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    loadResults();
  }, [user, hackathonId]);

  const loadResults = async () => {
    setLoading(true);
    try {
      const [data, session] = await Promise.all([
        api.getJudgingResults(hackathonId!),
        api.getJudgingSession(hackathonId!),
      ]);
      setRankings(data.rankings || []);
      setJudgeStats(data.judge_stats || []);
      setLeaderboardPublic(session.leaderboard_public ?? false);
    } catch (e: any) { setError(e.message || 'Failed to load results'); }
    setLoading(false);
  };

  const handleToggleLeaderboard = async () => {
    try {
      const res = await api.toggleLeaderboard(hackathonId!);
      setLeaderboardPublic(res.leaderboard_public);
    } catch {}
  };

  if (!user) return null;

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: SPACE.lg }}>
        <div>
          <h1 data-mobile-h1 style={{ ...TYPO.h1, color: TEXT_PRIMARY, marginBottom: SPACE.xs }}>Judging Results</h1>
          <p style={{ ...TYPO['body-sm'], color: TEXT_MUTED }}>
            {rankings.length} projects ranked
          </p>
        </div>
        <div style={{ display: 'flex', gap: SPACE.sm }}>
          {user?.role === 'organizer' && (
            <button onClick={handleToggleLeaderboard} style={{
              padding: '8px 16px', background: INPUT_BG, border: `1px solid ${BORDER}`,
              borderRadius: RADIUS.sm, color: TEXT_MUTED, fontFamily: 'inherit', fontSize: 13, cursor: 'pointer',
            }}>
              {leaderboardPublic ? 'Public' : 'Private'}
            </button>
          )}
          <button onClick={() => navigate(`/hackathons/${hackathonId}/judging`)} style={{
            padding: '8px 16px', background: INPUT_BG, border: `1px solid ${BORDER}`,
            borderRadius: RADIUS.sm, color: TEXT_MUTED, fontFamily: 'inherit', fontSize: 13, cursor: 'pointer',
          }}>
            Judge Portal
          </button>
          <button onClick={loadResults} style={{
            padding: '8px 16px', background: PRIMARY, border: 'none',
            borderRadius: RADIUS.sm, color: '#fff', fontFamily: 'inherit', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}>
            Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
          Computing rankings...
        </div>
      ) : error ? (
        <div style={{
          background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
          padding: SPACE.xl, textAlign: 'center', boxShadow: SHADOW.card,
        }}>
          <p style={{ color: TEXT_MUTED, marginBottom: SPACE.md }}>{error}</p>
          <button onClick={loadResults} style={{
            padding: '8px 20px', background: PRIMARY, border: 'none', borderRadius: RADIUS.sm,
            color: '#fff', fontFamily: 'inherit', fontSize: 14, fontWeight: 600, cursor: 'pointer',
          }}>
            Try Again
          </button>
        </div>
      ) : (
        <>
          {/* Rankings Table */}
          <Card scrollable style={{ marginBottom: SPACE.lg }}>
            <div style={{
              padding: '14px 20px', borderBottom: `1px solid ${BORDER}`,
            }}>
              <span style={{ ...TYPO['body-lg'], fontWeight: 600, color: TEXT_PRIMARY }}>
                Rankings
              </span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}`, background: 'rgba(255,255,255,0.02)' }}>
                  {['Rank', 'Project', 'Score', '±SE', 'Raw Avg', 'Judges'].map(h => (
                    <th key={h} style={{
                      padding: '10px 20px', ...TYPO['label-caps'], color: TEXT_MUTED,
                      textAlign: h === 'Project' ? 'left' : h === 'Rank' ? 'left' : 'right',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rankings.map((r) => {
                  const medal = medalDef[r.rank];
                  return (
                    <tr key={r.submission_id}
                      style={{
                        borderBottom: `1px solid ${BORDER}`,
                        transition: 'background 0.12s',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(26,92,231,0.06)')}
                      onMouseLeave={e => (e.currentTarget.style.background = '')}>
                      <td style={{ padding: '12px 20px' }}>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                          width: 36, height: 36, borderRadius: '50%',
                          background: medal ? medal.bg : INPUT_BG,
                          border: medal ? `1.5px solid ${medal.border}` : 'none',
                          color: medal ? medal.color : TEXT_MUTED,
                          fontWeight: 700, fontSize: 14,
                        }}>
                          {r.rank}
                        </span>
                      </td>
                      <td style={{
                        padding: '12px 20px', ...TYPO['body-sm'],
                        fontWeight: r.rank <= 3 ? 600 : 400,
                        color: TEXT_PRIMARY,
                      }}>
                        {r.project_title || 'Untitled'}
                      </td>
                      <td style={{
                        padding: '12px 20px', textAlign: 'right',
                        fontFamily: "'Space Mono', monospace", fontSize: 14, fontWeight: 600,
                        color: r.score > 5 ? SUCCESS : r.score < -5 ? ERROR : TEXT_PRIMARY,
                      }}>
                        {r.score}
                      </td>
                      <td style={{
                        padding: '12px 20px', textAlign: 'right',
                        fontFamily: "'Space Mono', monospace", fontSize: 13,
                        color: TEXT_MUTED,
                      }}>
                        {r.score_se != null ? `\u00b1${r.score_se}` : '-'}
                      </td>
                      <td style={{
                        padding: '12px 20px', textAlign: 'right',
                        ...TYPO['body-sm'], color: TEXT_SECONDARY,
                      }}>
                        {r.raw_avg}
                      </td>
                      <td style={{
                        padding: '12px 20px', textAlign: 'right',
                        ...TYPO['body-sm'], color: TEXT_MUTED,
                      }}>
                        {r.judges}
                      </td>
                    </tr>
                  );
                })}
                {rankings.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
                      No completed scores yet. Rankings appear after judges submit scores.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>

          {/* Judge Analysis */}
          {judgeStats.length > 0 && (
            <Card scrollable>
              <div style={{
                padding: '14px 20px', borderBottom: `1px solid ${BORDER}`,
              }}>
                <span style={{ ...TYPO['body-lg'], fontWeight: 600, color: TEXT_PRIMARY }}>
                  Judge Analysis
                </span>
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${BORDER}`, background: 'rgba(255,255,255,0.02)' }}>
                    {['Judge', 'Severity', 'Precision', 'Noise (σ)', 'Projects'].map(h => (
                      <th key={h} style={{
                        padding: '10px 20px', ...TYPO['label-caps'], color: TEXT_MUTED,
                        textAlign: h === 'Judge' ? 'left' : 'right',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {judgeStats.map(j => (
                    <tr key={j.judge_id} style={{ borderBottom: `1px solid ${BORDER}` }}>
                      <td style={{ padding: '12px 20px', ...TYPO['body-sm'], color: TEXT_PRIMARY }}>
                        {j.name}
                      </td>
                      <td style={{
                        padding: '12px 20px', textAlign: 'right',
                        fontFamily: "'Space Mono', monospace", fontSize: 13, fontWeight: 600,
                        color: j.severity > 0 ? SUCCESS : ERROR,
                      }}>
                        {j.severity > 0 ? '+' : ''}{j.severity}
                      </td>
                      <td style={{
                        padding: '12px 20px', textAlign: 'right',
                        fontFamily: "'Space Mono', monospace", fontSize: 13,
                        color: TEXT_PRIMARY,
                      }}>
                        {j.precision}
                      </td>
                      <td style={{
                        padding: '12px 20px', textAlign: 'right',
                        fontFamily: "'Space Mono', monospace", fontSize: 13,
                        color: TEXT_MUTED,
                      }}>
                        {j.sigma}
                      </td>
                      <td style={{
                        padding: '12px 20px', textAlign: 'right',
                        ...TYPO['body-sm'], color: TEXT_MUTED,
                      }}>
                        {j.n_projects}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
