import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import {
  PRIMARY, CYAN, SUCCESS, WARNING, ERROR, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, INPUT_BORDER, BORDER,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface Prize {
  id: string;
  hackathon_id: string;
  name: string;
  description: string | null;
  amount: string | null;
  currency: string | null;
  track_id: string | null;
}

export default function PrizesEditorPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [prizes, setPrizes] = useState<Prize[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Prize | null>(null);
  const [saving, setSaving] = useState(false);

  const loadPrizes = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.listPrizes(id);
      setPrizes(data || []);
    } catch { /* empty */ }
    setLoading(false);
  }, [id]);

  useEffect(() => {
    loadPrizes();
  }, [loadPrizes]);

  const startEdit = (prize?: Prize) => {
    if (prize) {
      setEditing({ ...prize });
    } else {
      setEditing({ id: '', hackathon_id: id || '', name: '', description: '', amount: '', currency: 'USD', track_id: null });
    }
  };

  const savePrize = async () => {
    if (!editing || !id) return;
    setSaving(true);
    try {
      const body = {
        name: editing.name,
        description: editing.description || undefined,
        amount: editing.amount || undefined,
        currency: editing.currency || undefined,
        track_id: editing.track_id || null,
      };
      if (editing.id) {
        await api.updatePrize(editing.id, body);
      } else {
        await api.createPrize({ hackathon_id: id, ...body });
      }
      setEditing(null);
      loadPrizes();
    } catch { }
    setSaving(false);
  };

  const deletePrize = async (prizeId: string) => {
    if (!confirm('Delete this prize?')) return;
    try {
      await api.deletePrize(prizeId);
      loadPrizes();
    } catch { }
  };

  if (loading) return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Loading prizes...</p>;

  if (user?.role !== 'organizer') {
    return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Organizer access only.</p>;
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: SPACE.lg }}>
        <div>
          <Link to={`/hackathons/${id}`} style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none' }}>&larr; Back to Hackathon</Link>
          <h1 style={{ ...TYPO.h1, marginTop: SPACE.xs }}>Edit Prizes</h1>
        </div>
        <button onClick={() => startEdit()} style={{
          padding: '10px 20px', background: PRIMARY, border: 'none', borderRadius: RADIUS.md,
          color: TEXT_WHITE, fontSize: 14, fontWeight: 600, cursor: 'pointer',
        }}>
          + New Prize
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm, marginBottom: SPACE.xl }}>
        {prizes.map(prize => (
          <div key={prize.id} style={{
            display: 'flex', alignItems: 'center', gap: SPACE.md,
            background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.md,
            padding: SPACE.md,
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: TEXT_PRIMARY }}>{prize.name}</div>
              <div style={{ fontSize: 12, color: TEXT_MUTED }}>{prize.amount} {prize.currency}{prize.description ? ` — ${prize.description}` : ''}</div>
            </div>
            <button onClick={() => startEdit(prize)} style={{
              padding: '6px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
              borderRadius: RADIUS.sm, color: TEXT_PRIMARY, cursor: 'pointer', fontSize: 13,
            }}>Edit</button>
            <button onClick={() => deletePrize(prize.id)} style={{
              padding: '6px 14px', background: 'none', border: 'none',
              color: ERROR, cursor: 'pointer', fontSize: 13,
            }}>Delete</button>
          </div>
        ))}
        {prizes.length === 0 && (
          <p style={{ color: TEXT_MUTED, fontSize: 14, textAlign: 'center', padding: SPACE.lg }}>No prizes yet. Add your first prize above.</p>
        )}
      </div>

      {editing && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(10,10,18,0.9)',
          backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 100, padding: SPACE.md,
        }} onClick={() => setEditing(null)}>
          <div style={{
            background: CARD_BG, border: `1px solid ${BORDER}`,
            borderRadius: RADIUS.lg, padding: SPACE.xl, maxWidth: 600, width: '100%',
            maxHeight: '90vh', overflow: 'auto',
          }} onClick={e => e.stopPropagation()}>
            <h2 style={{ ...TYPO.h2, marginBottom: SPACE.lg }}>{editing.id ? 'Edit Prize' : 'New Prize'}</h2>
            <div style={{ display: 'grid', gap: SPACE.md }}>
              <div>
                <label style={fieldLabel}>Name</label>
                <input value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })} style={fieldStyle} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: SPACE.md }}>
                <div>
                  <label style={fieldLabel}>Amount</label>
                  <input value={editing.amount || ''} onChange={e => setEditing({ ...editing, amount: e.target.value })} style={fieldStyle} />
                </div>
                <div>
                  <label style={fieldLabel}>Currency</label>
                  <input value={editing.currency || ''} onChange={e => setEditing({ ...editing, currency: e.target.value })} style={fieldStyle} />
                </div>
              </div>
              <div>
                <label style={fieldLabel}>Description</label>
                <textarea value={editing.description || ''} onChange={e => setEditing({ ...editing, description: e.target.value })} rows={3} style={fieldStyle} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: SPACE.md, marginTop: SPACE.xl }}>
              <button onClick={savePrize} disabled={saving} style={{
                padding: '10px 24px', background: PRIMARY, border: 'none',
                borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 14,
                fontWeight: 600, cursor: 'pointer', flex: 1,
              }}>
                {saving ? 'Saving...' : 'Save Prize'}
              </button>
              <button onClick={() => setEditing(null)} style={{
                padding: '10px 24px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
                borderRadius: RADIUS.md, color: TEXT_MUTED, fontSize: 14, cursor: 'pointer',
              }}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const fieldLabel: React.CSSProperties = { display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 4 };
const fieldStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
  borderRadius: 6, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box',
};
