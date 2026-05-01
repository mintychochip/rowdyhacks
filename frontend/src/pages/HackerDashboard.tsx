import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useCountdown } from '../hooks/useCountdown';
import * as api from '../services/api';
import QRCodeDisplay from '../components/QRCodeDisplay';
import WalletButtons from '../components/WalletButtons';
import {
  PAGE_BG, CARD_BG, INPUT_BG, PRIMARY, PRIMARY_BG20,
  SUCCESS, SUCCESS_BG10, WARNING, WARNING_BG10, INFO, INFO_BG10,
  GOLD, GOLD_BG10,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  BORDER, BORDER_LIGHT, INPUT_BORDER,
  TYPO, SPACE, RADIUS, ERROR_TEXT,
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
}

interface ScanItem {
  id: string;
  scan_type: string;
  scanned_at: string;
}

interface RegistrationData {
  id: string;
  status: string;
  team_name: string | null;
  qr_token: string | null;
  scan_count: number;
  scans: ScanItem[];
}

const SCAN_ICONS: Record<string, string> = {
  checkin: '>>',
  meal: '🍽',
  workshop: '⚙',
};

const SCAN_LABELS: Record<string, string> = {
  checkin: 'Check-in',
  meal: 'Meal',
  workshop: 'Workshop',
};

