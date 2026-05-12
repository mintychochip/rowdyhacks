import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import InviteCodeManager from '../components/InviteCodeManager';
import OAuthAdminPanel from '../components/OAuthAdminPanel';
import {
  CARD_BG, INPUT_BG, PRIMARY, SUCCESS, SUCCESS_BG10,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  BORDER, BORDER_LIGHT, INPUT_BORDER, ERROR, ERROR_TEXT, ERROR_BG10, ERROR_BORDER30,
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
  registration_mode: string | null;
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
  const [registrationMode, setRegistrationMode] = useState('open');

  // Assistant documents state
  const [documents, setDocuments] = useState<Array<{ id: string; filename: string; chunk_count: number; s3_url?: string; created_at?: string }>>([]);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState('');
  const [docSuccess, setDocSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Multi-file upload state
  const [dragOver, setDragOver] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<Array<{ file: File; status: 'pending' | 'uploading' | 'done' | 'error'; message?: string }>>([]);

  // Re-index state
  const [reindexing, setReindexing] = useState(false);
  const [reindexResult, setReindexResult] = useState('');

  useEffect(() => {
    if (!id || !user) { setLoading(false); return; }
    loadHackathon();
    loadDocuments();
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
      setRegistrationMode(data.registration_mode || 'open');
    } catch (e: any) {
      setError(e.message || 'Failed to load hackathon');
    }
    setLoading(false);
  };

  const loadDocuments = async () => {
    if (!id) return;
    setDocLoading(true);
    try {
      const res = await api.getAssistantDocuments(id);
      setDocuments(res.documents || []);
    } catch {
      // ignore — documents are optional
    } finally {
      setDocLoading(false);
    }
  };

  const handleFileUpload = async (files: FileList | null) => {
    if (!id || !files || files.length === 0) return;
    setDocError('');
    setDocSuccess('');

    const queue = Array.from(files).map((file) => ({ file, status: 'pending' as const }));
    setUploadQueue(queue);

    for (let i = 0; i < queue.length; i++) {
      setUploadQueue((prev) => {
        const next = [...prev];
        next[i] = { ...next[i], status: 'uploading' };
        return next;
      });
      try {
        const res = await api.uploadAssistantDocument(id, queue[i].file);
        setUploadQueue((prev) => {
          const next = [...prev];
          next[i] = { ...next[i], status: 'done', message: `${res.chunk_count} chunks indexed` };
          return next;
        });
      } catch (e: any) {
        setUploadQueue((prev) => {
          const next = [...prev];
          next[i] = { ...next[i], status: 'error', message: e.message || 'Upload failed' };
          return next;
        });
      }
    }

    // Refresh document list and clear queue after a short delay
    await loadDocuments();
    setTimeout(() => {
      setUploadQueue([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }, 3000);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const handleReindex = async () => {
    setReindexing(true);
    setReindexResult('');
    setDocError('');
    try {
      const res = await api.indexResources();
      setReindexResult(`Re-indexed ${res.indexed_count} of ${res.total_pages} pages.`);
    } catch (e: any) {
      setDocError(e.message || 'Re-index failed');
    } finally {
      setReindexing(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!id) return;
    setDocError('');
    setDocSuccess('');
    try {
      await api.deleteAssistantDocument(id, docId);
      setDocSuccess('Document deleted.');
      await loadDocuments();
    } catch (e: any) {
      setDocError(e.message || 'Delete failed');
    }
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
        registration_mode: registrationMode || undefined,
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
          background: ERROR_BG10, border: `1px solid ${ERROR}`, borderRadius: RADIUS.md,
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
                      background: 'none', border: 'none', color: ERROR, cursor: 'pointer',
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
              background: importResult.error ? ERROR_BG10 : SUCCESS_BG10,
              color: importResult.error ? ERROR_TEXT : SUCCESS, fontSize: 13,
            }}>
              {importResult.error
                ? importResult.error
                : `Found ${importResult.found} projects — ${importResult.imported} new, ${importResult.skipped} already imported. Analysis queued.`}
            </div>
          )}
        </div>
      </div>

      {/* Registration Section */}
      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: SPACE.lg, marginBottom: SPACE.md,
      }}>
        <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>Registration</h3>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Registration Mode</label>
          <select
            value={registrationMode}
            onChange={(e) => setRegistrationMode(e.target.value)}
            style={{
              width: '100%', padding: '10px 14px', background: INPUT_BG,
              border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
              color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none',
            }}
          >
            <option value="open">Open</option>
            <option value="invite_only">Invite Only</option>
          </select>
          <p style={{ fontSize: 12, color: TEXT_MUTED, marginTop: SPACE.xs }}>
            Open allows anyone to register. Invite Only requires a code.
          </p>
        </div>
      </div>

      {/* Knowledge Base / Documents Section */}
      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: SPACE.lg, marginBottom: SPACE.md,
      }}>
        <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>Assistant Knowledge Base</h3>
        <p style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: SPACE.md }}>
          Upload documents (.txt, .md, .pdf) so the AI assistant can answer questions about them.
        </p>

        {docError && (
          <div style={{
            background: ERROR_BG10, border: `1px solid ${ERROR}`, borderRadius: RADIUS.md,
            padding: '10px 16px', marginBottom: SPACE.md, color: ERROR_TEXT, fontSize: 14,
          }}>
            {docError}
          </div>
        )}

        {docSuccess && (
          <div style={{
            background: SUCCESS_BG10, border: `1px solid ${SUCCESS}`, borderRadius: RADIUS.md,
            padding: '10px 16px', marginBottom: SPACE.md, color: SUCCESS, fontSize: 14,
          }}>
            {docSuccess}
          </div>
        )}

        {reindexResult && (
          <div style={{
            background: SUCCESS_BG10, border: `1px solid ${SUCCESS}`, borderRadius: RADIUS.md,
            padding: '10px 16px', marginBottom: SPACE.md, color: SUCCESS, fontSize: 14,
          }}>
            {reindexResult}
          </div>
        )}

        {/* Drag-and-drop zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? PRIMARY : BORDER_LIGHT}`,
            borderRadius: RADIUS.md,
            padding: SPACE.lg,
            textAlign: 'center',
            cursor: 'pointer',
            background: dragOver ? `${PRIMARY}10` : INPUT_BG,
            transition: 'all 0.2s ease',
            marginBottom: SPACE.md,
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,.pdf,.markdown"
            multiple
            onChange={(e) => handleFileUpload(e.target.files)}
            style={{ display: 'none' }}
          />
          <p style={{ color: TEXT_MUTED, fontSize: 14, margin: 0 }}>
            {dragOver ? 'Drop files here' : 'Drag & drop files here, or click to browse'}
          </p>
          <p style={{ color: TEXT_MUTED, fontSize: 12, margin: '4px 0 0' }}>
            Supports .txt, .md, .pdf
          </p>
        </div>

        {/* Upload queue / per-file status */}
        {uploadQueue.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm, marginBottom: SPACE.md }}>
            {uploadQueue.map((item, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: SPACE.sm, background: INPUT_BG, borderRadius: RADIUS.sm,
                border: `1px solid ${BORDER_LIGHT}`,
              }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: 13, color: TEXT_PRIMARY, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.file.name}
                  </div>
                  <div style={{ fontSize: 11, color: TEXT_MUTED }}>
                    {(item.file.size / 1024).toFixed(1)} KB
                  </div>
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, marginLeft: SPACE.md, whiteSpace: 'nowrap' }}>
                  {item.status === 'pending' && <span style={{ color: TEXT_MUTED }}>Waiting...</span>}
                  {item.status === 'uploading' && <span style={{ color: PRIMARY }}>Uploading...</span>}
                  {item.status === 'done' && <span style={{ color: SUCCESS }}>{item.message}</span>}
                  {item.status === 'error' && <span style={{ color: ERROR }}>{item.message}</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Re-index button */}
        <div style={{ marginBottom: SPACE.md }}>
          <button
            onClick={handleReindex}
            disabled={reindexing}
            style={{
              padding: '10px 24px', background: reindexing ? INPUT_BG : SUCCESS,
              border: 'none', borderRadius: RADIUS.md, color: TEXT_WHITE,
              fontSize: 14, fontWeight: 600, cursor: reindexing ? 'not-allowed' : 'pointer',
              opacity: reindexing ? 0.6 : 1,
            }}
          >
            {reindexing ? 'Re-indexing...' : 'Re-index All Resources'}
          </button>
        </div>

        {/* Uploaded documents list */}
        {docLoading ? (
          <p style={{ color: TEXT_MUTED, fontSize: 14 }}>Loading documents...</p>
        ) : documents.length === 0 ? (
          <p style={{ color: TEXT_MUTED, fontSize: 14 }}>No documents uploaded yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
            {documents.map((doc) => (
              <div key={doc.id} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: SPACE.md, background: INPUT_BG, borderRadius: RADIUS.md,
                border: `1px solid ${BORDER_LIGHT}`,
              }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: 14, color: TEXT_PRIMARY, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {doc.filename}
                  </div>
                  <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>
                    {doc.chunk_count} chunks indexed
                    {doc.s3_url && (
                      <a href={doc.s3_url} target="_blank" rel="noopener noreferrer" style={{ color: PRIMARY, marginLeft: 8, textDecoration: 'none' }}>
                        View file
                      </a>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteDocument(doc.id)}
                  style={{
                    background: 'none', border: 'none', color: ERROR,
                    cursor: 'pointer', fontSize: 13, fontWeight: 600,
                    marginLeft: SPACE.md,
                  }}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <InviteCodeManager hackathonId={id!} />
      <OAuthAdminPanel />

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
