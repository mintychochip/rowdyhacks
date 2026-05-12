import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import {
  PRIMARY, CYAN, SUCCESS, WARNING, ERROR, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, INPUT_BORDER, BORDER,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface Sponsor {
  id: string;
  hackathon_id: string;
  name: string;
  tier: string | null;
  logo_url: string | null;
  website_url: string | null;
  description: string | null;
}

const TIERS = ['Platinum', 'Gold', 'Silver', 'Bronze', 'Partner', 'In-Kind'];

export default function SponsorsEditorPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [sponsors, setSponsors] = useState<Sponsor[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Sponsor | null>(null);
  const [saving, setSaving] = useState(false);

  const loadSponsors = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await api.listSponsors(id);
      setSponsors(data || []);
    } catch { /* empty */ }
    setLoading(false);
  }, [id]);

  useEffect(() => {
    loadSponsors();
  }, [loadSponsors]);

  const startEdit = (sponsor?: Sponsor) => {
    if (sponsor) {
      setEditing({ ...sponsor });
    } else {
      setEditing({ id: '', hackathon_id: id || '', name: '', tier: '', logo_url: '', website_url: '', description: '' });
    }
  };

  const saveSponsor = async () => {
    if (!editing || !id) return;
    setSaving(true);
    try {
      const body = {
        name: editing.name,
        tier: editing.tier || undefined,
        logo_url: editing.logo_url || undefined,
        website_url: editing.website_url || undefined,
        description: editing.description || undefined,
      };
      if (editing.id) {
        await api.updateSponsor(editing.id, body);
      } else {
        await api.createSponsor({ hackathon_id: id, ...body });
      }
      setEditing(null);
      loadSponsors();
    } catch { }
    setSaving(false);
  };

  const deleteSponsor = async (sponsorId: string) => {
    if (!confirm('Delete this sponsor?')) return;
    try {
      await api.deleteSponsor(sponsorId);
      loadSponsors();
    } catch { }
  };

  if (loading) return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Loading sponsors...</p>;

  if (user?.role !== 'organizer') {
    return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Organizer access only.</p>;
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: SPACE.lg }}>
        <div>
          <Link to={`/hackathons/${id}`} style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none' }}>&larr; Back to Hackathon</Link>
          <h1 style={{ ...TYPO.h1, marginTop: SPACE.xs }}>Edit Sponsors</h1>
        </div>
        <button onClick={() => startEdit()} style={{
          padding: '10px 20px', background: PRIMARY, border: 'none', borderRadius: RADIUS.md,
          color: TEXT_WHITE, fontSize: 14, fontWeight: 600, cursor: 'pointer',
        }}>
          + New Sponsor
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm, marginBottom: SPACE.xl }}>
        {sponsors.map(sponsor => (
          <div key={sponsor.id} style={{
            display: 'flex', alignItems: 'center', gap: SPACE.md,
            background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.md,
            padding: SPACE.md,
          }}>
            <div style={{
              width: 40, height: 40, borderRadius: RADIUS.sm,
              background: INPUT_BG, display: 'flex',
              alignItems: 'center', justifyContent: 'center', fontSize: 20,
            }}>{sponsor.logo_url ? <img src={sponsor.logo_url} alt="" style={{ width: 32, height: 32, objectFit: 'contain' }} /> : '🏢'}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: TEXT_PRIMARY }}>{sponsor.name}</div>
              <div style={{ fontSize: 12, color: TEXT_MUTED }}>{sponsor.tier}{sponsor.website_url ? ` • ${sponsor.website_url}` : ''}</div>
            </div>
            <button onClick={() => startEdit(sponsor)} style={{
              padding: '6px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
              borderRadius: RADIUS.sm, color: TEXT_PRIMARY, cursor: 'pointer', fontSize: 13,
            }}>Edit</button>
            <button onClick={() => deleteSponsor(sponsor.id)} style={{
              padding: '6px 14px', background: 'none', border: 'none',
              color: ERROR, cursor: 'pointer', fontSize: 13,
            }}>Delete</button>
          </div>
        ))}
        {sponsors.length === 0 && (
          <p style={{ color: TEXT_MUTED, fontSize: 14, textAlign: 'center', padding: SPACE.lg }}>No sponsors yet. Add your first sponsor above.</p>
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
            <h2 style={{ ...TYPO.h2, marginBottom: SPACE.lg }}>{editing.id ? 'Edit Sponsor' : 'New Sponsor'}</h2>
            <div style={{ display: 'grid', gap: SPACE.md }}>
              <div>
                <label style={fieldLabel}>Name</label>
                <input value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })} style={fieldStyle} />
              </div>
              <div>
                <label style={fieldLabel}>Tier</label>
                <select
                  value={editing.tier || ''}
                  onChange={e => setEditing({ ...editing, tier: e.target.value || null })}
                  style={fieldStyle}
                >
                  <option value="">Select tier</option>
                  {TIERS.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label style={fieldLabel}>Logo URL</label>
                <input value={editing.logo_url || ''} onChange={e => setEditing({ ...editing, logo_url: e.target.value })} style={fieldStyle} />
              </div>
              <div>
                <label style={fieldLabel}>Website URL</label>
                <input value={editing.website_url || ''} onChange={e => setEditing({ ...editing, website_url: e.target.value })} style={fieldStyle} />
              </div>
              <div>
                <label style={fieldLabel}>Description</label>
                <textarea value={editing.description || ''} onChange={e => setEditing({ ...editing, description: e.target.value })} rows={3} style={fieldStyle} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: SPACE.md, marginTop: SPACE.xl }}>
              <button onClick={saveSponsor} disabled={saving} style={{
                padding: '10px 24px', background: PRIMARY, border: 'none',
                borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 14,
                fontWeight: 600, cursor: 'pointer', flex: 1,
              }}>
                {saving ? 'Saving...' : 'Save Sponsor'}
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
