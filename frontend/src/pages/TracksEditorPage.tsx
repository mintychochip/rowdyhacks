import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import {
  PRIMARY, GOLD, CYAN, SUCCESS, WARNING, ERROR, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, INPUT_BORDER, BORDER,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface Track {
  id: string;
  name: string;
  description: string;
  challenge: string;
  icon: string;
  color: string;
  prize: string;
  track_type?: string | null;
  criteria: string[];
  resources: { name: string; url: string }[];
}

const COLORS = ['#8b5cf6', '#06b6d4', '#fbbf24', '#ec4899', '#10b981', '#f97316', '#ef4444', '#6366f1'];

export default function TracksEditorPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Track | null>(null);
  const [saving, setSaving] = useState(false);
  const [criteriaInput, setCriteriaInput] = useState('');
  const [resourceName, setResourceName] = useState('');
  const [resourceUrl, setResourceUrl] = useState('');

  const loadTracks = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.getHackathonTracks(id);
      setTracks(data.tracks || []);
    } catch { /* empty */ }
    setLoading(false);
  }, [id]);

  useEffect(() => {
    loadTracks();
  }, [loadTracks]);

  const startEdit = (track?: Track) => {
    if (track) {
      setEditing({ ...track, criteria: [...track.criteria], resources: [...track.resources] });
      setCriteriaInput('');
      setResourceName('');
      setResourceUrl('');
    } else {
      setEditing({
        id: '', name: '', description: '', challenge: '', icon: '🛸', color: COLORS[0],
        prize: '', track_type: null, criteria: [], resources: [],
      });
      setCriteriaInput('');
      setResourceName('');
      setResourceUrl('');
    }
  };

  const addCriteria = () => {
    if (!editing || !criteriaInput.trim()) return;
    setEditing({ ...editing, criteria: [...editing.criteria, criteriaInput.trim()] });
    setCriteriaInput('');
  };

  const removeCriteria = (idx: number) => {
    if (!editing) return;
    setEditing({ ...editing, criteria: editing.criteria.filter((_, i) => i !== idx) });
  };

  const addResource = () => {
    if (!editing || !resourceName.trim() || !resourceUrl.trim()) return;
    setEditing({ ...editing, resources: [...editing.resources, { name: resourceName.trim(), url: resourceUrl.trim() }] });
    setResourceName('');
    setResourceUrl('');
  };

  const removeResource = (idx: number) => {
    if (!editing) return;
    setEditing({ ...editing, resources: editing.resources.filter((_, i) => i !== idx) });
  };

  const saveTrack = async () => {
    if (!editing || !id) return;
    setSaving(true);
    try {
      const body = {
        name: editing.name,
        description: editing.description,
        challenge: editing.challenge,
        icon: editing.icon,
        color: editing.color,
        prize: editing.prize,
        track_type: editing.track_type || null,
        criteria: editing.criteria,
        resources: editing.resources,
      };
      if (editing.id) {
        await api.request(`/hackathons/${id}/tracks/${editing.id}`, { method: 'PUT', body: JSON.stringify(body) });
      } else {
        await api.request(`/hackathons/${id}/tracks`, { method: 'POST', body: JSON.stringify(body) });
      }
      setEditing(null);
      loadTracks();
    } catch { }
    setSaving(false);
  };

  const deleteTrack = async (trackId: string) => {
    if (!id || !confirm('Delete this track?')) return;
    try {
      await api.request(`/hackathons/${id}/tracks/${trackId}`, { method: 'DELETE' });
      loadTracks();
    } catch { }
  };

  if (loading) return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Loading tracks...</p>;

  if (user?.role !== 'organizer') {
    return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Organizer access only.</p>;
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: SPACE.lg }}>
        <div>
          <Link to={`/hackathons/${id}/tracks`} style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none' }}>&larr; View Tracks</Link>
          <h1 style={{ ...TYPO.h1, marginTop: SPACE.xs }}>Edit Tracks</h1>
        </div>
        <button onClick={() => startEdit()} style={{
          padding: '10px 20px', background: PRIMARY, border: 'none', borderRadius: RADIUS.md,
          color: TEXT_WHITE, fontSize: 14, fontWeight: 600, cursor: 'pointer',
        }}>
          + New Track
        </button>
      </div>

      {/* Track list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm, marginBottom: SPACE.xl }}>
        {tracks.map(track => (
          <div key={track.id} style={{
            display: 'flex', alignItems: 'center', gap: SPACE.md,
            background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.md,
            padding: SPACE.md,
          }}>
            <div style={{
              width: 40, height: 40, borderRadius: RADIUS.sm,
              background: `${track.color}20`, display: 'flex',
              alignItems: 'center', justifyContent: 'center', fontSize: 20,
            }}>{track.icon}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: track.color, display: 'flex', alignItems: 'center', gap: 8 }}>
                {track.name}
                {track.track_type && (
                  <span style={{
                    padding: '1px 8px', borderRadius: RADIUS.full,
                    background: `${PRIMARY}20`, color: PRIMARY,
                    fontSize: 11, fontWeight: 600, textTransform: 'capitalize',
                  }}>{track.track_type}</span>
                )}
              </div>
              <div style={{ fontSize: 12, color: TEXT_MUTED }}>{track.prize}</div>
            </div>
            <button onClick={() => startEdit(track)} style={{
              padding: '6px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
              borderRadius: RADIUS.sm, color: TEXT_PRIMARY, cursor: 'pointer', fontSize: 13,
            }}>Edit</button>
            <button onClick={() => deleteTrack(track.id)} style={{
              padding: '6px 14px', background: 'none', border: 'none',
              color: ERROR, cursor: 'pointer', fontSize: 13,
            }}>Delete</button>
          </div>
        ))}
      </div>

      {/* Edit modal */}
      {editing && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(10,10,18,0.9)',
          backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 100, padding: SPACE.md,
        }} onClick={() => setEditing(null)}>
          <div style={{
            background: CARD_BG, border: `1px solid ${editing.color || BORDER}`,
            borderRadius: RADIUS.lg, padding: SPACE.xl, maxWidth: 700, width: '100%',
            maxHeight: '90vh', overflow: 'auto',
          }} onClick={e => e.stopPropagation()}>
            <h2 style={{ ...TYPO.h2, marginBottom: SPACE.lg }}>
              {editing.id ? 'Edit Track' : 'New Track'}
            </h2>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: SPACE.md }}>
              <div>
                <label style={fieldLabel}>Name</label>
                <input value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })} style={fieldStyle} />
              </div>
              <div>
                <label style={fieldLabel}>Prize</label>
                <input value={editing.prize} onChange={e => setEditing({ ...editing, prize: e.target.value })} style={fieldStyle} />
              </div>
              <div>
                <label style={fieldLabel}>Icon</label>
                <input value={editing.icon} onChange={e => setEditing({ ...editing, icon: e.target.value })} style={fieldStyle} />
              </div>
              <div>
                <label style={fieldLabel}>Color</label>
                <div style={{ display: 'flex', gap: 4 }}>
                  {COLORS.map(c => (
                    <button key={c} onClick={() => setEditing({ ...editing, color: c })} style={{
                      width: 28, height: 28, borderRadius: '50%', background: c,
                      border: editing.color === c ? '2px solid white' : '2px solid transparent',
                      cursor: 'pointer',
                    }} />
                  ))}
                </div>
              </div>
              <div>
                <label style={fieldLabel}>Track Type</label>
                <select
                  value={editing.track_type || ''}
                  onChange={e => setEditing({ ...editing, track_type: e.target.value || null })}
                  style={fieldStyle}
                >
                  <option value="">General</option>
                  <option value="prize">Prize</option>
                  <option value="themed">Themed</option>
                  <option value="sponsor">Sponsor</option>
                </select>
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={fieldLabel}>Short Description</label>
                <textarea value={editing.description} onChange={e => setEditing({ ...editing, description: e.target.value })} rows={2}
                  style={fieldStyle} />
              </div>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={fieldLabel}>Challenge Prompt</label>
                <textarea value={editing.challenge} onChange={e => setEditing({ ...editing, challenge: e.target.value })} rows={4}
                  style={fieldStyle} />
              </div>
            </div>

            {/* Criteria */}
            <div style={{ marginTop: SPACE.lg }}>
              <label style={fieldLabel}>Judging Criteria</label>
              <div style={{ display: 'flex', gap: SPACE.sm, marginBottom: SPACE.sm }}>
                <input value={criteriaInput} onChange={e => setCriteriaInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCriteria(); } }}
                  placeholder="Add criterion..." style={{ ...fieldStyle, flex: 1 }} />
                <button onClick={addCriteria} style={{
                  padding: '8px 16px', background: PRIMARY, border: 'none',
                  borderRadius: RADIUS.sm, color: TEXT_WHITE, cursor: 'pointer', fontSize: 13,
                }}>Add</button>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACE.xs }}>
                {editing.criteria.map((c, i) => (
                  <span key={i} style={{
                    padding: '4px 10px', borderRadius: RADIUS.full,
                    background: `${editing.color}20`, color: editing.color,
                    fontSize: 13, display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    {c}
                    <button onClick={() => removeCriteria(i)} style={{
                      background: 'none', border: 'none', color: 'inherit',
                      cursor: 'pointer', padding: 0, fontSize: 16, lineHeight: 1,
                    }}>×</button>
                  </span>
                ))}
              </div>
            </div>

            {/* Resources */}
            <div style={{ marginTop: SPACE.lg }}>
              <label style={fieldLabel}>Resources</label>
              <div style={{ display: 'flex', gap: SPACE.sm, marginBottom: SPACE.sm }}>
                <input value={resourceName} onChange={e => setResourceName(e.target.value)}
                  placeholder="Name" style={{ ...fieldStyle, flex: 1 }} />
                <input value={resourceUrl} onChange={e => setResourceUrl(e.target.value)}
                  placeholder="URL" style={{ ...fieldStyle, flex: 2 }} />
                <button onClick={addResource} style={{
                  padding: '8px 16px', background: CYAN, border: 'none',
                  borderRadius: RADIUS.sm, color: TEXT_WHITE, cursor: 'pointer', fontSize: 13,
                }}>Add</button>
              </div>
              {editing.resources.map((r, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm, marginBottom: 4 }}>
                  <span style={{ fontSize: 13, color: CYAN }}>{r.name}</span>
                  <span style={{ fontSize: 12, color: TEXT_MUTED }}>{r.url}</span>
                  <button onClick={() => removeResource(i)} style={{
                    background: 'none', border: 'none', color: ERROR, cursor: 'pointer', fontSize: 16,
                  }}>×</button>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: SPACE.md, marginTop: SPACE.xl }}>
              <button onClick={saveTrack} disabled={saving} style={{
                padding: '10px 24px', background: PRIMARY, border: 'none',
                borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 14,
                fontWeight: 600, cursor: 'pointer', flex: 1,
              }}>
                {saving ? 'Saving...' : 'Save Track'}
              </button>
              <button onClick={() => setEditing(null)} style={{
                padding: '10px 24px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
                borderRadius: RADIUS.md, color: TEXT_MUTED, fontSize: 14, cursor: 'pointer',
              }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Add edit link to the tracks view */}
      <div style={{ textAlign: 'center', marginTop: SPACE.lg, paddingTop: SPACE.lg, borderTop: `1px solid ${BORDER}` }}>
        <Link to={`/hackathons/${id}/tracks`} style={{ color: PRIMARY, textDecoration: 'none', fontSize: 14 }}>
          View public tracks page →
        </Link>
      </div>
    </div>
  );
}

const fieldLabel: React.CSSProperties = { display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 4 };
const fieldStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
  borderRadius: 6, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box',
};
