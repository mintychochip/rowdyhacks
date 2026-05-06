import type { AboutYouData, SkillsLinksData, LogisticsData, ShortAnswersData } from './types';
import {
  PRIMARY, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  BORDER, RADIUS, TYPO, SHADOW, TIMING,
} from '../../theme';

interface Props {
  userName: string;
  userEmail: string;
  aboutYou: AboutYouData;
  skillsLinks: SkillsLinksData;
  logistics: LogisticsData;
  shortAnswers: ShortAnswersData;
  submitting: boolean;
  onSubmit: () => void;
}

const SECTION_TITLE_STYLE: React.CSSProperties = {
  fontSize: 11, fontWeight: 600, color: TEXT_MUTED, textTransform: 'uppercase' as const,
  letterSpacing: '0.06em', marginBottom: 10, paddingBottom: 6,
  borderBottom: `1px solid ${BORDER}`,
};

function Row({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      padding: '6px 0', fontSize: 13, borderBottom: '1px solid rgba(255,255,255,0.03)',
    }}>
      <span style={{ color: TEXT_MUTED, fontSize: 12 }}>{label}</span>
      <span style={{ color: TEXT_PRIMARY, fontSize: 13, fontWeight: 500, textAlign: 'right', maxWidth: '60%', wordBreak: 'break-word' }}>{value}</span>
    </div>
  );
}

export default function WizardReview({
  userName, userEmail, aboutYou, skillsLinks, logistics, shortAnswers, submitting, onSubmit,
}: Props) {
  return (
    <div>
      {/* Account */}
      <div style={{ marginBottom: 20 }}>
        <div style={SECTION_TITLE_STYLE}>Account</div>
        <Row label="Name" value={userName} />
        <Row label="Email" value={userEmail} />
      </div>

      {/* About You */}
      <div style={{ marginBottom: 20 }}>
        <div style={SECTION_TITLE_STYLE}>About You</div>
        {aboutYou.age && <Row label="Age" value={aboutYou.age} />}
        {aboutYou.school && <Row label="School" value={aboutYou.school} />}
        {aboutYou.major && <Row label="Major" value={aboutYou.major} />}
        {aboutYou.pronouns && <Row label="Pronouns" value={aboutYou.pronouns} />}
        {aboutYou.phone && <Row label="Phone" value={aboutYou.phone} />}
      </div>

      {/* Skills & Links */}
      <div style={{ marginBottom: 20 }}>
        <div style={SECTION_TITLE_STYLE}>Skills & Links</div>
        {skillsLinks.skills.length > 0 && <Row label="Skills" value={skillsLinks.skills.join(', ')} />}
        {skillsLinks.linkedinUrl && <Row label="LinkedIn" value={skillsLinks.linkedinUrl} />}
        {skillsLinks.githubUrl && <Row label="GitHub" value={skillsLinks.githubUrl} />}
        {skillsLinks.resumeUrl && <Row label="Resume" value={skillsLinks.resumeUrl} />}
        {skillsLinks.experienceLevel && <Row label="Experience" value={skillsLinks.experienceLevel} />}
      </div>

      {/* Logistics */}
      <div style={{ marginBottom: 20 }}>
        <div style={SECTION_TITLE_STYLE}>Logistics</div>
        {logistics.tshirtSize && <Row label="T-shirt" value={logistics.tshirtSize} />}
        {logistics.dietaryRestrictions && <Row label="Dietary" value={logistics.dietaryRestrictions} />}
        {logistics.emergencyContactName && (
          <Row label="Emergency" value={[logistics.emergencyContactName, logistics.emergencyContactPhone].filter(Boolean).join(' — ')} />
        )}
        {/* New fields */}
        {logistics.t_shirt_size && <Row label="T-Shirt" value={logistics.t_shirt_size} />}
        {logistics.dietary_restrictions && <Row label="Dietary" value={logistics.dietary_restrictions} />}
        {logistics.special_needs && <Row label="Special Needs" value={logistics.special_needs} />}
        {logistics.school_company && <Row label="School/Company" value={logistics.school_company} />}
        {logistics.graduation_year && <Row label="Grad Year" value={logistics.graduation_year?.toString()} />}
        {logistics.experience_level && <Row label="Experience" value={logistics.experience_level} />}
      </div>

      {/* Short Answers */}
      <div style={{ marginBottom: 24 }}>
        <div style={SECTION_TITLE_STYLE}>Short Answers</div>
        {shortAnswers.whatBuild && <Row label="What to build" value={shortAnswers.whatBuild} />}
        {shortAnswers.whyParticipate && <Row label="Why participate" value={shortAnswers.whyParticipate} />}
      </div>

      {/* Code of Conduct */}
      <div style={{
        padding: '14px 16px', background: 'rgba(94, 106, 210, 0.06)',
        border: '1px solid rgba(94, 106, 210, 0.15)',
        borderRadius: RADIUS.md, marginBottom: 20,
      }}>
        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
          <input type="checkbox" required
            style={{ marginTop: 2, accentColor: PRIMARY }} />
          <span style={{ fontSize: 13, color: TEXT_SECONDARY, lineHeight: 1.5 }}>
            I have read and agree to the <strong style={{ color: TEXT_PRIMARY }}>MLH Code of Conduct</strong> and the event rules.
          </span>
        </label>
      </div>

      <button onClick={onSubmit} disabled={submitting}
        style={{
          width: '100%', padding: '12px 20px', background: PRIMARY, border: 'none',
          borderRadius: RADIUS.md, color: '#fff', fontSize: 14, fontWeight: 600,
          cursor: submitting ? 'not-allowed' : 'pointer', opacity: submitting ? 0.5 : 1,
          transition: `opacity ${TIMING.fast}`,
        }}>
        {submitting ? 'Submitting...' : 'Submit Application'}
      </button>
    </div>
  );
}
