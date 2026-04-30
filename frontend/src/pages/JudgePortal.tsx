import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import {
  PRIMARY, GOLD, SUCCESS,
  TEXT_MUTED, TEXT_WHITE, TEXT_SECONDARY,
  CARD_BG, INPUT_BG, BORDER,
} from '../theme';

interface Criterion {
  id: string;
  name: string;
  description: string;
  max_score: number;
  weight: number;
  score: number | null;
}

interface QueueItem {
  assignment_id: string | null;
  submission_id: string;
  project_title: string;
  devpost_url: string;
  github_url: string | null;
  reasons: string[];
}

export default function JudgePortal() {
  const { id: hackathonId } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [scoredCount, setScoredCount] = useState(0);

  // Current project being scored
  const [current, setCurrent] = useState<QueueItem | null>(null);
  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [submission, setSubmission] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const loadQueue = useCallback(async () => {
    if (!user || !hackathonId) return;
    setLoading(true);
    try {
      const data = await api.getJudgingQueue(hackathonId, user.id);
      const q = data.queue || [];
      setQueue(q);
      if (q.length > 0 && !current) {
        startNextProject(q[0]);
      }
    } catch { setQueue([]); }
    setLoading(false);
  }, [user, hackathonId]);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    loadQueue();
  }, [user, hackathonId]);

  const startNextProject = async (item: QueueItem) => {
    setError('');
    if (!item.assignment_id) {
      setError('No assignment for this project.');
      return;
    }
    try {
      await api.openAssignment(item.assignment_id);
      const detail = await api.getAssignmentDetail(item.assignment_id);
      setCurrent(item);
      setCriteria((detail.criteria || []).map((c: any) => ({ ...c, score: c.score ?? null })));
      setSubmission(detail.submission);
      setSubmitted(false);
    } catch (e) {
      setError('Failed to open assignment. Please refresh.');
    }
  };

  const updateScore = (criterionId: string, score: number) => {
    setCriteria(prev => prev.map(c => c.id === criterionId ? { ...c, score } : c));
  };

  const handleSubmit = async () => {
    if (!current?.assignment_id || saving) return;
    setSaving(true);
    try {
      await api.submitScores(current.assignment_id, criteria.map(c => ({
        criterion_id: c.id,
        score: c.score,
      })));
      setSubmitted(true);
      setScoredCount(prev => prev + 1);

      // Auto-advance after brief pause
      setTimeout(() => {
        const remaining = queue.filter(q =>
          q.submission_id !== current.submission_id && q.assignment_id
        );
        setQueue(remaining);
        setCurrent(null);
        setCriteria([]);
        setSubmission(null);
        setSubmitted(false);
        if (remaining.length > 0) {
          startNextProject(remaining[0]);
        }
      }, 1200);
    } catch {
      setError('Failed to submit. Try again.');
    }
    setSaving(false);
  };

  if (!user) return null;

  // ── Empty / all done state ──
  if (!loading && queue.length === 0 && !current) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>&#10003;</div>
        <h2 style={{ fontSize: 22, marginBottom: 8 }}>All Caught Up!</h2>
        <p style={{ color: TEXT_MUTED, marginBottom: 24, maxWidth: 400, margin: '0 auto 24px' }}>
          {scoredCount > 0
            ? `You've scored ${scoredCount} project${scoredCount > 1 ? 's' : ''}. Check back later — more projects may be assigned as the judging rounds progress.`
            : 'No projects need your judging right now. Check back as more submissions come in or rounds advance.'}
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
          <button onClick={loadQueue} style={{
            padding: '8px 16px', background: 'none', border: `1px solid ${BORDER}`,
            borderRadius: 6, color: TEXT_SECONDARY, cursor: 'pointer',
          }}>Refresh</button>
          <button onClick={() => navigate(`/hackathons/${hackathonId}/judging/results`)} style={{
            padding: '8px 16px', background: 'none', border: `1px solid ${BORDER}`,
            borderRadius: 6, color: TEXT_SECONDARY, cursor: 'pointer',
          }}>View Results</button>
        </div>
      </div>
    );
  }

  // ── Loading ──
  if (loading && !current) {
    return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: 40 }}>Loading next project...</p>;
  }

  // ── Scoring view ──
  const scoredCriteria = criteria.filter(c => c.score !== null).length;

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 data-mobile-h1 style={{ fontSize: 22, marginBottom: 0 }}>Judging</h2>
        <button onClick={() => navigate(`/hackathons/${hackathonId}/judging/results`)} style={{
          padding: '6px 12px', background: 'none', border: `1px solid ${BORDER}`,
          borderRadius: 6, color: TEXT_SECONDARY, cursor: 'pointer', fontSize: 12,
        }}>View Results</button>
      </div>

      {/* Project card */}
      <div style={{
        background: CARD_BG,
        border: `1px solid ${submitted ? `${SUCCESS}40` : BORDER}`,
        borderRadius: 12,
        padding: 24,
        marginBottom: 16,
      }}>
        {/* Header */}
        <div style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 20, marginBottom: 4 }}>{submission?.project_title || current?.project_title || 'Untitled'}</h2>
          <div style={{ display: 'flex', gap: 12, fontSize: 13 }}>
            {submission?.devpost_url && (
              <a href={submission.devpost_url} target="_blank" style={{ color: PRIMARY }}>Devpost &rarr;</a>
            )}
            {submission?.github_url && (
              <a href={submission.github_url} target="_blank" style={{ color: PRIMARY }}>GitHub &rarr;</a>
            )}
          </div>
        </div>

        {/* Tech stack */}
        {submission?.claimed_tech?.length > 0 && (
          <div style={{ marginBottom: 16, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {submission.claimed_tech.map((t: string) => (
              <span key={t} style={{
                padding: '2px 8px', background: INPUT_BG, borderRadius: 10, fontSize: 11,
                color: TEXT_SECONDARY, border: `1px solid ${BORDER}`,
              }}>{t}</span>
            ))}
          </div>
        )}

        {/* Scoring */}
        <div>
          <div style={{ fontSize: 13, color: TEXT_MUTED, marginBottom: 12 }}>
            {scoredCriteria}/{criteria.length} criteria scored
          </div>

          {criteria.map((c) => (
            <div key={c.id} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <div>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{c.name}</span>
                  <span style={{ fontSize: 11, color: TEXT_MUTED, marginLeft: 6 }}>({c.weight}%)</span>
                </div>
                <span style={{
                  fontSize: 16, fontWeight: 700,
                  color: c.score !== null ? GOLD : TEXT_MUTED,
                }}>
                  {c.score !== null ? c.score : '-'}
                  <span style={{ fontSize: 11, fontWeight: 400 }}> / {c.max_score}</span>
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={c.max_score}
                value={c.score ?? 0}
                onChange={e => updateScore(c.id, Number(e.target.value))}
                disabled={submitted}
                style={{ width: '100%', accentColor: PRIMARY }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: TEXT_MUTED }}>
                <span>0</span><span>{c.max_score}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: '8px 12px', background: '#ff444418', borderRadius: 6,
            color: '#ff6666', fontSize: 13, marginBottom: 12,
          }}>
            {error}
          </div>
        )}

        {/* Submit */}
        {submitted ? (
          <div style={{
            padding: '12px 16px', background: `${SUCCESS}18`, borderRadius: 8,
            color: SUCCESS, fontSize: 14, fontWeight: 600, textAlign: 'center',
          }}>
            Submitted! Loading next project...
          </div>
        ) : (
          <button onClick={handleSubmit} disabled={saving}
            style={{
              width: '100%', padding: '12px', fontSize: 15, fontWeight: 600,
              background: PRIMARY, border: 'none', borderRadius: 8, color: TEXT_WHITE,
              cursor: 'pointer',
            }}>
            {saving ? 'Submitting...' : 'Submit Scores'}
          </button>
        )}
      </div>
    </div>
  );
}
