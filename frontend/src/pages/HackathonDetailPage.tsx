import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import {
  PRIMARY, PRIMARY_BG20, SUCCESS, SUCCESS_BG10, WARNING, WARNING_BG10, ERROR, ERROR_TEXT, ERROR_BG20,
  TEXT_MUTED, TEXT_SECONDARY, TEXT_PRIMARY, TEXT_WHITE,
  INPUT_BG, INPUT_BORDER, GOLD,
  STATUS_ACCEPTED, STATUS_PENDING, STATUS_REJECTED, STATUS_CHECKED_IN,
  TYPO, SPACE, RADIUS, CARD_BG, BORDER, BORDER_LIGHT,
} from '../theme';
import { Card, Button, Badge } from '../components/Primitives';

interface HackathonDetail {
  id: string; name: string; start_date: string; end_date: string; description: string | null;
}

interface RegistrationFull {
  id: string; status: string; team_name: string | null; team_members: string[] | null;
  qr_token: string | null; registered_at: string; accepted_at: string | null; checked_in_at: string | null;
  scan_count?: number; scans?: Array<{ id: string; scan_type: string; scanned_at: string }>;
  linkedin_url?: string | null; github_url?: string | null; resume_url?: string | null;
  experience_level?: string | null; t_shirt_size?: string | null; phone?: string | null;
  dietary_restrictions?: string | null; what_build?: string | null; why_participate?: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  pending: STATUS_PENDING,
  accepted: STATUS_ACCEPTED,
  rejected: STATUS_REJECTED,
  checked_in: STATUS_CHECKED_IN,
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'Application Pending',
  accepted: 'Accepted!',
  rejected: 'Not Accepted',
  checked_in: 'Checked In',
};

