import { useState, useEffect } from 'react';
import * as api from '../services/api';
import { CARD_BG, INPUT_BG, INPUT_BORDER, PRIMARY, TEXT_PRIMARY, TEXT_MUTED, BORDER, RADIUS, SPACE, CYAN, SUCCESS } from '../theme';

interface Prefs {
  channel: string;
  registration_updates: boolean;
  announcements: boolean;
  judging_updates: boolean;
  team_requests: boolean;
  mentor_requests: boolean;
}

export default function NotificationPrefsPage() {
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getNotificationPrefs().then(setPrefs).catch(() => {});
  }, []);

  const update = async (patch: Partial<Prefs>) => {
    setSaving(true);
    try {
      const updated = await api.updateNotificationPrefs(patch);
      setPrefs(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch { /* ignore */ }
    setSaving(false);
  };

  if (!prefs) return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: 40 }}>Loading...</p>;

  const toggleStyle = (enabled: boolean) => ({
    width: 44, height: 24, borderRadius: 12, border: 'none', cursor: 'pointer',
    background: enabled ? PRIMARY : INPUT_BG, position: 'relative' as const,
    transition: 'background 0.2s',
  });

  const dotStyle = (enabled: boolean) => ({
    position: 'absolute' as const, top: 2, width: 20, height: 20, borderRadius: '50%',
    background: '#fff', transition: 'left 0.2s',
    left: enabled ? 22 : 2,
  });

  const rows: { key: keyof Prefs; label: string; icon: string }[] = [
    { key: 'registration_updates', label: 'Registration Updates', icon: 'how_to_reg' },
    { key: 'announcements', label: 'Announcements', icon: 'campaign' },
    { key: 'judging_updates', label: 'Judging Updates', icon: 'gavel' },
    { key: 'team_requests', label: 'Team Requests', icon: 'group_add' },
    { key: 'mentor_requests', label: 'Mentor Requests', icon: 'school' },
  ];

  return (
    <div style={{ padding: SPACE.lg, maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: SPACE.lg }}>
        <span className="material-symbols-outlined" style={{ verticalAlign: 'middle', marginRight: 8, color: PRIMARY }}>notifications</span>
        Notification Preferences
      </h1>

      {saved && (
        <div style={{
          padding: `${SPACE.sm} ${SPACE.md}`, background: `${SUCCESS}15`, border: `1px solid ${SUCCESS}`,
          borderRadius: RADIUS.md, color: SUCCESS, fontSize: 13, marginBottom: SPACE.md,
        }}>Preferences saved</div>
      )}

      <div style={{
        background: CARD_BG, borderRadius: RADIUS.lg, padding: SPACE.lg,
        border: `1px solid ${BORDER}`, marginBottom: SPACE.lg,
      }}>
        <label style={{ display: 'block', fontSize: 14, fontWeight: 600, color: TEXT_PRIMARY, marginBottom: SPACE.sm }}>
          Notification Channel
        </label>
        <div style={{ display: 'flex', gap: SPACE.sm }}>
          {['email', 'discord', 'none'].map(ch => (
            <button key={ch} onClick={() => update({ channel: ch })} style={{
              padding: '8px 20px', borderRadius: RADIUS.md, border: `1px solid ${prefs.channel === ch ? PRIMARY : BORDER}`,
              background: prefs.channel === ch ? `${PRIMARY}20` : 'transparent',
              color: prefs.channel === ch ? PRIMARY : TEXT_MUTED, cursor: 'pointer',
              fontWeight: 500, textTransform: 'capitalize',
            }}>{ch}</button>
          ))}
        </div>
      </div>

      <div style={{
        background: CARD_BG, borderRadius: RADIUS.lg,
        border: `1px solid ${BORDER}`,
      }}>
        {rows.map((r, i) => (
          <div key={r.key} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: `${SPACE.md} ${SPACE.lg}`,
            borderBottom: i < rows.length - 1 ? `1px solid ${BORDER}` : 'none',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
              <span className="material-symbols-outlined" style={{ fontSize: 20, color: TEXT_MUTED }}>{r.icon}</span>
              <span style={{ fontSize: 14, color: TEXT_PRIMARY }}>{r.label}</span>
            </div>
            <button
              onClick={() => update({ [r.key]: !(prefs[r.key] as boolean) })}
              style={toggleStyle(prefs[r.key] as boolean)}
              disabled={saving}
            >
              <div style={dotStyle(prefs[r.key] as boolean)} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
