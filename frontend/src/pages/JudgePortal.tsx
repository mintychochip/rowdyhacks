import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { Card } from '../components/Primitives';
import { useMediaQuery } from '../hooks/useMediaQuery';
import {
  PRIMARY, GOLD, SUCCESS, SUCCESS_BG10, ERROR, ERROR_BG10, ERROR_BG20, WARNING,
  TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY, TEXT_DIM,
  INPUT_BG, BORDER, CARD_BG,
  TYPO, SPACE, RADIUS, SHADOW,
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
  score: number | null;
  score_se: number | null;
  uncertainty: { total: number; variance: number; proximity: number; coverage: number; };
  judge_count: number;
  reasons: string[];
}

interface CompletedItem {
  id: string;
  submission_id: string;
  project_title: string;
}

const REASON_LABELS: Record<string, string> = {
  high_variance: 'High variance',
  close_race: 'Close race',
  needs_coverage: 'Needs coverage',
  low_priority: 'Low priority',
};

const REASON_COLORS: Record<string, string> = {
  high_variance: ERROR,
  close_race: WARNING,
  needs_coverage: PRIMARY,
  low_priority: TEXT_MUTED,
};

export default function JudgePortal() {
  const { id: hackathonId } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [completed, setCompleted] = useState<CompletedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeAssignmentId, setActiveAssignmentId] = useState<string | null>(null);

  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [submission, setSubmission] = useState<any>(null);
  const [, setOpenedAt] = useState<string | null>(null);
  const [, setPerProjectSeconds] = useState(300);
  const [timeRemaining, setTimeRemaining] = useState(300);
  const [saving, setSaving] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { isMobile } = useMediaQuery();

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    loadData();
  }, [user, hackathonId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const queueData = await api.getJudgingQueue(hackathonId!, user!.id);
      setQueue(queueData.queue || []);
      const assignments = await api.getJudgeAssignments(hackathonId!, user!.id);
      if (Array.isArray(assignments)) {
        setCompleted(
          assignments.filter((a: any) => a.is_completed).map((a: any) => ({
            id: a.id, submission_id: a.submission_id,
            project_title: a.submission?.project_title || a.submission_id,
          }))
        );
      }
    } catch { setQueue([]); setCompleted([]); }
    setLoading(false);
  };

  const openScoring = async (assignmentId: string) => {
    try {
      await api.openAssignment(assignmentId);
      const detail = await api.getAssignmentDetail(assignmentId);
      setActiveAssignmentId(assignmentId);
      setCriteria(detail.criteria || []);
      setSubmission(detail.submission);
      setOpenedAt(detail.opened_at);
      setPerProjectSeconds(detail.per_project_seconds || 300);
      if (detail.opened_at) {
        const elapsed = Math.floor((Date.now() - new Date(detail.opened_at).getTime()) / 1000);
        setTimeRemaining(Math.max(0, (detail.per_project_seconds || 300) - elapsed));
      } else {
        setTimeRemaining(detail.per_project_seconds || 300);
      }
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    if (!activeAssignmentId) return;
    intervalRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) { clearInterval(intervalRef.current!); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [activeAssignmentId]);

  useEffect(() => {
    if (timeRemaining <= 0 && activeAssignmentId) handleSubmit();
  }, [timeRemaining]);

  const updateScore = (criterionId: string, score: number) => {
    setCriteria(prev => prev.map(c => c.id === criterionId ? { ...c, score } : c));
  };

  const handleSubmit = async () => {
    if (!activeAssignmentId || saving) return;
    setSaving(true);
    try {
      await api.submitScores(activeAssignmentId, criteria.map(c => ({
        criterion_id: c.id, score: c.score,
      })));
    } catch {}
    setSaving(false);
    setActiveAssignmentId(null);
    setSubmission(null);
    setCriteria([]);
    if (intervalRef.current) clearInterval(intervalRef.current);
    loadData();
  };

  const closeScoring = () => {
    setActiveAssignmentId(null);
    setSubmission(null);
    setCriteria([]);
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  if (!user) return null;

  // ── Scoring View ──
  if (activeAssignmentId) {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    const isLow = timeRemaining <= 60;
    const scoredCount = criteria.filter(c => c.score !== null).length;

    return (
      <div>
        {/* Hero card */}
        <div style={{
          background: CARD_BG, border: `1px solid ${BORDER}`,
          borderRadius: RADIUS.lg, padding: SPACE.lg, marginBottom: SPACE.lg,
          boxShadow: SHADOW.card,
        }}>
          <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: isMobile ? SPACE.md : 0 }}>
            <div>
              <h2 data-mobile-h1 style={{ ...TYPO.h2, color: TEXT_PRIMARY, marginBottom: SPACE.xs }}>
                {submission?.project_title || 'Untitled'}
              </h2>
              <div style={{ display: 'flex', gap: SPACE.md, flexWrap: 'wrap' }}>
                <a href={submission?.devpost_url} target="_blank" style={{ ...TYPO['body-sm'], color: PRIMARY, textDecoration: 'none' }}>
                  View on Devpost &rarr;
                </a>
                {submission?.github_url && (
                  <a href={submission.github_url} target="_blank" style={{ ...TYPO['body-sm'], color: PRIMARY, textDecoration: 'none' }}>
                    View on GitHub &rarr;
                  </a>
                )}
              </div>
            </div>
            <div style={{
              background: isLow ? ERROR_BG20 : 'rgba(255,199,44,0.08)',
              border: `2px solid ${isLow ? ERROR : GOLD}`,
              borderRadius: RADIUS.lg, padding: '12px 24px', textAlign: 'center', minWidth: 100,
            }}>
              <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 28, fontWeight: 700, color: isLow ? ERROR : GOLD }}>
                {minutes}:{String(seconds).padStart(2, '0')}
              </div>
              <div style={{ ...TYPO['label-caps'], color: TEXT_MUTED, fontSize: 10 }}>remaining</div>
            </div>
          </div>

          {submission?.claimed_tech?.length > 0 && (
            <div style={{ marginTop: SPACE.md, display: 'flex', gap: SPACE.xs, flexWrap: 'wrap' }}>
              {submission.claimed_tech.map((t: string) => (
                <span key={t} style={{
                  padding: '2px 10px', background: INPUT_BG, borderRadius: RADIUS.full,
                  fontSize: 12, color: TEXT_SECONDARY, border: `1px solid ${BORDER}`,
                }}>{t}</span>
              ))}
            </div>
          )}
        </div>

        {/* Criteria card */}
        <div style={{
          background: CARD_BG, border: `1px solid ${BORDER}`,
          borderRadius: RADIUS.lg, padding: SPACE.lg, marginBottom: SPACE.lg,
          boxShadow: SHADOW.card,
        }}>
          <h3 style={{ ...TYPO.h3, color: TEXT_PRIMARY, marginBottom: SPACE.lg }}>
            Scoring ({scoredCount}/{criteria.length})
          </h3>
          {criteria.map(c => (
            <div key={c.id} style={{ marginBottom: SPACE.lg }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: SPACE.xs }}>
                <div>
                  <span style={{ ...TYPO['body-lg'], fontWeight: 600, color: TEXT_PRIMARY }}>{c.name}</span>
                  <span style={{ ...TYPO['body-sm'], color: TEXT_MUTED, marginLeft: SPACE.sm }}>
                    ({c.weight}%)
                  </span>
                </div>
                <span style={{ ...TYPO.h3, color: c.score !== null ? GOLD : TEXT_MUTED }}>
                  {c.score !== null ? c.score : '-'}<span style={{ fontSize: 12, fontWeight: 400 }}>/{c.max_score}</span>
                </span>
              </div>
              {c.description && (
                <div style={{ ...TYPO['body-sm'], color: TEXT_MUTED, marginBottom: SPACE.xs + 2 }}>
                  {c.description}
                </div>
              )}
              <input type="range" min={0} max={c.max_score}
                value={c.score ?? 0} onChange={e => updateScore(c.id, Number(e.target.value))}
                style={{ width: '100%', accentColor: PRIMARY }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: TEXT_MUTED, marginTop: 2 }}>
                <span>0</span><span>{c.max_score}</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: SPACE.sm }}>
          <button onClick={handleSubmit} disabled={saving} style={{
            padding: '10px 28px', background: PRIMARY, border: 'none', borderRadius: RADIUS.sm,
            color: '#fff', fontFamily: "'Space Grotesk', sans-serif", fontSize: 14, fontWeight: 600,
            cursor: saving ? 'not-allowed' : 'pointer',
          }}>
            {saving ? 'Submitting...' : 'Submit Scores'}
          </button>
          <button onClick={closeScoring} style={{
            padding: '10px 20px', background: INPUT_BG, border: `1px solid ${BORDER}`,
            borderRadius: RADIUS.sm, color: TEXT_MUTED, fontFamily: "'Space Grotesk', sans-serif",
            fontSize: 14, cursor: 'pointer',
          }}>
            Back to List
          </button>
        </div>

        {timeRemaining <= 60 && timeRemaining > 0 && (
          <div style={{
            marginTop: SPACE.md, padding: '10px 16px',
            background: ERROR_BG20, border: `1px solid ${ERROR}`,
            borderRadius: RADIUS.sm, color: ERROR,
            ...TYPO['body-sm'], fontWeight: 600,
          }}>
            Less than 1 minute remaining — scores auto-submit when time runs out.
          </div>
        )}
      </div>
    );
  }

  // ── Queue List View ──
  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: SPACE.lg }}>
        <div>
          <h1 data-mobile-h1 style={{ ...TYPO.h1, color: TEXT_PRIMARY, marginBottom: SPACE.xs }}>Judge Portal</h1>
          <p style={{ ...TYPO['body-sm'], color: TEXT_MUTED }}>
            {queue.length} projects awaiting review
          </p>
        </div>
        <div style={{ display: 'flex', gap: SPACE.sm }}>
          <button onClick={loadData} style={{
            padding: '8px 16px', background: INPUT_BG, border: `1px solid ${BORDER}`,
            borderRadius: RADIUS.sm, color: TEXT_MUTED, fontFamily: 'inherit', fontSize: 13, cursor: 'pointer',
          }}>
            Refresh
          </button>
          <button onClick={() => navigate(`/hackathons/${hackathonId}/judging/results`)} style={{
            padding: '8px 16px', background: PRIMARY, border: 'none',
            borderRadius: RADIUS.sm, color: '#fff', fontFamily: 'inherit', fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}>
            View Results
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>Loading priority queue...</div>
      ) : (
        <>
          {/* Priority Queue */}
          <Card scrollable style={{ marginBottom: SPACE.lg }}>
            <div style={{
              padding: '14px 20px', borderBottom: `1px solid ${BORDER}`,
              display: 'flex', alignItems: 'center', gap: SPACE.sm,
            }}>
              <span style={{ ...TYPO['body-lg'], fontWeight: 600, color: TEXT_PRIMARY }}>Priority Queue</span>
              <span style={{ ...TYPO['body-sm'], color: TEXT_MUTED }}>
                Ranked by judging need
              </span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}`, background: 'rgba(255,255,255,0.02)' }}>
                  {['#', 'Project', 'Score', 'Judges', 'Why', 'Action'].map(h => (
                    <th key={h} style={{
                      padding: '10px 20px', ...TYPO['label-caps'], color: TEXT_MUTED, textAlign: 'left',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {queue.map((item, idx) => {
                  const rowBg = idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)';
                  return (
                    <tr key={item.submission_id}
                      style={{
                        borderBottom: `1px solid ${BORDER}`, background: rowBg,
                        transition: 'background 0.12s',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(26,92,231,0.06)')}
                      onMouseLeave={e => (e.currentTarget.style.background = rowBg)}>
                      <td style={{ padding: '12px 20px', ...TYPO['body-sm'], color: TEXT_DIM }}>{idx + 1}</td>
                      <td style={{ padding: '12px 20px' }}>
                        <div style={{ ...TYPO['body-sm'], fontWeight: 600, color: TEXT_PRIMARY }}>
                          {item.project_title || 'Untitled'}
                        </div>
                        <a href={item.devpost_url} target="_blank" style={{ ...TYPO['body-sm'], color: PRIMARY, fontSize: 12, textDecoration: 'none' }}>
                          Devpost &rarr;
                        </a>
                      </td>
                      <td style={{
                        padding: '12px 20px', fontFamily: "'Space Mono', monospace",
                        fontSize: 14, fontWeight: 600, color: TEXT_PRIMARY,
                      }}>
                        {item.score != null ? item.score : '\u2014'}
                      </td>
                      <td style={{ padding: '12px 20px' }}>
                        <span style={{
                          ...TYPO['body-sm'], fontWeight: 600,
                          color: item.judge_count === 0 ? ERROR_TEXT : TEXT_SECONDARY,
                        }}>
                          {item.judge_count}
                        </span>
                      </td>
                      <td style={{ padding: '12px 20px' }}>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {item.reasons.map(reason => (
                            <span key={reason} style={{
                              display: 'inline-block', padding: '1px 8px', borderRadius: RADIUS.full,
                              fontSize: 10, fontWeight: 600,
                              background: `${REASON_COLORS[reason] || TEXT_MUTED}18`,
                              color: REASON_COLORS[reason] || TEXT_MUTED,
                              border: `1px solid ${REASON_COLORS[reason] || TEXT_MUTED}30`,
                            }}>
                              {REASON_LABELS[reason] || reason}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: '12px 20px' }}>
                        {item.assignment_id ? (
                          <button onClick={() => openScoring(item.assignment_id!)} style={{
                            padding: '6px 16px', background: PRIMARY, border: 'none',
                            borderRadius: RADIUS.sm, color: '#fff', fontFamily: 'inherit',
                            fontSize: 12, fontWeight: 600, cursor: 'pointer',
                          }}>
                            Score
                          </button>
                        ) : (
                          <span style={{ ...TYPO['body-sm'], color: TEXT_MUTED }}>—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {queue.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
                      All projects scored — check back after more judges submit.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Card>

          {/* Completed */}
          {completed.length > 0 && (
            <Card scrollable>
              <div style={{
                padding: '14px 20px', borderBottom: `1px solid ${BORDER}`,
              }}>
                <span style={{ ...TYPO['body-lg'], fontWeight: 600, color: TEXT_PRIMARY }}>
                  Completed by You
                </span>
                <span style={{ ...TYPO['body-sm'], color: TEXT_MUTED, marginLeft: SPACE.sm }}>
                  ({completed.length})
                </span>
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <tbody>
                  {completed.map((a, i) => (
                    <tr key={a.id} style={{
                      borderBottom: i < completed.length - 1 ? `1px solid ${BORDER}` : 'none',
                    }}>
                      <td style={{ padding: '12px 20px', ...TYPO['body-sm'], color: TEXT_PRIMARY }}>
                        {a.project_title}
                      </td>
                      <td style={{ padding: '12px 20px' }}>
                        <span style={{
                          display: 'inline-block', padding: '2px 10px', borderRadius: RADIUS.full,
                          fontSize: 11, fontWeight: 600, background: SUCCESS_BG10, color: SUCCESS,
                        }}>
                          Completed
                        </span>
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
