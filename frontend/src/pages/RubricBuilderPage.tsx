import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import {
  PRIMARY, PRIMARY_HOVER, GOLD, SUCCESS, ERROR, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, INPUT_BORDER, BORDER, WARNING,
} from '../theme';

interface Criterion {
  name: string;
  description: string;
  max_score: number;
  weight: number;
}

const EMPTY_CRITERION: Criterion = { name: '', description: '', max_score: 10, weight: 30 };

export default function RubricBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [perProjectSeconds, setPerProjectSeconds] = useState(300);
  const [criteria, setCriteria] = useState<Criterion[]>([
    { name: 'Innovation', description: 'Originality and creativity of the idea', max_score: 10, weight: 30 },
    { name: 'Execution', description: 'Technical complexity and completeness', max_score: 10, weight: 30 },
    { name: 'Design', description: 'UI/UX and visual polish', max_score: 10, weight: 20 },
    { name: 'Pitch', description: 'Presentation and storytelling', max_score: 10, weight: 20 },
  ]);
  const [saving, setSaving] = useState(false);
  const [existingSession, setExistingSession] = useState<any>(null);

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    if (id) loadSession();
  }, [id, user]);

  const loadSession = async () => {
    try {
      const s = await api.getJudgingSession(id!);
      setExistingSession(s);
      setStartTime(s.start_time.slice(0, 16));
      setEndTime(s.end_time.slice(0, 16));
      setPerProjectSeconds(s.per_project_seconds);
      if (s.rubric?.criteria?.length) {
        setCriteria(s.rubric.criteria.map((c: any) => ({
          name: c.name,
          description: c.description || '',
          max_score: c.max_score,
          weight: c.weight,
        })));
      }
    } catch {
      // No session yet — use defaults
    }
  };

  const totalWeight = criteria.reduce((s, c) => s + c.weight, 0);

  const addCriterion = () => setCriteria([...criteria, { ...EMPTY_CRITERION, weight: Math.max(0, 100 - totalWeight) }]);
  const removeCriterion = (i: number) => setCriteria(criteria.filter((_, idx) => idx !== i));
  const updateCriterion = (i: number, field: keyof Criterion, value: string | number) => {
    const next = [...criteria];
    next[i] = { ...next[i], [field]: value };
    setCriteria(next);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totalWeight !== 100) return;
    setSaving(true);
    try {
      await api.createJudgingSession(id!, {
        start_time: new Date(startTime).toISOString(),
        end_time: new Date(endTime).toISOString(),
        per_project_seconds: perProjectSeconds,
        criteria: criteria.map((c, i) => ({ ...c, sort_order: i })),
      });
      setSaving(false);
      navigate(`/hackathons/${id}/judging`);
    } catch {
      setSaving(false);
    }
  };

  if (!user) return null;

  return (
    <div>
      <h2 style={{ fontSize: 24, marginBottom: 20 }} data-mobile-h1>Judging Setup</h2>

      <form onSubmit={handleSave}>
        {/* Timing */}
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, marginBottom: 16 }}>Judging Window</h3>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Opens (UTC)</label>
              <input type="datetime-local" value={startTime} onChange={e => setStartTime(e.target.value)} required
                style={{ padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: TEXT_WHITE, fontSize: 14 }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Closes (UTC)</label>
              <input type="datetime-local" value={endTime} onChange={e => setEndTime(e.target.value)} required
                style={{ padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: TEXT_WHITE, fontSize: 14 }} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Per project (seconds)</label>
              <input type="number" value={perProjectSeconds} onChange={e => setPerProjectSeconds(Number(e.target.value))}
                min={30} max={3600}
                style={{ padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: TEXT_WHITE, fontSize: 14, width: 80 }} />
            </div>
          </div>
        </div>

        {/* Rubric criteria */}
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24, marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16 }}>Criteria</h3>
            <span style={{
              fontSize: 13,
              color: totalWeight === 100 ? SUCCESS : ERROR,
              fontWeight: 600,
            }}>
              Total: {totalWeight}%
            </span>
          </div>

          {criteria.map((c, i) => (
            <div key={i} style={{
              display: 'flex', gap: 10, alignItems: 'flex-end', marginBottom: 12,
              padding: '12px', background: INPUT_BG, borderRadius: 8, flexWrap: 'wrap',
            }}>
              <div style={{ flex: 2, minWidth: 120 }}>
                <label style={{ display: 'block', fontSize: 11, color: TEXT_MUTED, marginBottom: 2 }}>Name</label>
                <input value={c.name} onChange={e => updateCriterion(i, 'name', e.target.value)}
                  placeholder="Innovation" required
                  style={{ width: '100%', padding: '6px 10px', background: CARD_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 4, color: TEXT_WHITE, fontSize: 13 }} />
              </div>
              <div style={{ flex: 3, minWidth: 160 }}>
                <label style={{ display: 'block', fontSize: 11, color: TEXT_MUTED, marginBottom: 2 }}>Description</label>
                <input value={c.description} onChange={e => updateCriterion(i, 'description', e.target.value)}
                  placeholder="What judges should evaluate..."
                  style={{ width: '100%', padding: '6px 10px', background: CARD_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 4, color: TEXT_WHITE, fontSize: 13 }} />
              </div>
              <div style={{ width: 70 }}>
                <label style={{ display: 'block', fontSize: 11, color: TEXT_MUTED, marginBottom: 2 }}>Max</label>
                <input type="number" value={c.max_score} onChange={e => updateCriterion(i, 'max_score', Number(e.target.value))}
                  min={1} max={100}
                  style={{ width: '100%', padding: '6px 10px', background: CARD_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 4, color: TEXT_WHITE, fontSize: 13 }} />
              </div>
              <div style={{ width: 70 }}>
                <label style={{ display: 'block', fontSize: 11, color: TEXT_MUTED, marginBottom: 2 }}>Weight %</label>
                <input type="number" value={c.weight} onChange={e => updateCriterion(i, 'weight', Number(e.target.value))}
                  min={0} max={100}
                  style={{ width: '100%', padding: '6px 10px', background: CARD_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 4, color: TEXT_WHITE, fontSize: 13 }} />
              </div>
              <button type="button" onClick={() => removeCriterion(i)}
                disabled={criteria.length <= 1}
                style={{
                  background: 'none', border: 'none', color: criteria.length <= 1 ? '#333' : ERROR,
                  cursor: criteria.length <= 1 ? 'default' : 'pointer', fontSize: 18, padding: '0 4px', lineHeight: '36px',
                }}>
                &times;
              </button>
            </div>
          ))}

          <button type="button" onClick={addCriterion}
            style={{
              background: 'none', border: `1px dashed ${INPUT_BORDER}`, borderRadius: 8, padding: '8px 16px',
              color: TEXT_MUTED, cursor: 'pointer', fontSize: 13, marginBottom: 16,
            }}>
            + Add Criterion
          </button>
        </div>

        <button type="submit" disabled={totalWeight !== 100 || saving}
          style={{
            padding: '12px 32px', fontSize: 15, fontWeight: 600,
            background: totalWeight === 100 ? PRIMARY : '#333',
            border: 'none', borderRadius: 8, color: TEXT_WHITE,
            cursor: totalWeight === 100 ? 'pointer' : 'not-allowed',
          }}>
          {saving ? 'Saving...' : 'Save Judging Config'}
        </button>
      </form>
    </div>
  );
}
