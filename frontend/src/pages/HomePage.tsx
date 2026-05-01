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
import {
  PRIMARY, PRIMARY_BG20, CYAN, SUCCESS, SUCCESS_BG10, WARNING, WARNING_BG10,
  ERROR, ERROR_TEXT, ERROR_BG20,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  INPUT_BG, INPUT_BORDER, CARD_BG, BORDER, BORDER_LIGHT,
  STATUS_ACCEPTED, STATUS_PENDING, STATUS_REJECTED, STATUS_CHECKED_IN,
  GOLD, GOLD_BG10,
  TYPO, SPACE, RADIUS,
} from '../theme';

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

const STATUS_COLORS: Record<string, string> = {
  pending: STATUS_PENDING, accepted: STATUS_ACCEPTED,
  rejected: STATUS_REJECTED, checked_in: STATUS_CHECKED_IN,
};

const SCAN_LABELS: Record<string, string> = { checkin: 'Check-in', meal: 'Meal', workshop: 'Workshop' };

export default function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();

  const [hackathon, setHackathon] = useState<HackathonData | null>(null);
  const [registration, setRegistration] = useState<RegData | null>(null);
  const [googleUrl, setGoogleUrl] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Register form
  const [regName, setRegName] = useState('');
  const [registering, setRegistering] = useState(false);
  const [regError, setRegError] = useState('');

  const countdown = useCountdown(
    hackathon?.end_date || new Date().toISOString(),
    hackathon?.start_date,
  );

  useEffect(() => { loadHome(); }, [user]);

  const loadHome = async () => {
    // Participants go straight to their dashboard, not the home page
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
        // Check if user has an accepted registration — use full dashboard endpoint
        const regs = await api.getMyRegistrations();
        const mine = (regs.registrations || []).find((r: any) => r.hackathon_id === latest.id);

        if (mine && (mine.status === 'accepted' || mine.status === 'checked_in')) {
          // Load full dashboard data
          const dash = await api.getHackerDashboard(latest.id);
          setHackathon(dash.hackathon);
          setRegistration(dash.registration);
          try {
            const gRes = await api.getGoogleWalletLink(dash.registration.id);
            setGoogleUrl(gRes.save_url);
          } catch {}
        } else {
          // Just load hackathon info + registration
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
    try { await navigator.clipboard.writeText(text); setCopiedField(field); setTimeout(() => setCopiedField(null), 2000); } catch {}
  };

  if (loading) return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Loading...</p>;

  // ── Not logged in ──
  if (!user) {
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? SPACE.xl : 80 }}>
        <div style={{ fontSize: 72, marginBottom: SPACE.lg, animation: 'float 6s ease-in-out infinite' }}>🚀</div>
        <h1 style={{ ...TYPO.h1, marginBottom: SPACE.sm }}>RowdyHacks: Cosmos</h1>
        <p style={{ color: TEXT_SECONDARY, fontSize: 18, marginBottom: SPACE.lg, maxWidth: 480, margin: '0 auto ' + SPACE.lg + 'px' }}>
          Launch your ideas into orbit. A 36-hour hackathon mission for the next generation of cosmic builders.
        </p>
        <Link to="/auth" style={{ display: 'inline-block', padding: '14px 36px', background: `linear-gradient(135deg, ${PRIMARY} 0%, ${CYAN} 100%)`, borderRadius: RADIUS.md, color: TEXT_WHITE, textDecoration: 'none', fontSize: 16, fontWeight: 700 }}>
          🚀 Launch Mission
        </Link>
      </div>
    );
  }

  // ── No hackathon ──
  if (!hackathon) {
    const isOrganizer = user.role === 'organizer';
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? SPACE.xl : 80 }}>
        <div style={{ fontSize: 56, marginBottom: SPACE.lg }}>🌌</div>
        <h1 style={{ ...TYPO.h1, marginBottom: SPACE.sm }}>Welcome to RowdyHacks: Cosmos</h1>
        <p style={{ color: TEXT_SECONDARY, fontSize: 16, marginBottom: SPACE.lg }}>
          {isOrganizer ? 'Initialize your first mission parameters.' : 'No active missions in orbit.'}
        </p>
        {isOrganizer && (
          <Link to="/hackathons" style={{ display: 'inline-block', padding: '14px 36px', background: PRIMARY, borderRadius: RADIUS.md, color: TEXT_WHITE, textDecoration: 'none', fontSize: 16, fontWeight: 700 }}>
            Initialize Mission
          </Link>
        )}
      </div>
    );
  }

  const isOrganizer = user.role === 'organizer';
  const isAccepted = registration && (registration.status === 'accepted' || registration.status === 'checked_in');
  const scanUrl = registration?.qr_token ? `${window.location.origin}/api/checkin/scan?token=${registration.qr_token}` : '';

  // ===================================================================
  // ACCEPTED / CHECKED_IN — Full Dashboard
  // ===================================================================
  if (isAccepted) {
    const now = Date.now();

    return (
      <div style={{ padding: isMobile ? SPACE.md : SPACE.xl, maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: SPACE.lg, flexWrap: 'wrap', gap: SPACE.md }}>
          <div>
            <h1 style={{ ...TYPO.h1, marginBottom: SPACE.xs }}>{hackathon.name}</h1>
            <p style={{ color: TEXT_MUTED, fontSize: 14, margin: 0 }}>Hacker Dashboard</p>
          </div>
          {hackathon.discord_invite_url && (
            <a href={hackathon.discord_invite_url} target="_blank" rel="noopener noreferrer" title="Join Discord"
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: 'rgba(88,101,242,0.15)', color: '#5865F2', borderRadius: RADIUS.md,
                padding: '8px 14px', textDecoration: 'none', fontSize: 13, fontWeight: 600,
              }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>
              Discord
            </a>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 340px', gap: SPACE.lg, alignItems: 'start' }}>
          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.md }}>

            {/* QR Hero Card */}
            <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg, textAlign: 'center' }}>
              <div style={{ display: 'flex', justifyContent: 'center', marginBottom: SPACE.md }}>
                <QRCodeDisplay token={scanUrl} size={isMobile ? 200 : 240} />
              </div>
              <WalletButtons registrationId={registration.id} googleSaveUrl={googleUrl} />
              {registration.checked_in_at && (
                <div style={{ marginTop: SPACE.md, display: 'inline-block', padding: '4px 14px', borderRadius: RADIUS.full, background: SUCCESS_BG10, color: SUCCESS, fontSize: 13, fontWeight: 600 }}>
                  Checked in {new Date(registration.checked_in_at).toLocaleString()}
                </div>
              )}
            </div>

            {/* WiFi Card */}
            {hackathon.wifi_ssid && (
              <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg }}>
                <h3 style={{ ...TYPO.h3, marginBottom: SPACE.sm }}>WiFi</h3>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: INPUT_BG, borderRadius: RADIUS.md, marginBottom: SPACE.sm }}>
                  <div>
                    <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 2 }}>Network</div>
                    <div style={{ fontSize: 16, fontWeight: 600 }}>{hackathon.wifi_ssid}</div>
                  </div>
                  <button onClick={() => copyToClipboard(hackathon.wifi_ssid!, 'ssid')}
                    style={{ background: 'none', border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.sm, color: copiedField === 'ssid' ? SUCCESS : TEXT_MUTED, cursor: 'pointer', padding: '4px 10px', fontSize: 12 }}>
                    {copiedField === 'ssid' ? 'Copied' : 'Copy'}
                  </button>
                </div>
                {hackathon.wifi_password && (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: INPUT_BG, borderRadius: RADIUS.md }}>
                    <div>
                      <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 2 }}>Password</div>
                      <div style={{ fontSize: 16, fontWeight: 600 }}>{hackathon.wifi_password}</div>
                    </div>
                    <button onClick={() => copyToClipboard(hackathon.wifi_password!, 'password')}
                      style={{ background: 'none', border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.sm, color: copiedField === 'password' ? SUCCESS : TEXT_MUTED, cursor: 'pointer', padding: '4px 10px', fontSize: 12 }}>
                      {copiedField === 'password' ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Schedule */}
            <ScheduleGrid events={hackathon.schedule || []} />

            {/* Scan History */}
            <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg }}>
              <h3 style={{ ...TYPO.h3, marginBottom: SPACE.sm }}>
                Scan History
                {registration.scan_count ? <Badge color={PRIMARY} bgColor={PRIMARY_BG20} style={{ marginLeft: SPACE.sm }}>{registration.scan_count} scan{registration.scan_count !== 1 ? 's' : ''}</Badge> : null}
              </h3>
              {(!registration.scans || registration.scans.length === 0) ? (
                <p style={{ color: TEXT_MUTED, fontSize: 14 }}>No scans yet.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
                  {registration.scans.map(scan => (
                    <div key={scan.id} style={{ display: 'flex', alignItems: 'center', gap: SPACE.md, padding: '8px 12px', background: INPUT_BG, borderRadius: RADIUS.md }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: scan.scan_type === 'checkin' ? SUCCESS : scan.scan_type === 'meal' ? WARNING : PRIMARY, textTransform: 'capitalize' }}>{scan.scan_type}</span>
                      <span style={{ fontSize: 12, color: TEXT_MUTED, marginLeft: 'auto' }}>{new Date(scan.scanned_at).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right column: Countdown Timer */}
          <div style={{ position: isMobile ? 'static' : 'sticky', top: SPACE.lg }}>
            <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg, textAlign: 'center' }}>
              <div style={{ fontSize: 13, color: TEXT_MUTED, marginBottom: SPACE.md, textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
                {countdown.isExpired ? 'Event Ended' : 'Time Remaining'}
              </div>
              {countdown.isExpired ? (
                <div style={{ fontSize: 24, fontWeight: 700, color: TEXT_SECONDARY }}>Finished</div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: SPACE.sm, marginBottom: SPACE.md }}>
                  {[{ label: 'Days', value: countdown.days }, { label: 'Hours', value: countdown.hours }, { label: 'Min', value: countdown.minutes }, { label: 'Sec', value: countdown.seconds }].map(unit => (
                    <div key={unit.label}>
                      <div style={{ fontFamily: "'Space Mono', monospace", fontSize: isMobile ? 28 : 36, fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: GOLD, lineHeight: 1.1 }}>
                        {String(unit.value).padStart(2, '0')}
                      </div>
                      <div style={{ fontSize: 10, color: TEXT_MUTED, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>{unit.label}</div>
                    </div>
                  ))}
                </div>
              )}
              <div style={{ height: 4, background: INPUT_BG, borderRadius: 2, overflow: 'hidden', marginTop: SPACE.sm }}>
                <div style={{ height: '100%', width: `${countdown.elapsedPercent}%`, background: `linear-gradient(90deg, ${PRIMARY}, ${CYAN})`, borderRadius: 2, transition: 'width 1s linear' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: SPACE.xs, fontSize: 10, color: TEXT_MUTED }}>
                <span>Start</span><span>{countdown.elapsedPercent}%</span><span>End</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ===================================================================
  // NOT REGISTERED — Application form
  // ===================================================================
  const startDate = new Date(hackathon.start_date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  const endDate = new Date(hackathon.end_date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      <div style={{ textAlign: 'center', marginBottom: SPACE.xl }}>
        <div style={{ fontSize: 13, color: CYAN, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: SPACE.sm }}>
          Mission Launch Window · April 29–30, 2026
        </div>
        <h1 style={{ ...TYPO.h1, marginBottom: SPACE.xs, fontSize: isMobile ? 28 : 36 }}>{hackathon.name}</h1>
        <p style={{ color: TEXT_SECONDARY, fontSize: 15 }}>{startDate} – {endDate}</p>
        {hackathon.description && <p style={{ color: TEXT_MUTED, fontSize: 14, maxWidth: 450, margin: '0 auto', marginTop: SPACE.xs }}>{hackathon.description}</p>}
      </div>

      {/* NOT REGISTERED */}
      {!isOrganizer && !registration && (
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.xl }}>
          <h2 style={{ ...TYPO.h2, marginBottom: SPACE.xs }}>Apply to participate</h2>
          <p style={{ color: TEXT_MUTED, fontSize: 14, marginBottom: SPACE.lg }}>Submit your application below.</p>
          <form onSubmit={handleRegister}>
            <div style={{ marginBottom: SPACE.md }}>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Display name (optional)</label>
              <input value={regName} onChange={e => setRegName(e.target.value)} placeholder="Your name or team name"
                style={{ width: '100%', padding: '12px 16px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 15, boxSizing: 'border-box', outline: 'none' }} />
            </div>
            {regError && <div style={{ background: ERROR_BG20, border: `1px solid ${ERROR}40`, borderRadius: RADIUS.md, padding: '10px 14px', marginBottom: SPACE.md, color: ERROR_TEXT, fontSize: 13 }}>{regError}</div>}
            <button type="submit" disabled={registering}
              style={{ width: '100%', padding: '14px 20px', background: PRIMARY, border: 'none', borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 16, fontWeight: 700, cursor: registering ? 'not-allowed' : 'pointer', opacity: registering ? 0.6 : 1 }}>
              {registering ? 'Submitting...' : 'Submit Application'}
            </button>
          </form>
        </div>
      )}

      {/* PENDING */}
      {registration && registration.status === 'pending' && (
        <div style={{ background: CARD_BG, border: `2px solid ${STATUS_PENDING}40`, borderRadius: RADIUS.lg, padding: SPACE.xl, textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: SPACE.md }}>&#9993;</div>
          <Badge color={STATUS_PENDING} style={{ marginBottom: SPACE.md }}>pending review</Badge>
          <h2 style={{ ...TYPO.h2, marginBottom: SPACE.sm }}>Application submitted</h2>
          <p style={{ color: TEXT_PRIMARY, fontWeight: 600, marginBottom: SPACE.xs, fontSize: 16 }}>{registration.team_name || user.name}</p>
          <p style={{ color: TEXT_MUTED, fontSize: 14, maxWidth: 360, margin: '0 auto' }}>Your application is being reviewed. You'll see your QR pass here once accepted.</p>
        </div>
      )}

      {/* REJECTED */}
      {registration && registration.status === 'rejected' && (
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.xl, textAlign: 'center' }}>
          <Badge color={STATUS_REJECTED} style={{ marginBottom: SPACE.md }}>not accepted</Badge>
          <p style={{ color: TEXT_SECONDARY, fontSize: 14 }}>Your application was not accepted for this event.</p>
        </div>
      )}

      {/* ORGANIZER TOOLS */}
      {isOrganizer && (
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg, padding: SPACE.lg, marginTop: registration ? SPACE.lg : 0 }}>
          <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>Organizer Tools</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACE.sm }}>
            <button onClick={() => navigate(`/hackathons/${hackathon.id}/registrations`)} style={{ padding: '8px 18px', background: PRIMARY, border: 'none', borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Manage Registrations</button>
            <button onClick={() => navigate(`/hackathons/${hackathon.id}/settings`)} style={{ padding: '8px 18px', background: 'none', border: `1px solid ${BORDER}`, borderRadius: RADIUS.md, color: TEXT_SECONDARY, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Event Settings</button>
            <button onClick={() => navigate(`/hackathons/${hackathon.id}/judging/setup`)} style={{ padding: '8px 18px', background: 'none', border: `1px solid ${BORDER}`, borderRadius: RADIUS.md, color: TEXT_SECONDARY, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Set Up Judging</button>
            <button onClick={() => navigate(`/hackathons/${hackathon.id}/judging/results`)} style={{ padding: '8px 18px', background: 'none', border: `1px solid ${BORDER}`, borderRadius: RADIUS.md, color: TEXT_SECONDARY, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>View Results</button>
            <button onClick={() => navigate(`/hackathons/${hackathon.id}/judging`)} style={{ padding: '8px 18px', background: 'none', border: `1px solid ${BORDER}`, borderRadius: RADIUS.md, color: TEXT_SECONDARY, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Score Projects</button>
            <button onClick={() => navigate('/check-in')} style={{ padding: '8px 18px', background: 'none', border: `1px solid ${BORDER}`, borderRadius: RADIUS.md, color: TEXT_SECONDARY, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Check-In Scanner</button>
          </div>
        </div>
      )}
    </div>
  );
}
