import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import * as api from '../services/api';
import {
  SUCCESS, ERROR,
  TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY,
  INPUT_BG, BORDER,
  TYPO, SPACE,
} from '../theme';
import { Card } from '../components/Primitives';

interface Ranking {
  rank: number;
  submission_id: string;
  project_title: string;
  elo: number;
  raw_avg: number;
  judges: number;
}

const goldColor = '#FFC72C';
const silverColor = '#C0C0C0';
const bronzeColor = '#CD7F32';

const rankMedals: Record<number, { color: string; label: string }> = {
  1: { color: goldColor, label: '1st' },
  2: { color: silverColor, label: '2nd' },
  3: { color: bronzeColor, label: '3rd' },
};

export default function PublicLeaderboard() {
  const { id } = useParams<{ id: string }>();
  const [rankings, setRankings] = useState<Ranking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.getJudgingResults(id)
      .then(data => setRankings(data.rankings || []))
      .catch((e: any) => setError(e.message || 'Failed to load leaderboard'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Loading leaderboard...</p>;
  }

  return (
    <div>
      <div style={{ marginBottom: SPACE.lg }}>
        <Link to={`/hackathons/${id}`} style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none' }}>
          &larr; Back to Hackathon
        </Link>
        <h1 style={{ ...TYPO.h1, marginTop: SPACE.sm, marginBottom: 0 }}>Leaderboard</h1>
      </div>

      {error ? (
        <Card style={{ padding: SPACE.xl, textAlign: 'center' }}>
          <p style={{ color: TEXT_MUTED }}>{error}</p>
        </Card>
      ) : rankings.length === 0 ? (
        <Card style={{ padding: SPACE.xl, textAlign: 'center' }}>
          <p style={{ color: TEXT_MUTED }}>No rankings available yet.</p>
          <p style={{ color: TEXT_SECONDARY, fontSize: 13, marginTop: SPACE.sm }}>
            Rankings appear once judges have submitted their scores.
          </p>
        </Card>
      ) : (
        <Card style={{ overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${BORDER}`, textAlign: 'left' }}>
                <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500, width: 60 }}>Rank</th>
                <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Project</th>
                <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>ELO</th>
                <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>Raw Avg</th>
                <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500, textAlign: 'right' }}>Judges</th>
              </tr>
            </thead>
            <tbody>
              {rankings.map((r) => {
                const medal = rankMedals[r.rank];
                return (
                  <tr key={r.submission_id} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td style={{ padding: '10px 16px' }}>
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
                    <td style={{ padding: '10px 16px', fontWeight: r.rank <= 3 ? 600 : 400 }}>
                      {r.project_title || 'Untitled'}
                    </td>
                    <td style={{
                      padding: '10px 16px', textAlign: 'right',
                      fontFamily: TYPO['mono-data'].fontFamily, fontWeight: 600,
                      color: r.elo > 1550 ? SUCCESS : r.elo < 1450 ? ERROR : TEXT_PRIMARY,
                    }}>
                      {r.elo}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', color: TEXT_MUTED, fontFamily: TYPO['mono-data'].fontFamily }}>
                      {r.raw_avg}
                    </td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', color: TEXT_MUTED }}>
                      {r.judges}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
