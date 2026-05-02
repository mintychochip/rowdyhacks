import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import {
  CARD_BG, INPUT_BG, PRIMARY, SUCCESS, SUCCESS_BG10,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  BORDER, BORDER_LIGHT, INPUT_BORDER, ERROR_TEXT,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface ScheduleEvent {
  datetime: string;
  title: string;
  description?: string;
  location?: string;
}

interface HackathonData {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  description: string | null;
  schedule: ScheduleEvent[] | null;
  wifi_ssid: string | null;
  wifi_password: string | null;
  discord_invite_url: string | null;
  discord_webhook_url: string | null;
  devpost_url: string | null;
}

export default function HackathonSettings() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();

  const [hackathon, setHackathon] = useState<HackathonData | null>(null);
  const [schedule, setSchedule] = useState<ScheduleEvent[]>([]);
  const [wifiSsid, setWifiSsid] = useState('');
  const [wifiPassword, setWifiPassword] = useState('');
  const [discordUrl, setDiscordUrl] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [devpostUrl, setDevpostUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id || !user) { setLoading(false); return; }
    loadHackathon();
  }, [id, user]);

  const loadHackathon = async () => {
    if (!id) return;
    try {
      const data = await api.getHackathon(id);
      setHackathon(data);
      setSchedule(data.schedule || []);
      setWifiSsid(data.wifi_ssid || '');
      setWifiPassword(data.wifi_password || '');
      setDiscordUrl(data.discord_invite_url || '');
      setWebhookUrl(data.discord_webhook_url || '');
      setDevpostUrl(data.devpost_url || '');
    } catch (e: any) {
      setError(e.message || 'Failed to load hackathon');
    }
    setLoading(false);
  };

  const addEvent = () => {
    setSchedule([...schedule, { datetime: '', title: '', description: '', location: '' }]);
  };

  const removeEvent = (index: number) => {
    setSchedule(schedule.filter((_, i) => i !== index));
  };

  const updateEvent = (index: number, field: keyof ScheduleEvent, value: string) => {
    const updated = [...schedule];
    updated[index] = { ...updated[index], [field]: value };
    setSchedule(updated);
  };

  const handleSave = async () => {
    if (!id) return;
    setSaving(true);
    setError('');
    setSaved(false);
    try {
      const cleanSchedule = schedule
        .filter((e) => e.datetime && e.title)
        .map((e) => ({
          datetime: new Date(e.datetime).toISOString(),
          title: e.title,
          description: e.description || undefined,
          location: e.location || undefined,
        }));

      await api.updateHackathon(id, {
        schedule: cleanSchedule,
        wifi_ssid: wifiSsid || undefined,
        wifi_password: wifiPassword || undefined,
        discord_invite_url: discordUrl || undefined,
        discord_webhook_url: webhookUrl || undefined,
        devpost_url: devpostUrl || undefined,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e: any) {
      setError(e.message || 'Failed to save settings');
    }
    setSaving(false);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>Loading...</div>
    );
  }

  if (error && !hackathon) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl }}>
        <p style={{ color: ERROR_TEXT, marginBottom: SPACE.md }}>{error}</p>
        <button
          onClick={() => navigate('/hackathons')}
          style={{
            padding: '10px 20px', background: PRIMARY, border: 'none',
            borderRadius: RADIUS.md, color: TEXT_WHITE, cursor: 'pointer',
          }}
        >
          Back to Hackathons
        </button>
      </div>
    );
  }

  if (!hackathon) return null;

  // Redirect non-organizers
  if (user?.role !== 'organizer') {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
        <p>Only organizers can access event settings.</p>
        <Link to={`/hackathons/${id}`} style={{ color: PRIMARY, textDecoration: 'none', fontWeight: 600 }}>
          Back to Hackathon
        </Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      <Link
        to={`/hackathons/${id}`}
        style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none', display: 'inline-block', marginBottom: SPACE.lg }}
      >
        &larr; Back to Hackathon
      </Link>

      <h1 style={{ ...TYPO.h1, marginBottom: SPACE.xs }}>Event Settings</h1>
      <p style={{ color: TEXT_MUTED, marginBottom: SPACE.lg, fontSize: 14 }}>
        Configure schedule, WiFi, and Discord for {hackathon.name}
      </p>

      {/* Save notification */}
      {error && (
        <div style={{
          background: '#ff444420', border: '1px solid #ff4444', borderRadius: RADIUS.md,
          padding: '10px 16px', marginBottom: SPACE.md, color: ERROR_TEXT, fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {saved && (
        <div style={{
          background: SUCCESS_BG10, border: `1px solid ${SUCCESS}`, borderRadius: RADIUS.md,
          padding: '10px 16px', marginBottom: SPACE.md, color: SUCCESS, fontSize: 14,
        }}>
          Settings saved successfully!
        </div>
      )}

      {/* Schedule Section */}
      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: SPACE.lg, marginBottom: SPACE.md,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACE.md }}>
          <h3 style={{ ...TYPO.h3, margin: 0 }}>Schedule</h3>
          <button
            onClick={addEvent}
            style={{
              padding: '6px 14px', background: PRIMARY, border: 'none', borderRadius: RADIUS.sm,
              color: TEXT_WHITE, fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            + Add Event
          </button>
        </div>

        {schedule.length === 0 ? (
          <p style={{ color: TEXT_MUTED, fontSize: 14 }}>No events scheduled yet. Add your first event above.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
            {schedule.map((event, i) => (
              <div key={i} style={{
                padding: SPACE.md, background: INPUT_BG, borderRadius: RADIUS.md,
                border: `1px solid ${BORDER_LIGHT}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACE.sm }}>
                  <span style={{ fontSize: 12, color: TEXT_MUTED, fontWeight: 600 }}>Event {i + 1}</span>
                  <button
                    onClick={() => removeEvent(i)}
                    style={{
                      background: 'none', border: 'none', color: '#ff6b6b', cursor: 'pointer',
                      fontSize: 13, fontWeight: 600,
                    }}
                  >
                    Remove
                  </button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: SPACE.sm, marginBottom: SPACE.sm }}>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Date & Time *</label>
                    <input
                      type="datetime-local"
                      value={event.datetime ? event.datetime.slice(0, 16) : ''}
                      onChange={(e) => updateEvent(i, 'datetime', e.target.value)}
                      style={{
                        width: '100%', padding: '8px 12px', background: CARD_BG,
                        border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.sm,
                        color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Title *</label>
                    <input
                      type="text"
                      value={event.title}
                      onChange={(e) => updateEvent(i, 'title', e.target.value)}
                      placeholder="Opening Ceremony"
                      style={{
                        width: '100%', padding: '8px 12px', background: CARD_BG,
                        border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.sm,
                        color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
                      }}
                    />
                  </div>
                </div>
                <div style={{ marginBottom: SPACE.sm }}>
                  <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Location</label>
                  <input
                    type="text"
                    value={event.location || ''}
                    onChange={(e) => updateEvent(i, 'location', e.target.value)}
                    placeholder="Main Auditorium"
                    style={{
                      width: '100%', padding: '8px 12px', background: CARD_BG,
                      border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.sm,
                      color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Description</label>
                  <input
                    type="text"
                    value={event.description || ''}
                    onChange={(e) => updateEvent(i, 'description', e.target.value)}
                    placeholder="Brief description of the event"
                    style={{
                      width: '100%', padding: '8px 12px', background: CARD_BG,
                      border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.sm,
                      color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* WiFi Section */}
      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: SPACE.lg, marginBottom: SPACE.md,
      }}>
        <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>WiFi</h3>
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: SPACE.md }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>SSID (Network Name)</label>
            <input
              type="text"
              value={wifiSsid}
              onChange={(e) => setWifiSsid(e.target.value)}
              placeholder="Hackathon WiFi"
              style={{
                width: '100%', padding: '10px 14px', background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
                color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
              }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Password</label>
            <input
              type="text"
              value={wifiPassword}
              onChange={(e) => setWifiPassword(e.target.value)}
              placeholder="WiFi password"
              style={{
                width: '100%', padding: '10px 14px', background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
                color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
              }}
            />
          </div>
        </div>
      </div>

      {/* Discord Section */}
      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: SPACE.lg, marginBottom: SPACE.md,
      }}>
        <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>Discord</h3>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Invite URL</label>
          <input
            type="url"
            value={discordUrl}
            onChange={(e) => setDiscordUrl(e.target.value)}
            placeholder="https://discord.gg/..."
            style={{
              width: '100%', padding: '10px 14px', background: INPUT_BG,
              border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
              color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
            }}
          />
          <p style={{ fontSize: 12, color: TEXT_MUTED, marginTop: SPACE.xs }}>
            Shown to participants on their dashboard.
          </p>
        </div>
        <div style={{ marginTop: SPACE.md }}>
          <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Application Webhook URL</label>
          <input
            type="url"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://discord.com/api/webhooks/..."
            style={{
              width: '100%', padding: '10px 14px', background: INPUT_BG,
              border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
              color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
            }}
          />
          <p style={{ fontSize: 12, color: TEXT_MUTED, marginTop: SPACE.xs }}>
            New applications will be posted to this Discord channel.
          </p>
        </div>
      </div>

      {/* Devpost Section */}
      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: SPACE.lg, marginBottom: SPACE.md,
      }}>
        <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>Devpost Integration</h3>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Hackathon URL</label>
          <input
            type="url"
            value={devpostUrl}
            onChange={(e) => setDevpostUrl(e.target.value)}
            placeholder="https://csub-hacks.devpost.com"
            style={{
              width: '100%', padding: '10px 14px', background: INPUT_BG,
              border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
              color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
            }}
          />
          <p style={{ fontSize: 12, color: TEXT_MUTED, marginTop: SPACE.xs }}>
            Paste the URL of your Devpost hackathon page. Save settings first, then click Import below.
          </p>
        </div>
        <div style={{ marginTop: SPACE.md }}>
          <button
            onClick={async () => {
              if (!id || !devpostUrl) return;
              setImporting(true);
              setImportResult(null);
              try {
                const res = await api.request(`/hackathons/${id}/import-devpost`, { method: 'POST' });
                setImportResult(res);
              } catch (e: any) {
                setImportResult({ error: e.message || 'Import failed' });
              }
              setImporting(false);
            }}
            disabled={importing || !devpostUrl}
            style={{
              padding: '10px 24px', background: devpostUrl ? SUCCESS : INPUT_BG,
              border: 'none', borderRadius: RADIUS.md, color: TEXT_WHITE,
              fontSize: 14, fontWeight: 600, cursor: devpostUrl ? 'pointer' : 'not-allowed',
              opacity: importing ? 0.6 : 1,
            }}
          >
            {importing ? 'Importing...' : 'Import Submissions from Devpost'}
          </button>
          {importResult && (
            <div style={{
              marginTop: SPACE.sm, padding: SPACE.sm, borderRadius: RADIUS.sm,
              background: importResult.error ? '#ff444420' : SUCCESS_BG10,
              color: importResult.error ? ERROR_TEXT : SUCCESS, fontSize: 13,
            }}>
              {importResult.error
                ? importResult.error
                : `Found ${importResult.found} projects — ${importResult.imported} new, ${importResult.skipped} already imported. Analysis queued.`}
            </div>
          )}
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        disabled={saving}
        style={{
          width: '100%', padding: '14px 20px', background: PRIMARY,
          border: 'none', borderRadius: RADIUS.md, color: TEXT_WHITE,
          fontSize: 16, fontWeight: 700, cursor: saving ? 'not-allowed' : 'pointer',
          opacity: saving ? 0.6 : 1,
        }}
      >
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}
