import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import {
  PRIMARY, PRIMARY_HOVER, GOLD, SUCCESS, ERROR, WARNING,
  TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE, TEXT_SECONDARY,
  CARD_BG, INPUT_BG, INPUT_BORDER, BORDER, TABLE_HOVER,
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
  elo: number;
  uncertainty: {
    total: number;
    variance: number;
    proximity: number;
    coverage: number;
  };
  judge_count: number;
  reasons: string[];
}

interface CompletedItem {
  id: string;
  submission_id: string;
  project_title: string;
}

const REASON_LABELS: Record<string, string> = {
  high_variance: 'High disagreement among judges',
  close_race: 'Close race with neighbor',
  needs_coverage: 'Needs more judge coverage',
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

  // Scoring state
  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [submission, setSubmission] = useState<any>(null);
  const [openedAt, setOpenedAt] = useState<string | null>(null);
  const [perProjectSeconds, setPerProjectSeconds] = useState(300);
  const [timeRemaining, setTimeRemaining] = useState(300);
  const [saving, setSaving] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    loadData();
  }, [user, hackathonId]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load priority queue
      const queueData = await api.getJudgingQueue(hackathonId!, user!.id);
      setQueue(queueData.queue || []);

      // Load completed assignments for reference
      const assignments = await api.getJudgeAssignments(hackathonId!, user!.id);
      if (Array.isArray(assignments)) {
        setCompleted(
          assignments
            .filter((a: any) => a.is_completed)
            .map((a: any) => ({
              id: a.id,
              submission_id: a.submission_id,
              project_title: a.submission?.project_title || a.submission_id,
            }))
        );
      }
    } catch { setQueue([]); setCompleted([]); }
    setLoading(false);
  };

  // ── scoring flow ──

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
    } catch (e) {
      console.error('Failed to open assignment', e);
    }
  };

  // Timer
  useEffect(() => {
    if (!activeAssignmentId) return;
    intervalRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        const next = prev - 1;
        if (next <= 0) {
          clearInterval(intervalRef.current!);
          return 0;
        }
        return next;
      });
    }, 1000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [activeAssignmentId]);

  // Auto-submit when time runs out
  useEffect(() => {
    if (timeRemaining <= 0 && activeAssignmentId) {
      handleSubmit();
    }
  }, [timeRemaining]);

  const updateScore = (criterionId: string, score: number) => {
    setCriteria(prev => prev.map(c => c.id === criterionId ? { ...c, score } : c));
  };

  const handleSubmit = async () => {
    if (!activeAssignmentId || saving) return;
    setSaving(true);
    try {
      await api.submitScores(activeAssignmentId, criteria.map(c => ({
        criterion_id: c.id,
        score: c.score,
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

  // ── render ──

  if (!user) return null;

  // Scoring view (same as before)
  if (activeAssignmentId) {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    const isLow = timeRemaining <= 60;
    const scoredCount = criteria.filter(c => c.score !== null).length;

    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
          <div>
            <h2 style={{ fontSize: 24, marginBottom: 4 }}>{submission?.project_title || 'Untitled'}</h2>
            <a href={submission?.devpost_url} target="_blank" style={{ color: PRIMARY, fontSize: 13 }}>View on Devpost</a>
            {submission?.github_url && (
              <> &middot; <a href={submission.github_url} target="_blank" style={{ color: PRIMARY, fontSize: 13 }}>View on GitHub</a></>
            )}
          </div>

          <div style={{
            background: isLow ? '#ff444420' : INPUT_BG,
            border: `2px solid ${isLow ? ERROR : GOLD}`,
            borderRadius: 12,
            padding: '12px 20px',
            textAlign: 'center',
            minWidth: 100,
          }}>
            <div style={{
              fontSize: 32, fontWeight: 700,
              color: isLow ? ERROR : GOLD,
              fontVariantNumeric: 'tabular-nums',
              fontFamily: 'monospace',
            }}>
              {minutes}:{String(seconds).padStart(2, '0')}
            </div>
            <div style={{ fontSize: 11, color: TEXT_MUTED }}>remaining</div>
          </div>
        </div>

        {submission?.claimed_tech?.length > 0 && (
          <div style={{ marginBottom: 20, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {submission.claimed_tech.map((t: string) => (
              <span key={t} style={{
                padding: '3px 10px', background: INPUT_BG, borderRadius: 12, fontSize: 12, color: TEXT_SECONDARY,
                border: `1px solid ${BORDER}`,
              }}>{t}</span>
            ))}
          </div>
        )}

        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, marginBottom: 20 }}>Scoring ({scoredCount}/{criteria.length})</h3>

          {criteria.map((c) => (
            <div key={c.id} style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <div>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{c.name}</span>
                  <span style={{ fontSize: 12, color: TEXT_MUTED, marginLeft: 8 }}>({c.weight}%)</span>
                </div>
                <span style={{
                  fontSize: 16, fontWeight: 700,
                  color: c.score !== null ? GOLD : TEXT_MUTED,
                }}>
                  {c.score !== null ? c.score : '-'}
                  <span style={{ fontSize: 12, fontWeight: 400 }}> / {c.max_score}</span>
                </span>
              </div>
              {c.description && (
                <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 8 }}>{c.description}</div>
              )}
              <input
                type="range"
                min={0}
                max={c.max_score}
                value={c.score ?? 0}
                onChange={e => updateScore(c.id, Number(e.target.value))}
                style={{ width: '100%', accentColor: PRIMARY }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: TEXT_MUTED }}>
                <span>0</span>
                <span>{c.max_score}</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={handleSubmit} disabled={saving}
            style={{
              padding: '12px 32px', fontSize: 15, fontWeight: 600,
              background: PRIMARY, border: 'none', borderRadius: 8, color: TEXT_WHITE,
              cursor: 'pointer',
            }}>
            {saving ? 'Submitting...' : 'Submit Scores'}
          </button>
          <button onClick={closeScoring}
            style={{
              padding: '12px 24px', fontSize: 15,
              background: 'none', border: `1px solid ${BORDER}`, borderRadius: 8, color: TEXT_MUTED,
              cursor: 'pointer',
            }}>
            Back to List
          </button>
        </div>

        {timeRemaining <= 60 && timeRemaining > 0 && (
          <div style={{
            marginTop: 16, padding: '10px 16px', background: '#ff444420',
            border: `1px solid ${ERROR}`, borderRadius: 8,
            color: ERROR, fontSize: 13, fontWeight: 600,
          }}>
            Less than 1 minute remaining — scores will auto-submit when time runs out.
          </div>
        )}
      </div>
    );
  }

  // Priority queue list view
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ fontSize: 24 }}>Judge Portal</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={loadData}
            style={{
              padding: '8px 16px', fontSize: 13,
              background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6, color: TEXT_SECONDARY,
              cursor: 'pointer',
            }}>
            Refresh
          </button>
          <button onClick={() => navigate(`/hackathons/${hackathonId}/judging/results`)}
            style={{
              padding: '8px 16px', fontSize: 13,
              background: 'none', border: `1px solid ${BORDER}`, borderRadius: 6, color: TEXT_SECONDARY,
              cursor: 'pointer',
            }}>
            View Results
          </button>
        </div>
      </div>

      {loading ? (
        <p style={{ color: TEXT_MUTED }}>Loading priority queue...</p>
      ) : (
        <>
          {/* Priority queue */}
          <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden', marginBottom: 24 }}>
            <div style={{ padding: '12px 16px', borderBottom: `1px solid ${BORDER}` }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>Priority Queue</span>
              <span style={{ fontSize: 12, color: TEXT_MUTED, marginLeft: 8 }}>
                (projects ranked by judging need)
              </span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}`, textAlign: 'left' }}>
                  <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>#</th>
                  <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Project</th>
                  <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>ELO</th>
                  <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Judges</th>
                  <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Why</th>
                  <th style={{ padding: '10px 16px', color: TEXT_MUTED, fontWeight: 500 }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item, idx) => (
                  <tr key={item.submission_id} style={{ borderBottom: '1px solid #080c1a' }}>
                    <td style={{ padding: '10px 16px', color: TEXT_MUTED, fontSize: 12 }}>{idx + 1}</td>
                    <td style={{ padding: '10px 16px' }}>
                      <div style={{ fontWeight: 600 }}>{item.project_title || 'Untitled'}</div>
                      <a href={item.devpost_url} target="_blank" style={{ fontSize: 12, color: PRIMARY }}>
                        Devpost &rarr;
                      </a>
                    </td>
                    <td style={{ padding: '10px 16px', fontVariantNumeric: 'tabular-nums', fontFamily: 'monospace' }}>
                      {item.elo}
                    </td>
                    <td style={{ padding: '10px 16px', color: item.judge_count === 0 ? ERROR : TEXT_SECONDARY }}>
                      {item.judge_count}
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                        {item.reasons.map((reason) => (
                          <span key={reason} style={{
                            fontSize: 11,
                            padding: '1px 8px',
                            borderRadius: 8,
                            background: `${REASON_COLORS[reason] || TEXT_MUTED}18`,
                            color: REASON_COLORS[reason] || TEXT_MUTED,
                            whiteSpace: 'nowrap',
                          }}>
                            {REASON_LABELS[reason] || reason}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      {item.assignment_id ? (
                        <button onClick={() => openScoring(item.assignment_id!)}
                          style={{
                            padding: '6px 16px', background: PRIMARY, border: 'none', borderRadius: 6,
                            color: TEXT_WHITE, cursor: 'pointer', fontSize: 13,
                          }}>
                          Score
                        </button>
                      ) : (
                        <span style={{ fontSize: 12, color: TEXT_MUTED }}>No assignment</span>
                      )}
                    </td>
                  </tr>
                ))}
                {queue.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: 24, color: TEXT_MUTED }}>
                    All projects scored! Check back after more judges submit.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Uncertainty legend */}
          {queue.length > 0 && (
            <div style={{
              display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24,
              fontSize: 12, color: TEXT_MUTED,
            }}>
              <span>Uncertainty = judge disagreement (35%) + close races (30%) + coverage gaps (35%)</span>
            </div>
          )}

          {/* Completed */}
          {completed.length > 0 && (
            <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, overflow: 'hidden' }}>
              <h3 style={{ fontSize: 14, padding: '12px 16px', color: TEXT_MUTED, margin: 0 }}>
                Completed by You ({completed.length})
              </h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                <tbody>
                  {completed.map(a => (
                    <tr key={a.id} style={{ borderBottom: '1px solid #080c1a' }}>
                      <td style={{ padding: '10px 16px' }}>{a.project_title}</td>
                      <td style={{ padding: '10px 16px' }}>
                        <span style={{
                          padding: '2px 8px', borderRadius: 10, fontSize: 12,
                          background: `${SUCCESS}20`, color: SUCCESS,
                        }}>
                          Completed
                        </span>
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
