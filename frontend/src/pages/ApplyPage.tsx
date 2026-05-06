import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import WizardProgress from '../components/WizardProgress';
import WizardAboutYou from '../components/wizard/WizardAboutYou';
import WizardSkillsLinks from '../components/wizard/WizardSkillsLinks';
import WizardLogistics from '../components/wizard/WizardLogistics';
import WizardShortAnswers from '../components/wizard/WizardShortAnswers';
import type { AboutYouData, SkillsLinksData, LogisticsData, ShortAnswersData } from '../components/wizard/types';
import WizardReview from '../components/wizard/WizardReview';
import {
  PRIMARY, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  CARD_BG, BORDER, TYPO, RADIUS, SHADOW, TIMING,
} from '../theme';

const TOTAL_STEPS = 5;

export default function ApplyPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [hackathonId, setHackathonId] = useState('');
  const [hackathonName, setHackathonName] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);
  const [step, setStep] = useState(1);

  // Lifted form state
  const [aboutYou, setAboutYou] = useState<AboutYouData>({
    age: '', school: '', major: '', pronouns: '', phone: '',
  });
  const [skillsLinks, setSkillsLinks] = useState<SkillsLinksData>({
    skills: [], linkedinUrl: '', githubUrl: '', resumeUrl: '', experienceLevel: '',
  });
  const [logistics, setLogistics] = useState<LogisticsData>({
    tshirtSize: '', dietaryRestrictions: '', emergencyContactName: '', emergencyContactPhone: '',
  });
  const [shortAnswers, setShortAnswers] = useState<ShortAnswersData>({
    whatBuild: '', whyParticipate: '',
  });

  useEffect(() => {
    if (!user) { navigate('/auth'); return; }
    api.getHackathons().then(hacks => {
      if (hacks && hacks.length > 0) {
        setHackathonId(hacks[0].id);
        setHackathonName(hacks[0].name);
      }
    }).finally(() => setLoading(false));
  }, [user]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const reg = await api.registerForHackathon(hackathonId, {
        team_name: undefined,
        team_members: undefined,
        linkedin_url: skillsLinks.linkedinUrl.trim() || undefined,
        github_url: skillsLinks.githubUrl.trim() || undefined,
        resume_url: skillsLinks.resumeUrl.trim() || undefined,
        experience_level: skillsLinks.experienceLevel || undefined,
        t_shirt_size: logistics.tshirtSize || undefined,
        phone: aboutYou.phone.trim() || undefined,
        dietary_restrictions: logistics.dietaryRestrictions.trim() || undefined,
        what_build: shortAnswers.whatBuild.trim() || undefined,
        why_participate: shortAnswers.whyParticipate.trim() || undefined,
        age: aboutYou.age ? parseInt(aboutYou.age, 10) : undefined,
        school: aboutYou.school.trim() || undefined,
        major: aboutYou.major.trim() || undefined,
        pronouns: aboutYou.pronouns.trim() || undefined,
        skills: skillsLinks.skills.length ? skillsLinks.skills : undefined,
        emergency_contact_name: logistics.emergencyContactName.trim() || undefined,
        emergency_contact_phone: logistics.emergencyContactPhone.trim() || undefined,
      });
      setResult(reg);
    } catch (err: any) {
      setError(err.message);
    }
    setSubmitting(false);
  };

  const canGoBack = step > 1;
  const canGoNext = step < TOTAL_STEPS;

  if (!user) return null;
  if (loading) return <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>Loading...</div>;

  if (result) {
    return (
      <div style={{ maxWidth: 480, margin: '0 auto', padding: isMobile ? 20 : 80, textAlign: 'center' }}>
        <div style={{
          width: 56, height: 56, borderRadius: RADIUS.full,
          background: 'rgba(94, 106, 210, 0.12)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 24px',
        }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={PRIMARY} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <h1 style={{ ...TYPO.h2, marginBottom: 8, color: TEXT_PRIMARY }}>Application submitted</h1>
        <p style={{ color: TEXT_MUTED, fontSize: 15, marginBottom: 8, lineHeight: 1.6 }}>
          Your application to <strong style={{ color: TEXT_SECONDARY }}>{hackathonName}</strong> has been received.
        </p>
        <p style={{ color: TEXT_MUTED, fontSize: 14, marginBottom: 32, lineHeight: 1.5 }}>
          You'll be notified when the organizers make a decision.
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button onClick={() => navigate('/')}
            style={{ padding: '10px 22px', background: PRIMARY, border: 'none', borderRadius: RADIUS.md, color: '#fff', fontSize: 14, fontWeight: 500, cursor: 'pointer', transition: `background ${TIMING.fast}` }}>
            Go to Dashboard
          </button>
          <button onClick={() => navigate('/registrations')}
            style={{ padding: '10px 22px', background: 'none', border: `1px solid ${BORDER}`, borderRadius: RADIUS.md, color: TEXT_SECONDARY, fontSize: 14, fontWeight: 500, cursor: 'pointer', transition: `border-color ${TIMING.fast}` }}>
            View Application
          </button>
        </div>
      </div>
    );
  }

  const renderStep = () => {
    switch (step) {
      case 1:
        return <WizardAboutYou data={aboutYou} onChange={setAboutYou} userName={user.name} userEmail={user.email} />;
      case 2:
        return <WizardSkillsLinks data={skillsLinks} onChange={setSkillsLinks} />;
      case 3:
        return <WizardLogistics data={logistics} onChange={setLogistics} />;
      case 4:
        return <WizardShortAnswers data={shortAnswers} onChange={setShortAnswers} />;
      case 5:
        return (
          <WizardReview
            userName={user.name}
            userEmail={user.email}
            aboutYou={aboutYou}
            skillsLinks={skillsLinks}
            logistics={logistics}
            shortAnswers={shortAnswers}
            submitting={submitting}
            onSubmit={handleSubmit}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div style={{ maxWidth: 560, margin: '0 auto', padding: isMobile ? 20 : 60 }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: 36 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          fontSize: 11, color: TEXT_MUTED, fontWeight: 500,
          textTransform: 'uppercase', letterSpacing: '0.08em',
          marginBottom: 10, background: 'rgba(255,255,255,0.03)',
          padding: '4px 10px', borderRadius: RADIUS.full,
          border: `1px solid ${BORDER}`,
        }}>
          <span style={{ width: 4, height: 4, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
          Bakersfield · April 29–30, 2026
        </div>
        <h1 style={{ ...TYPO.h2, marginBottom: 6, letterSpacing: '-0.03em' }}>{hackathonName}</h1>
        <p style={{ color: TEXT_MUTED, fontSize: 14 }}>Submit your application to participate</p>
      </div>

      {/* Progress Bar */}
      <WizardProgress currentStep={step} />

      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`,
        borderRadius: RADIUS.xl, padding: isMobile ? 24 : 36,
        boxShadow: SHADOW.card,
      }}>
        {/* Step Content */}
        {renderStep()}

        {/* Error */}
        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: RADIUS.md, padding: '10px 14px', marginTop: 20,
            color: '#ef4444', fontSize: 13, lineHeight: 1.5,
          }}>{error}</div>
        )}

        {/* Navigation buttons (not shown on review step since it has its own submit) */}
        {step < TOTAL_STEPS && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 32, gap: 12 }}>
            {canGoBack ? (
              <button type="button" onClick={() => setStep(s => s - 1)}
                style={{
                  padding: '9px 20px', background: 'none', border: `1px solid ${BORDER}`,
                  borderRadius: RADIUS.md, color: TEXT_SECONDARY, fontSize: 14, fontWeight: 500,
                  cursor: 'pointer', transition: `all ${TIMING.fast}`,
                }}>
                Back
              </button>
            ) : <div />}
            {canGoNext && (
              <button type="button" onClick={() => setStep(s => s + 1)}
                style={{
                  padding: '9px 28px', background: PRIMARY, border: 'none',
                  borderRadius: RADIUS.md, color: '#fff', fontSize: 14, fontWeight: 500,
                  cursor: 'pointer', transition: `opacity ${TIMING.fast}`,
                }}>
                Continue
              </button>
            )}
          </div>
        )}

        {/* Back button for review step */}
        {step === TOTAL_STEPS && (
          <button type="button" onClick={() => setStep(4)}
            style={{
              marginTop: 16, padding: '9px 20px', background: 'none',
              border: `1px solid ${BORDER}`, borderRadius: RADIUS.md,
              color: TEXT_SECONDARY, fontSize: 14, fontWeight: 500, cursor: 'pointer',
            }}>
            Back
          </button>
        )}
      </div>
    </div>
  );
}
