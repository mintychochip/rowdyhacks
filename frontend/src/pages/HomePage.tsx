import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useCountdown } from '../hooks/useCountdown';
import * as api from '../services/api';
import QRCodeDisplay from '../components/QRCodeDisplay';
import WalletButtons from '../components/WalletButtons';
import ScheduleGrid from '../components/ScheduleGrid';
import { Badge } from '../components/Primitives';

interface ScheduleEvent { datetime: string; title: string; description?: string; location?: string; }
interface HackathonData {
  id: string; name: string; start_date: string; end_date: string; description: string | null;
  schedule: ScheduleEvent[] | null; wifi_ssid: string | null; wifi_password: string | null;
  discord_invite_url: string | null;
}
interface ScanItem { id: string; scan_type: string; scanned_at: string; }
interface RegData {
  id: string; status: string; team_name: string | null;
  qr_token: string | null; registered_at: string; accepted_at: string | null; checked_in_at: string | null;
  scan_count?: number; scans?: ScanItem[];
}

const STATUS_COLORS: Record<string, { bg: string; color: string; border: string }> = {
  pending: { bg: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.2)' },
  accepted: { bg: 'rgba(34, 197, 94, 0.1)', color: '#22c55e', border: 'rgba(34, 197, 94, 0.2)' },
  rejected: { bg: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.2)' },
  checked_in: { bg: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6', border: 'rgba(59, 130, 246, 0.2)' },
};

const SCAN_LABELS: Record<string, string> = { checkin: 'Check-in', meal: 'Meal', workshop: 'Workshop' };

// Icons
const CalendarIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>
    <line x1="16" x2="16" y1="2" y2="6"/>
    <line x1="8" x2="8" y1="2" y2="6"/>
    <line x1="3" x2="21" y1="10" y2="10"/>
  </svg>
);

const MapPinIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>
    <circle cx="12" cy="10" r="3"/>
  </svg>
);

const UsersIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const ClockIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>
);

const TrophyIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>
    <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>
    <path d="M4 22h16"/>
    <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>
    <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>
    <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
  </svg>
);

const ArrowRightIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14"/>
    <path d="m12 5 7 7-7 7"/>
  </svg>
);

const WifiIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12.55a11 11 0 0 1 14.08 0"/>
    <path d="M1.42 9a16 16 0 0 1 21.16 0"/>
    <path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
    <line x1="12" x2="12.01" y1="20" y2="20"/>
  </svg>
);

const CopyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
    <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
  </svg>
);

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 6 9 17l-5-5"/>
  </svg>
);

const DiscordIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
  </svg>
);