export default function HackerDashboard() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();

  const [hackathon, setHackathon] = useState<HackathonData | null>(null);
  const [registration, setRegistration] = useState<RegistrationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const countdown = useCountdown(
    hackathon?.end_date || new Date().toISOString(),
    hackathon?.start_date,
  );

  useEffect(() => {
    if (!id || !user) { setLoading(false); return; }
    loadDashboard();
  }, [id, user]);

  const loadDashboard = async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.getHackerDashboard(id);
      setHackathon(data.hackathon);
      setRegistration(data.registration);

    } catch (e: any) {
      setError(e.message || 'Failed to load dashboard');
    }
    setLoading(false);
  };

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {}
  };

  // ── Loading State ──
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
        Loading dashboard...
      </div>
    );
  }

  // ── Error State ──
  if (error || !hackathon || !registration) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl }}>
        <p style={{ color: ERROR_TEXT, marginBottom: SPACE.md }}>{error || 'Dashboard not available'}</p>
        <button
          onClick={loadDashboard}
          style={{
            padding: '10px 20px', background: PRIMARY, border: 'none',
            borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 14, fontWeight: 600, cursor: 'pointer', marginRight: 8,
          }}
        >
          Retry
        </button>
        <button
          onClick={() => navigate('/hackathons')}
          style={{
            padding: '10px 20px', background: 'none', border: `1px solid ${INPUT_BORDER}`,
            borderRadius: RADIUS.md, color: TEXT_MUTED, fontSize: 14, cursor: 'pointer',
          }}
        >
          Back to Hackathons
        </button>
      </div>
    );
  }

  // ── Not Registered / Rejected ──
  if (registration.status === 'pending' || registration.status === 'rejected') {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
        <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.3 }}>--</div>
        <div style={{ fontSize: 16, marginBottom: 8 }}>
          {registration.status === 'pending' ? 'Your registration is pending approval.' : 'Your registration was not accepted.'}
        </div>
        <Link to={`/hackathons/${id}`} style={{ color: PRIMARY, textDecoration: 'none', fontWeight: 600, fontSize: 14 }}>
          View Hackathon Details
        </Link>
      </div>
    );
  }

  const scanUrl = registration.qr_token
    ? `${window.location.origin}/api/checkin/scan?token=${registration.qr_token}`
    : '';

  const sortedSchedule = hackathon.schedule
    ? [...hackathon.schedule].sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime())
    : [];

  const now = Date.now();
  const currentEventIndex = sortedSchedule.findIndex(
    (e) => new Date(e.datetime).getTime() > now
  );
  const currentEvent = currentEventIndex > 0 ? sortedSchedule[currentEventIndex - 1] : null;
  const nextEvent = currentEventIndex >= 0 ? sortedSchedule[currentEventIndex] : null;

  // Check if current event is happening now (within 2 hours before its start and 3 hours after)
  const isLive = (event: ScheduleEvent) => {
    const t = new Date(event.datetime).getTime();
    return now >= t - 2 * 60 * 60 * 1000 && now <= t + 3 * 60 * 60 * 1000;
  };

  return (
    <div style={{ padding: isMobile ? SPACE.md : SPACE.xl, maxWidth: 1200, margin: '0 auto' }}>
      {/* Back link */}
      <Link
        to={`/hackathons/${id}`}
        style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none', display: 'inline-block', marginBottom: SPACE.lg }}
      >
        &larr; Back to Hackathon
      </Link>

      <h1 style={{ ...TYPO.h1, marginBottom: SPACE.xs }}>{hackathon.name}</h1>
      <p style={{ color: TEXT_MUTED, marginBottom: SPACE.lg, fontSize: 14 }}>
        Hacker Dashboard
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '1fr 340px',
        gap: SPACE.lg,
        alignItems: 'start',
      }}>
        {/* ── Left Column ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.md }}>

          {/* QR Hero Card */}
          <div style={{
            background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
            padding: SPACE.lg, textAlign: 'center',
          }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: SPACE.md }}>
              <QRCodeDisplay token={scanUrl} size={isMobile ? 220 : 280} />
            </div>
            {registration.qr_token && (
              <div style={{
                fontFamily: "'Space Mono', monospace", fontSize: 11, color: TEXT_MUTED,
                wordBreak: 'break-all', marginBottom: SPACE.md, padding: '0 16px',
              }}>
                {registration.qr_token}
              </div>
            )}
            <WalletButtons />
            {registration.status === 'checked_in' && (
              <div style={{
                marginTop: SPACE.md, display: 'inline-block', padding: '4px 14px',
                borderRadius: RADIUS.full, background: SUCCESS_BG10, color: SUCCESS,
                fontSize: 13, fontWeight: 600,
              }}>
                Checked In
              </div>
            )}
          </div>

          {/* WiFi Card */}
          {hackathon.wifi_ssid && (
            <div style={{
              background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg,
            }}>
              <h3 style={{ ...TYPO.h3, marginBottom: SPACE.sm, display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={PRIMARY} strokeWidth="2"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1"/></svg>
                WiFi
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px', background: INPUT_BG, borderRadius: RADIUS.md,
                }}>
                  <div>
                    <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 2 }}>Network</div>
                    <div style={{ fontSize: 16, fontWeight: 600 }}>{hackathon.wifi_ssid}</div>
                  </div>
                  <button
                    onClick={() => copyToClipboard(hackathon.wifi_ssid!, 'ssid')}
                    style={{
                      background: 'none', border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.sm,
                      color: copiedField === 'ssid' ? SUCCESS : TEXT_MUTED, cursor: 'pointer',
                      padding: '4px 10px', fontSize: 12,
                    }}
                  >
                    {copiedField === 'ssid' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                {hackathon.wifi_password && (
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 14px', background: INPUT_BG, borderRadius: RADIUS.md,
                  }}>
                    <div>
                      <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 2 }}>Password</div>
                      <div style={{ fontSize: 16, fontWeight: 600 }}>{hackathon.wifi_password}</div>
                    </div>
                    <button
                      onClick={() => copyToClipboard(hackathon.wifi_password!, 'password')}
                      style={{
                        background: 'none', border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.sm,
                        color: copiedField === 'password' ? SUCCESS : TEXT_MUTED, cursor: 'pointer',
                        padding: '4px 10px', fontSize: 12,
                      }}
                    >
                      {copiedField === 'password' ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Discord Card */}
          {hackathon.discord_invite_url && (
            <div style={{
              background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg,
            }}>
              <h3 style={{ ...TYPO.h3, marginBottom: SPACE.sm, display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>
                Discord
              </h3>
              <a
                href={hackathon.discord_invite_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  padding: '10px 20px', background: '#5865F2', color: TEXT_WHITE,
                  borderRadius: RADIUS.md, textDecoration: 'none', fontSize: 14, fontWeight: 600,
                }}
              >
                Join Discord Server
              </a>
            </div>
          )}

          {/* Schedule Timeline */}
          {sortedSchedule.length > 0 && (
            <div style={{
              background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg,
            }}>
              <h3 style={{ ...TYPO.h3, marginBottom: SPACE.lg }}>Event Schedule</h3>
              <div style={{ position: 'relative' }}>
                {sortedSchedule.map((event, i) => {
                  const live = isLive(event);
                  const past = new Date(event.datetime).getTime() < now - 3 * 60 * 60 * 1000;
                  const eventTime = new Date(event.datetime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
                  const eventDate = new Date(event.datetime).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });

                  return (
                    <div key={i} style={{
                      display: 'flex', gap: SPACE.md, paddingBottom: i < sortedSchedule.length - 1 ? SPACE.lg : 0,
                      position: 'relative',
                    }}>
                      {/* Timeline line + dot */}
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 32, flexShrink: 0 }}>
                        <div style={{
                          width: 12, height: 12, borderRadius: '50%',
                          background: live ? SUCCESS : past ? TEXT_MUTED : PRIMARY,
                          boxShadow: live ? `0 0 12px ${SUCCESS}80` : 'none',
                          zIndex: 1,
                          flexShrink: 0,
                        }} />
                        {i < sortedSchedule.length - 1 && (
                          <div style={{
                            width: 2, flex: 1, background: BORDER_LIGHT,
                            marginTop: -2, minHeight: 40,
                          }} />
                        )}
                      </div>
                      {/* Event content */}
                      <div style={{
                        flex: 1, paddingBottom: SPACE.sm,
                        opacity: past ? 0.5 : 1,
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm, flexWrap: 'wrap', marginBottom: 2 }}>
                          <span style={{
                            fontSize: 14, fontWeight: 600, color: live ? SUCCESS : TEXT_PRIMARY,
                          }}>
                            {event.title}
                          </span>
                          {live && (
                            <span style={{
                              fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
                              padding: '2px 8px', borderRadius: RADIUS.full,
                              background: SUCCESS_BG10, color: SUCCESS,
                              letterSpacing: '0.05em',
                            }}>
                              LIVE NOW
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 2 }}>
                          {eventDate} at {eventTime}
                          {event.location && ` · ${event.location}`}
                        </div>
                        {event.description && (
                          <div style={{ fontSize: 13, color: TEXT_SECONDARY, marginTop: 4 }}>{event.description}</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              {nextEvent && (
                <div style={{
                  marginTop: SPACE.md, padding: '10px 14px', background: INPUT_BG, borderRadius: RADIUS.md,
                  display: 'flex', alignItems: 'center', gap: SPACE.sm,
                }}>
                  <span style={{ fontSize: 12, color: TEXT_MUTED }}>Next up:</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY }}>{nextEvent.title}</span>
                  <span style={{ fontSize: 12, color: TEXT_MUTED, marginLeft: 'auto' }}>
                    {new Date(nextEvent.datetime).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Scan History */}
          <div style={{
            background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg,
          }}>
            <h3 style={{ ...TYPO.h3, marginBottom: SPACE.sm, display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
              Scan History
              {registration.scan_count > 0 && (
                <span style={{
                  fontSize: 12, fontWeight: 700, padding: '2px 10px', borderRadius: RADIUS.full,
                  background: PRIMARY_BG20, color: PRIMARY,
                }}>
                  {registration.scan_count} scan{registration.scan_count !== 1 ? 's' : ''}
                </span>
              )}
            </h3>
            {registration.scans.length === 0 ? (
              <p style={{ color: TEXT_MUTED, fontSize: 14 }}>No scans yet.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
                {registration.scans.map((scan) => (
                  <div key={scan.id} style={{
                    display: 'flex', alignItems: 'center', gap: SPACE.md,
                    padding: '8px 12px', background: INPUT_BG, borderRadius: RADIUS.md,
                  }}>
                    <span style={{ fontSize: 18 }}>{SCAN_ICONS[scan.scan_type] || '>>'}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>{SCAN_LABELS[scan.scan_type] || scan.scan_type}</div>
                      <div style={{ fontSize: 12, color: TEXT_MUTED }}>
                        {new Date(scan.scanned_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Right Column: Countdown Timer (sticky on desktop) ── */}
        <div style={{
          position: isMobile ? 'static' : 'sticky',
          top: SPACE.lg,
        }}>
          <div style={{
            background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
            padding: SPACE.lg, textAlign: 'center',
          }}>
            <div style={{ fontSize: 13, color: TEXT_MUTED, marginBottom: SPACE.md, textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
              {countdown.isExpired ? 'Event Ended' : 'Time Remaining'}
            </div>

            {countdown.isExpired ? (
              <div style={{ fontSize: 24, fontWeight: 700, color: TEXT_SECONDARY }}>Finished</div>
            ) : (
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: SPACE.sm,
                marginBottom: SPACE.md,
              }}>
                {[
                  { label: 'Days', value: countdown.days },
                  { label: 'Hours', value: countdown.hours },
                  { label: 'Min', value: countdown.minutes },
                  { label: 'Sec', value: countdown.seconds },
                ].map((unit) => (
                  <div key={unit.label}>
                    <div style={{
                      fontFamily: "'Space Mono', monospace", fontSize: isMobile ? 28 : 36,
                      fontWeight: 700, fontVariantNumeric: 'tabular-nums',
                      color: GOLD, lineHeight: 1.1,
                    }}>
                      {String(unit.value).padStart(2, '0')}
                    </div>
                    <div style={{ fontSize: 10, color: TEXT_MUTED, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>
                      {unit.label}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Progress bar */}
            <div style={{
              height: 4, background: INPUT_BG, borderRadius: 2, overflow: 'hidden',
              marginTop: SPACE.sm,
            }}>
              <div style={{
                height: '100%', width: `${countdown.elapsedPercent}%`,
                background: `linear-gradient(90deg, ${PRIMARY}, ${GOLD})`,
                borderRadius: 2, transition: 'width 1s linear',
              }} />
            </div>
            <div style={{
              display: 'flex', justifyContent: 'space-between', marginTop: SPACE.xs,
              fontSize: 10, color: TEXT_MUTED,
            }}>
              <span>Start</span>
              <span>{countdown.elapsedPercent}%</span>
              <span>End</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