export default function HackathonDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();

  const [hackathon, setHackathon] = useState<HackathonDetail | null>(null);
  const [registration, setRegistration] = useState<RegistrationFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Registration form state
  const [regName, setRegName] = useState('');
  const [regLinkedin, setRegLinkedin] = useState('');
  const [regGithub, setRegGithub] = useState('');
  const [regResume, setRegResume] = useState('');
  const [regExperience, setRegExperience] = useState('');
  const [regTshirt, setRegTshirt] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regDietary, setRegDietary] = useState('');
  const [regWhatBuild, setRegWhatBuild] = useState('');
  const [regWhyParticipate, setRegWhyParticipate] = useState('');
  const [registering, setRegistering] = useState(false);
  const [regError, setRegError] = useState('');

  useEffect(() => {
    loadData();
  }, [id, user]);

  const loadData = async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      const hk = await api.getHackathon(id);
      setHackathon(hk);

      if (user) {
        try {
          const regs = await api.getMyRegistrations();
          const mine = (regs.registrations || []).find(
            (r: any) => r.hackathon_id === id
          );
          if (mine) {
            setRegistration(mine);
          }
        } catch { /* not registered */ }
      }
    } catch (e: any) {
      setError(e.message || 'Failed to load hackathon');
    }
    setLoading(false);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setRegistering(true);
    setRegError('');
    try {
      const reg = await api.registerForHackathon(id, {
        team_name: regName.trim() || undefined,
        linkedin_url: regLinkedin.trim() || undefined,
        github_url: regGithub.trim() || undefined,
        resume_url: regResume.trim() || undefined,
        experience_level: regExperience || undefined,
        t_shirt_size: regTshirt || undefined,
        phone: regPhone.trim() || undefined,
        dietary_restrictions: regDietary.trim() || undefined,
        what_build: regWhatBuild.trim() || undefined,
        why_participate: regWhyParticipate.trim() || undefined,
      });
      setRegistration(reg);
      setRegName('');
      setRegLinkedin(''); setRegGithub(''); setRegResume('');
      setRegExperience(''); setRegTshirt(''); setRegPhone('');
      setRegDietary(''); setRegWhatBuild(''); setRegWhyParticipate('');
    } catch (err: any) {
      setRegError(err.message);
    }
    setRegistering(false);
  };

  if (loading) {
    return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Loading...</p>;
  }

  if (error || !hackathon) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl }}>
        <p style={{ color: ERROR_TEXT, marginBottom: SPACE.md }}>{error || 'Hackathon not found'}</p>
        <Button onClick={() => navigate('/hackathons')}>Back to Hackathons</Button>
      </div>
    );
  }

  const role = user?.role;
  const isOrganizer = role === 'organizer';
  const startDate = new Date(hackathon.start_date).toLocaleDateString();
  const endDate = new Date(hackathon.end_date).toLocaleDateString();

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      {/* Header */}
      <Link to="/hackathons" style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none' }}>
        &larr; All Hackathons
      </Link>
      <h1 style={{ ...TYPO.h1, marginTop: SPACE.sm, marginBottom: SPACE.xs }}>{hackathon.name}</h1>
      <p style={{ color: TEXT_MUTED, marginBottom: SPACE.lg, fontSize: 15 }}>
        {startDate} &ndash; {endDate}
        {hackathon.description && <><br />{hackathon.description}</>}
      </p>

      {/* ================================================================ */}
      {/* NOT REGISTERED — Inline Registration Form                         */}
      {/* ================================================================ */}
      {user && !registration && !isOrganizer && (
        <div style={{
          background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
          padding: SPACE.lg, marginBottom: SPACE.lg,
        }}>
          <h2 style={{ ...TYPO.h2, marginBottom: SPACE.xs }}>Register for this event</h2>
          <p style={{ color: TEXT_MUTED, fontSize: 14, marginBottom: SPACE.lg }}>Fill out your application below.</p>

          <form onSubmit={handleRegister}>
            <div style={{ marginBottom: SPACE.lg }}>
              <div style={{ fontSize: 11, color: GOLD, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, paddingBottom: 6, borderBottom: `1px solid ${BORDER}` }}>Team</div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Team name (optional)</label>
              <input value={regName} onChange={e => setRegName(e.target.value)} placeholder="Leave blank to apply solo"
                style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none' }} />
            </div>

            <div style={{ marginBottom: SPACE.lg }}>
              <div style={{ fontSize: 11, color: GOLD, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, paddingBottom: 6, borderBottom: `1px solid ${BORDER}` }}>Professional Links</div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>LinkedIn URL</label>
                <input value={regLinkedin} onChange={e => setRegLinkedin(e.target.value)} placeholder="https://linkedin.com/in/you"
                  style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none' }} />
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>GitHub URL</label>
                <input value={regGithub} onChange={e => setRegGithub(e.target.value)} placeholder="https://github.com/you"
                  style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Resume URL</label>
                <input value={regResume} onChange={e => setRegResume(e.target.value)} placeholder="https://drive.google.com/..."
                  style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none' }} />
              </div>
            </div>

            <div style={{ marginBottom: SPACE.lg }}>
              <div style={{ fontSize: 11, color: GOLD, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, paddingBottom: 6, borderBottom: `1px solid ${BORDER}` }}>Personal Info</div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Phone number</label>
                <input value={regPhone} onChange={e => setRegPhone(e.target.value)} placeholder="(555) 555-5555"
                  style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none' }} />
              </div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>T-shirt size</label>
                <select value={regTshirt} onChange={e => setRegTshirt(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none' }}>
                  <option value="">Select your size</option>
                  <option value="S">S</option>
                  <option value="M">M</option>
                  <option value="L">L</option>
                  <option value="XL">XL</option>
                  <option value="XXL">XXL</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Dietary restrictions</label>
                <textarea value={regDietary} onChange={e => setRegDietary(e.target.value)} placeholder="Any food allergies or dietary needs..."
                  rows={2} style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none', resize: 'vertical' }} />
              </div>
            </div>

            <div style={{ marginBottom: SPACE.lg }}>
              <div style={{ fontSize: 11, color: GOLD, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, paddingBottom: 6, borderBottom: `1px solid ${BORDER}` }}>Experience</div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Experience level</label>
              <select value={regExperience} onChange={e => setRegExperience(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none' }}>
                <option value="">Select your experience level</option>
                <option value="beginner">Beginner — New to hackathons</option>
                <option value="intermediate">Intermediate — Some experience</option>
                <option value="advanced">Advanced — Hackathon veteran</option>
              </select>
            </div>

            <div style={{ marginBottom: SPACE.lg }}>
              <div style={{ fontSize: 11, color: GOLD, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10, paddingBottom: 6, borderBottom: `1px solid ${BORDER}` }}>Short Answer</div>
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>What do you hope to build?</label>
                <textarea value={regWhatBuild} onChange={e => setRegWhatBuild(e.target.value)} placeholder="Describe your project idea or what you'd like to create..."
                  rows={3} style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none', resize: 'vertical' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Why do you want to participate?</label>
                <textarea value={regWhyParticipate} onChange={e => setRegWhyParticipate(e.target.value)} placeholder="Tell us what excites you about this hackathon..."
                  rows={3} style={{ width: '100%', padding: '10px 14px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box', outline: 'none', resize: 'vertical' }} />
              </div>
            </div>

            {regError && (
              <div style={{ background: ERROR_BG20, border: `1px solid ${ERROR}40`, borderRadius: RADIUS.md, padding: '10px 14px', marginBottom: SPACE.md, color: ERROR_TEXT, fontSize: 13 }}>
                {regError}
              </div>
            )}

            <button type="submit" disabled={registering}
              style={{
                width: '100%', padding: '14px 20px', background: PRIMARY, border: 'none',
                borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 16, fontWeight: 700,
                cursor: registering ? 'not-allowed' : 'pointer', opacity: registering ? 0.6 : 1,
              }}>
              {registering ? 'Submitting...' : 'Submit Application'}
            </button>
          </form>
        </div>
      )}

      {/* ================================================================ */}
      {/* PENDING — Application Status                                     */}
      {/* ================================================================ */}
      {registration && registration.status === 'pending' && (
        <div style={{
          background: CARD_BG, border: `2px solid ${STATUS_PENDING}40`, borderRadius: RADIUS.lg,
          padding: SPACE.xl, marginBottom: SPACE.lg, textAlign: 'center',
        }}>
          <div style={{ fontSize: 48, marginBottom: SPACE.md, opacity: 0.6 }}>&#9993;</div>
          <Badge color={STATUS_PENDING} style={{ marginBottom: SPACE.md }}>pending</Badge>
          <h2 style={{ ...TYPO.h2, marginBottom: SPACE.sm }}>Application Submitted</h2>
          <p style={{ color: TEXT_SECONDARY, marginBottom: SPACE.xs, fontSize: 14 }}>
            <strong>{registration.team_name || user?.name}</strong>
          </p>
          <p style={{ color: TEXT_MUTED, fontSize: 14 }}>
            Your application is being reviewed by the organizers.<br />
            You'll see your QR pass here once accepted.
          </p>
        </div>
      )}

      {/* ================================================================ */}
      {/* ACCEPTED / CHECKED_IN — Application Details                       */}
      {/* ================================================================ */}
      {registration && (registration.status === 'accepted' || registration.status === 'checked_in') && (
        <div style={{
          background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
          padding: SPACE.lg, marginBottom: SPACE.lg,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm, marginBottom: SPACE.lg }}>
            <Badge
              color={STATUS_COLORS[registration.status]}
              bgColor={STATUS_COLORS[registration.status] + '20'}
            >
              {STATUS_LABELS[registration.status]}
            </Badge>
            {registration.checked_in_at && (
              <span style={{ fontSize: 12, color: SUCCESS, fontWeight: 600 }}>
                Checked in {new Date(registration.checked_in_at).toLocaleString()}
              </span>
            )}
          </div>

          <h2 style={{ ...TYPO.h2, marginBottom: SPACE.lg }}>Your Application</h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm, marginBottom: SPACE.lg }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Name</span>
              <span style={{ fontWeight: 600, fontSize: 14 }}>{user?.name}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Email</span>
              <span style={{ fontSize: 14 }}>{user?.email}</span>
            </div>
            {registration.team_name && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Team Name</span>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{registration.team_name}</span>
              </div>
            )}
            {registration.team_members && registration.team_members.length > 0 && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Team Members</span>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{(registration.team_members as string[]).join(', ')}</span>
              </div>
            )}
            {registration.phone && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Phone</span>
                <span style={{ fontSize: 14 }}>{registration.phone}</span>
              </div>
            )}
            {registration.t_shirt_size && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>T-Shirt Size</span>
                <span style={{ fontSize: 14 }}>{registration.t_shirt_size}</span>
              </div>
            )}
            {registration.dietary_restrictions && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Dietary Restrictions</span>
                <span style={{ fontSize: 14 }}>{registration.dietary_restrictions}</span>
              </div>
            )}
            {registration.experience_level && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Experience</span>
                <span style={{ fontSize: 14 }}>{registration.experience_level}</span>
              </div>
            )}
            {registration.linkedin_url && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>LinkedIn</span>
                <a href={registration.linkedin_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 14, color: PRIMARY }}>View Profile</a>
              </div>
            )}
            {registration.github_url && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>GitHub</span>
                <a href={registration.github_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 14, color: PRIMARY }}>View Profile</a>
              </div>
            )}
            {registration.resume_url && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Resume</span>
                <a href={registration.resume_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 14, color: PRIMARY }}>View Resume</a>
              </div>
            )}
            {registration.what_build && (
              <div style={{ flexDirection: 'column', gap: 4 }}>
                <span style={{ color: TEXT_MUTED, fontSize: 13 }}>What they hope to build</span>
                <p style={{ margin: '4px 0 0', fontSize: 14, lineHeight: 1.5 }}>{registration.what_build}</p>
              </div>
            )}
            {registration.why_participate && (
              <div style={{ flexDirection: 'column', gap: 4 }}>
                <span style={{ color: TEXT_MUTED, fontSize: 13 }}>Why they want to participate</span>
                <p style={{ margin: '4px 0 0', fontSize: 14, lineHeight: 1.5 }}>{registration.why_participate}</p>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Applied</span>
              <span style={{ fontSize: 14 }}>{new Date(registration.registered_at).toLocaleDateString()}</span>
            </div>
            {registration.accepted_at && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: TEXT_MUTED, fontSize: 14 }}>Accepted</span>
                <span style={{ fontSize: 14 }}>{new Date(registration.accepted_at).toLocaleDateString()}</span>
              </div>
            )}
          </div>

          {/* Live Dashboard link */}
          <a
            href={`/hackathons/${id}/hacker-dashboard`}
            onClick={(e) => { e.preventDefault(); navigate(`/hackathons/${id}/hacker-dashboard`); }}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '12px 28px', background: PRIMARY, color: TEXT_WHITE,
              borderRadius: RADIUS.md, textDecoration: 'none', fontSize: 15, fontWeight: 600,
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
              <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
            </svg>
            Open Live Dashboard
          </a>
        </div>
      )}

      {/* ================================================================ */}
      {/* REJECTED                                                        */}
      {/* ================================================================ */}
      {registration && registration.status === 'rejected' && (
        <div style={{
          background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
          padding: SPACE.xl, marginBottom: SPACE.lg, textAlign: 'center',
        }}>
          <Badge color={STATUS_REJECTED} style={{ marginBottom: SPACE.md }}>rejected</Badge>
          <p style={{ color: TEXT_SECONDARY, fontSize: 14 }}>
            Your application was not accepted for this event.
          </p>
        </div>
      )}

      {/* ================================================================ */}
      {/* ORGANIZER TOOLS                                                  */}
      {/* ================================================================ */}
      {isOrganizer && (
        <div style={{
          background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
          padding: SPACE.lg, marginBottom: SPACE.lg,
        }}>
          <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>Organizer Tools</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACE.sm }}>
            <Button onClick={() => navigate(`/hackathons/${id}/registrations`)}>
              Manage Registrations
            </Button>
            <Button onClick={() => navigate(`/hackathons/${id}/settings`)} variant="secondary">
              Event Settings
            </Button>
            <Button onClick={() => navigate(`/hackathons/${id}/judging/setup`)} variant="secondary">
              Set Up Judging
            </Button>
            <Button onClick={() => navigate(`/hackathons/${id}/judging/results`)} variant="secondary">
              View Results
            </Button>
            <Button onClick={() => navigate(`/hackathons/${id}/judging`)} variant="secondary">
              Score Projects
            </Button>
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* EXPLORE (everyone)                                               */}
      {/* ================================================================ */}
      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: SPACE.lg, marginBottom: SPACE.lg,
      }}>
        <h3 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>Explore</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACE.sm }}>
          <Button onClick={() => navigate(`/hackathons/${id}/projects`)} variant="secondary">
            Browse Projects
          </Button>
          <Button onClick={() => navigate(`/hackathons/${id}/leaderboard`)} variant="secondary">
            View Leaderboard
          </Button>
          {(role === 'judge' || isOrganizer) && (
            <Button onClick={() => navigate(`/hackathons/${id}/judging`)} variant="secondary">
              {isOrganizer ? 'Score Projects' : 'Judge Projects'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