export default function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();

  const [hackathon, setHackathon] = useState<HackathonData | null>(null);
  const [registration, setRegistration] = useState<RegData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const [regName, setRegName] = useState('');
  const [registering, setRegistering] = useState(false);
  const [regError, setRegError] = useState('');

  const countdown = useCountdown(
    hackathon?.end_date || new Date().toISOString(),
    hackathon?.start_date,
  );

  useEffect(() => { loadHome(); }, [user]);

  const loadHome = async () => {
    if (user?.role === 'participant') {
      try {
        const hacks = await api.getHackathons();
        if (hacks && hacks.length > 0) {
          navigate(`/hackathons/${hacks[0].id}/hacker-dashboard`, { replace: true });
          return;
        }
      } catch {}
    }

    setLoading(true);
    setError('');
    try {
      const hacks = await api.getHackathons();
      if (!hacks || hacks.length === 0) { setLoading(false); return; }
      const latest = hacks[0];

      if (user) {
        const regs = await api.getMyRegistrations();
        const mine = (regs.registrations || []).find((r: any) => r.hackathon_id === latest.id);

        if (mine && (mine.status === 'accepted' || mine.status === 'checked_in')) {
          const dash = await api.getHackerDashboard(latest.id);
          setHackathon(dash.hackathon);
          setRegistration(dash.registration);
        } else {
          const hk = await api.getHackathon(latest.id);
          setHackathon(hk);
          if (mine) setRegistration(mine);
        }
      } else {
        const hk = await api.getHackathon(latest.id);
        setHackathon(hk);
      }
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hackathon) return;
    setRegistering(true); setRegError('');
    try {
      const reg = await api.registerForHackathon(hackathon.id, { team_name: regName.trim() || undefined });
      setRegistration(reg); setRegName('');
    } catch (err: any) { setRegError(err.message); }
    setRegistering(false);
  };

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {}
  };

  if (loading) return (
    <div style={{
      minHeight: '60vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '24px',
    }}>
      <div style={{
        width: '48px',
        height: '48px',
        border: '3px solid var(--border-default)',
        borderTop: '3px solid var(--accent-primary)',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
      }} />
      <p style={{ color: 'var(--text-tertiary)', fontSize: '14px', margin: 0 }}>Loading...</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );

  // Not logged in - Hero landing
  if (!user) {
    return (
      <div style={{
        maxWidth: 1200,
        margin: '0 auto',
        padding: isMobile ? '40px 16px' : '80px 24px',
      }}>
        {/* Hero section */}
        <div style={{
          textAlign: 'center',
          marginBottom: isMobile ? 60 : 100,
        }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            background: 'var(--accent-subtle)',
            border: '1px solid rgba(139, 92, 246, 0.2)',
            borderRadius: 100,
            marginBottom: 32,
          }}>
            <span style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: 'var(--accent-primary)',
              animation: 'pulse 2s ease-in-out infinite',
            }} />
            <span style={{
              fontSize: 13,
              fontWeight: 500,
              color: 'var(--accent-primary)',
            }}>
              Feb 15-17, 2026
            </span>
          </div>

          <h1 style={{
            fontSize: isMobile ? 40 : 64,
            fontWeight: 700,
            lineHeight: 1.1,
            letterSpacing: '-0.03em',
            marginBottom: 24,
            color: 'var(--text-primary)',
            background: 'linear-gradient(135deg, var(--text-primary) 0%, var(--text-secondary) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            Build something<br />worth showing off
          </h1>

          <p style={{
            fontSize: isMobile ? 17 : 20,
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
            marginBottom: 40,
            maxWidth: 560,
            margin: '0 auto 40px',
          }}>
            36 hours, 800+ hackers, real prizes. No pitch decks required.
          </p>

          <div style={{
            display: 'flex',
            gap: 16,
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'wrap',
          }}>
            <Link to="/auth" style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              padding: '14px 28px',
              background: 'var(--accent-primary)',
              color: 'white',
              fontSize: 15,
              fontWeight: 500,
              textDecoration: 'none',
              borderRadius: 10,
              transition: 'all 150ms ease',
              boxShadow: '0 4px 20px rgba(139, 92, 246, 0.3)',
            }}>
              Get Ticket
              <ArrowRightIcon />
            </Link>
            <Link to="/tracks" style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '14px 24px',
              background: 'transparent',
              color: 'var(--text-secondary)',
              fontSize: 15,
              fontWeight: 500,
              textDecoration: 'none',
              borderRadius: 10,
              border: '1px solid var(--border-default)',
              transition: 'all 150ms ease',
            }}>
              View tracks
            </Link>
          </div>
        </div>

        {/* Stats grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(4, 1fr)',
          gap: 16,
        }}>
          {[
            { icon: <UsersIcon />, value: '800+', label: 'Hackers', sublabel: 'University students & developers' },
            { icon: <ClockIcon />, value: '36h', label: 'Duration', sublabel: 'Non-stop building & learning' },
            { icon: <TrophyIcon />, value: '$50K', label: 'Prizes', sublabel: 'Cash, internships & swag' },
            { icon: <MapPinIcon />, value: 'Bakersfield', label: 'Location', sublabel: 'Downtown venue' },
          ].map((stat, i) => (
            <div key={i} style={{
              padding: 24,
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 12,
              transition: 'all 150ms ease',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 40,
                height: 40,
                borderRadius: 10,
                background: 'var(--accent-subtle)',
                color: 'var(--accent-primary)',
                marginBottom: 16,
              }}>
                {stat.icon}
              </div>
              <div style={{
                fontSize: 32,
                fontWeight: 700,
                color: 'var(--text-primary)',
                marginBottom: 4,
                letterSpacing: '-0.02em',
              }}>
                {stat.value}
              </div>
              <div style={{
                fontSize: 14,
                fontWeight: 500,
                color: 'var(--text-secondary)',
                marginBottom: 2,
              }}>
                {stat.label}
              </div>
              <div style={{
                fontSize: 12,
                color: 'var(--text-muted)',
              }}>
                {stat.sublabel}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // No hackathon
  if (!hackathon) {
    const isOrganizer = user.role === 'organizer';
    return (
      <div style={{
        maxWidth: 640,
        margin: '0 auto',
        padding: isMobile ? '60px 16px' : '100px 24px',
        textAlign: 'center',
      }}>
        <div style={{
          width: 80,
          height: 80,
          borderRadius: 20,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-default)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 24px',
          fontSize: 40,
        }}>
          📅
        </div>
        <h1 style={{
          fontSize: 28,
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: 12,
        }}>
          No Active Events
        </h1>
        <p style={{
          fontSize: 16,
          color: 'var(--text-secondary)',
          marginBottom: 32,
        }}>
          {isOrganizer ? 'Set up your first hackathon event to get started.' : 'Check back later for upcoming hackathons.'}
        </p>
        {isOrganizer && (
          <Link to="/hackathons" style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 10,
            padding: '14px 28px',
            background: 'var(--accent-primary)',
            color: 'white',
            fontSize: 15,
            fontWeight: 500,
            textDecoration: 'none',
            borderRadius: 10,
            boxShadow: '0 4px 20px rgba(139, 92, 246, 0.3)',
          }}>
            Create Event
            <ArrowRightIcon />
          </Link>
        )}
      </div>
    );
  }

  const isOrganizer = user.role === 'organizer';
  const isAccepted = registration && (registration.status === 'accepted' || registration.status === 'checked_in');
  const scanUrl = registration?.qr_token ? `${window.location.origin}/api/checkin/scan?token=${registration.qr_token}` : '';

  // Accepted / Checked-in Dashboard
  if (isAccepted) {
    return (
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 32,
          flexWrap: 'wrap',
          gap: 16,
        }}>
          <div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              marginBottom: 8,
            }}>
              <h1 style={{
                fontSize: 28,
                fontWeight: 600,
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
              }}>
                {hackathon.name}
              </h1>
              <span style={{
                padding: '4px 12px',
                background: STATUS_COLORS[registration.status]?.bg || 'var(--bg-tertiary)',
                color: STATUS_COLORS[registration.status]?.color || 'var(--text-secondary)',
                border: `1px solid ${STATUS_COLORS[registration.status]?.border || 'var(--border-default)'}`,
                borderRadius: 100,
                fontSize: 12,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                {registration.status === 'checked_in' ? 'Checked In' : 'Accepted'}
              </span>
            </div>
            <p style={{
              fontSize: 15,
              color: 'var(--text-secondary)',
              margin: 0,
            }}>
              Hacker Dashboard
            </p>
          </div>

          {hackathon.discord_invite_url && (
            <a
              href={hackathon.discord_invite_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 18px',
                background: 'rgba(88, 101, 242, 0.1)',
                border: '1px solid rgba(88, 101, 242, 0.2)',
                borderRadius: 10,
                color: '#5865F2',
                fontSize: 14,
                fontWeight: 500,
                textDecoration: 'none',
                transition: 'all 150ms ease',
              }}
            >
              <DiscordIcon />
              Join Discord
            </a>
          )}
        </div>

        {/* Main grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : '1fr 380px',
          gap: 24,
          alignItems: 'start',
        }}>
          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* QR Code Card */}
            <div style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 12,
              padding: 32,
              textAlign: 'center',
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'center',
                marginBottom: 24,
              }}>
                <div style={{
                  padding: 20,
                  background: 'white',
                  borderRadius: 12,
                }}>
                  <QRCodeDisplay token={scanUrl} size={isMobile ? 180 : 220} />
                </div>
              </div>
              <p style={{
                fontSize: 14,
                color: 'var(--text-secondary)',
                marginBottom: 16,
              }}>
                Show this QR code at check-in and meal times
              </p>
              <WalletButtons />
              {registration.checked_in_at && (
                <div style={{
                  marginTop: 20,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 16px',
                  borderRadius: 100,
                  background: 'var(--success-subtle)',
                  color: 'var(--success)',
                  fontSize: 13,
                  fontWeight: 500,
                }}>
                  <CheckIcon />
                  Checked in {new Date(registration.checked_in_at).toLocaleDateString()}
                </div>
              )}
            </div>

            {/* WiFi Card */}
            {hackathon.wifi_ssid && (
              <div style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-default)',
                borderRadius: 12,
                padding: 24,
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  marginBottom: 20,
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 36,
                    height: 36,
                    borderRadius: 10,
                    background: 'var(--bg-tertiary)',
                    color: 'var(--text-secondary)',
                  }}>
                    <WifiIcon />
                  </div>
                  <h3 style={{
                    fontSize: 16,
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    margin: 0,
                  }}>
                    WiFi Access
                  </h3>
                </div>

                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 16px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 10,
                    border: '1px solid var(--border-default)',
                  }}>
                    <div>
                      <div style={{
                        fontSize: 11,
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        marginBottom: 4,
                      }}>
                        Network
                      </div>
                      <div style={{
                        fontSize: 16,
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                      }}>
                        {hackathon.wifi_ssid}
                      </div>
                    </div>
                    <button
                      onClick={() => copyToClipboard(hackathon.wifi_ssid!, 'ssid')}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '8px 12px',
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border-default)',
                        borderRadius: 8,
                        color: copiedField === 'ssid' ? 'var(--success)' : 'var(--text-secondary)',
                        fontSize: 13,
                        cursor: 'pointer',
                        transition: 'all 150ms ease',
                      }}
                    >
                      {copiedField === 'ssid' ? <CheckIcon /> : <CopyIcon />}
                      {copiedField === 'ssid' ? 'Copied' : 'Copy'}
                    </button>
                  </div>

                  {hackathon.wifi_password && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '14px 16px',
                      background: 'var(--bg-tertiary)',
                      borderRadius: 10,
                      border: '1px solid var(--border-default)',
                    }}>
                      <div>
                        <div style={{
                          fontSize: 11,
                          color: 'var(--text-muted)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          marginBottom: 4,
                        }}>
                          Password
                        </div>
                        <div style={{
                          fontSize: 16,
                          fontWeight: 500,
                          color: 'var(--text-primary)',
                          fontFamily: 'var(--font-mono)',
                        }}>
                          {hackathon.wifi_password}
                        </div>
                      </div>
                      <button
                        onClick={() => copyToClipboard(hackathon.wifi_password!, 'password')}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '8px 12px',
                          background: 'var(--bg-elevated)',
                          border: '1px solid var(--border-default)',
                          borderRadius: 8,
                          color: copiedField === 'password' ? 'var(--success)' : 'var(--text-secondary)',
                          fontSize: 13,
                          cursor: 'pointer',
                          transition: 'all 150ms ease',
                        }}
                      >
                        {copiedField === 'password' ? <CheckIcon /> : <CopyIcon />}
                        {copiedField === 'password' ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Schedule */}
            <ScheduleGrid events={hackathon.schedule || []} />

            {/* Scan History */}
            <div style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 12,
              padding: 24,
            }}>
              <h3 style={{
                fontSize: 16,
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: 16,
                display: 'flex',
                alignItems: 'center',
                gap: 12,
              }}>
                Scan History
                {registration.scan_count ? (
                  <span style={{
                    padding: '3px 10px',
                    background: 'var(--accent-subtle)',
                    color: 'var(--accent-primary)',
                    borderRadius: 100,
                    fontSize: 12,
                    fontWeight: 600,
                  }}>
                    {registration.scan_count}
                  </span>
                ) : null}
              </h3>
              {(!registration.scans || registration.scans.length === 0) ? (
                <p style={{ color: 'var(--text-tertiary)', fontSize: 14, margin: 0 }}>
                  No scans yet. Visit check-in points to get scanned.
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {registration.scans.map(scan => (
                    <div key={scan.id} style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 16,
                      padding: '12px 16px',
                      background: 'var(--bg-tertiary)',
                      borderRadius: 10,
                      border: '1px solid var(--border-default)',
                    }}>
                      <span style={{
                        padding: '4px 12px',
                        borderRadius: 100,
                        fontSize: 12,
                        fontWeight: 600,
                        textTransform: 'capitalize',
                        background: scan.scan_type === 'checkin' ? 'var(--success-subtle)' :
                                   scan.scan_type === 'meal' ? 'var(--warning-subtle)' :
                                   'var(--accent-subtle)',
                        color: scan.scan_type === 'checkin' ? 'var(--success)' :
                              scan.scan_type === 'meal' ? 'var(--warning)' :
                              'var(--accent-primary)',
                      }}>
                        {SCAN_LABELS[scan.scan_type] || scan.scan_type}
                      </span>
                      <span style={{
                        fontSize: 13,
                        color: 'var(--text-muted)',
                        marginLeft: 'auto',
                      }}>
                        {new Date(scan.scanned_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right column: Countdown */}
          <div style={{
            position: isMobile ? 'static' : 'sticky',
            top: 80,
          }}>
            <div style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 12,
              padding: 28,
              textAlign: 'center',
            }}>
              <div style={{
                fontSize: 12,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                color: 'var(--text-muted)',
                marginBottom: 20,
              }}>
                {countdown.isExpired ? 'Event Ended' : 'Time Remaining'}
              </div>

              {countdown.isExpired ? (
                <div style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: 'var(--text-secondary)',
                }}>
                  Finished
                </div>
              ) : (
                <>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: 12,
                    marginBottom: 24,
                  }}>
                    {[
                      { label: 'Days', value: countdown.days },
                      { label: 'Hours', value: countdown.hours },
                      { label: 'Min', value: countdown.minutes },
                      { label: 'Sec', value: countdown.seconds },
                    ].map(unit => (
                      <div key={unit.label}>
                        <div style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: isMobile ? 28 : 36,
                          fontWeight: 700,
                          fontVariantNumeric: 'tabular-nums',
                          color: 'var(--accent-primary)',
                          lineHeight: 1.1,
                        }}>
                          {String(unit.value).padStart(2, '0')}
                        </div>
                        <div style={{
                          fontSize: 10,
                          color: 'var(--text-muted)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.1em',
                          marginTop: 6,
                        }}>
                          {unit.label}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div style={{
                    height: 6,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 3,
                    overflow: 'hidden',
                    marginBottom: 12,
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${countdown.elapsedPercent}%`,
                      background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))',
                      borderRadius: 3,
                      transition: 'width 1s linear',
                    }} />
                  </div>

                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 11,
                    color: 'var(--text-muted)',
                  }}>
                    <span>Start</span>
                    <span>{countdown.elapsedPercent}%</span>
                    <span>End</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // NOT REGISTERED - Application form
  const startDate = new Date(hackathon.start_date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  const endDate = new Date(hackathon.end_date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <div style={{ maxWidth: 560, margin: '0 auto', padding: isMobile ? '20px 16px' : '40px 24px' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 14px',
          background: 'var(--accent-subtle)',
          border: '1px solid rgba(139, 92, 246, 0.2)',
          borderRadius: 100,
          marginBottom: 20,
        }}>
          <CalendarIcon />
          <span style={{
            fontSize: 12,
            fontWeight: 500,
            color: 'var(--accent-primary)',
          }}>
            {startDate} – {endDate}
          </span>
        </div>

        <h1 style={{
          fontSize: isMobile ? 26 : 32,
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
          marginBottom: 12,
        }}>
          {hackathon.name}
        </h1>

        {hackathon.description && (
          <p style={{
            fontSize: 15,
            color: 'var(--text-secondary)',
            maxWidth: 480,
            margin: '0 auto',
          }}>
            {hackathon.description}
          </p>
        )}
      </div>

      {/* NOT REGISTERED */}
      {!isOrganizer && !registration && (
        <div style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-default)',
          borderRadius: 12,
          padding: 32,
        }}>
          <h2 style={{
            fontSize: 18,
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 8,
          }}>
            Apply to participate
          </h2>
          <p style={{
            color: 'var(--text-secondary)',
            fontSize: 14,
            marginBottom: 24,
          }}>
            Submit your application to join the hackathon.
          </p>

          <form onSubmit={handleRegister}>
            <div style={{ marginBottom: 20 }}>
              <label style={{
                display: 'block',
                fontSize: 12,
                fontWeight: 500,
                color: 'var(--text-secondary)',
                marginBottom: 8,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}>
                Display name (optional)
              </label>
              <input
                value={regName}
                onChange={e => setRegName(e.target.value)}
                placeholder="Your name or team name"
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 10,
                  color: 'var(--text-primary)',
                  fontSize: 15,
                  outline: 'none',
                  transition: 'all 150ms ease',
                }}
              />
            </div>

            {regError && (
              <div style={{
                background: 'var(--error-subtle)',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                borderRadius: 10,
                padding: '12px 16px',
                marginBottom: 20,
                color: 'var(--error)',
                fontSize: 14,
              }}>
                {regError}
              </div>
            )}

            <button
              type="submit"
              disabled={registering}
              style={{
                width: '100%',
                padding: '14px 20px',
                background: 'var(--accent-primary)',
                border: 'none',
                borderRadius: 10,
                color: 'white',
                fontSize: 15,
                fontWeight: 500,
                cursor: registering ? 'not-allowed' : 'pointer',
                opacity: registering ? 0.7 : 1,
                transition: 'all 150ms ease',
                boxShadow: '0 4px 20px rgba(139, 92, 246, 0.3)',
              }}
            >
              {registering ? 'Submitting...' : 'Submit Application'}
            </button>
          </form>
        </div>
      )}

      {/* PENDING */}
      {registration && registration.status === 'pending' && (
        <div style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--warning-subtle)',
          borderRadius: 12,
          padding: 40,
          textAlign: 'center',
        }}>
          <div style={{
            width: 64,
            height: 64,
            borderRadius: 16,
            background: 'var(--warning-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            fontSize: 28,
          }}>
            ✉️
          </div>

          <span style={{
            display: 'inline-block',
            padding: '4px 12px',
            background: 'var(--warning-subtle)',
            color: 'var(--warning)',
            borderRadius: 100,
            fontSize: 12,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 16,
          }}>
            Pending Review
          </span>

          <h2 style={{
            fontSize: 20,
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 12,
          }}>
            Application submitted
          </h2>

          <p style={{
            color: 'var(--text-secondary)',
            fontSize: 15,
            marginBottom: 8,
          }}>
            {registration.team_name || user.name}
          </p>

          <p style={{
            color: 'var(--text-muted)',
            fontSize: 14,
          }}>
            Your application is being reviewed. You'll see your QR pass here once accepted.
          </p>
        </div>
      )}

      {/* REJECTED */}
      {registration && registration.status === 'rejected' && (
        <div style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--error-subtle)',
          borderRadius: 12,
          padding: 40,
          textAlign: 'center',
        }}>
          <span style={{
            display: 'inline-block',
            padding: '4px 12px',
            background: 'var(--error-subtle)',
            color: 'var(--error)',
            borderRadius: 100,
            fontSize: 12,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 16,
          }}>
            Not Accepted
          </span>

          <p style={{
            color: 'var(--text-secondary)',
            fontSize: 15,
          }}>
            Your application was not accepted for this event.
          </p>
        </div>
      )}

      {/* ORGANIZER TOOLS */}
      {isOrganizer && (
        <div style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-default)',
          borderRadius: 12,
          padding: 24,
          marginTop: registration ? 24 : 0,
        }}>
          <h3 style={{
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 16,
          }}>
            Organizer Tools
          </h3>

          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 10,
          }}>
            {[
              { label: 'Manage Registrations', onClick: () => navigate(`/hackathons/${hackathon.id}/registrations`), primary: true },
              { label: 'Event Settings', onClick: () => navigate(`/hackathons/${hackathon.id}/settings`) },
              { label: 'Set Up Judging', onClick: () => navigate(`/hackathons/${hackathon.id}/judging/setup`) },
              { label: 'View Results', onClick: () => navigate(`/hackathons/${hackathon.id}/judging/results`) },
              { label: 'Score Projects', onClick: () => navigate(`/hackathons/${hackathon.id}/judging`) },
              { label: 'Check-In Scanner', onClick: () => navigate('/check-in') },
            ].map((btn, i) => (
              <button
                key={i}
                onClick={btn.onClick}
                style={{
                  padding: '10px 18px',
                  background: btn.primary ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                  border: '1px solid',
                  borderColor: btn.primary ? 'transparent' : 'var(--border-default)',
                  borderRadius: 8,
                  color: btn.primary ? 'white' : 'var(--text-secondary)',
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 150ms ease',
                }}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
