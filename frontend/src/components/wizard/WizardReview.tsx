import type { AboutYouData, SkillsLinksData, LogisticsData, ShortAnswersData } from './types';
import { GOLD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, CARD_BG, BORDER, RADIUS, SUCCESS } from '../../theme';

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
  fontSize: 13, color: GOLD, fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.08em', marginBottom: 10, paddingBottom: 6,
  borderBottom: `1px solid ${BORDER}`,
};

function Row({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div style={{ marginBottom: 6, fontSize: 14 }}>
      <span style={{ color: TEXT_MUTED }}>{label}: </span>
      <span style={{ color: TEXT_PRIMARY }}>{value}</span>
    </div>
  );
}

export default function WizardReview({
  userName, userEmail, aboutYou, skillsLinks, logistics, shortAnswers, submitting, onSubmit,
}: Props) {
  return (
    <div>
      {/* Account */}
      <div style={{ marginBottom: 24 }}>
        <div style={SECTION_TITLE_STYLE}>Account</div>
        <Row label="Name" value={userName} />
        <Row label="Email" value={userEmail} />
      </div>

      {/* About You */}
      <div style={{ marginBottom: 24 }}>
        <div style={SECTION_TITLE_STYLE}>About You</div>
        <Row label="Age" value={aboutYou.age || undefined} />
        <Row label="School" value={aboutYou.school || undefined} />
        <Row label="Major" value={aboutYou.major || undefined} />
        <Row label="Pronouns" value={aboutYou.pronouns || undefined} />
        <Row label="Phone" value={aboutYou.phone || undefined} />
      </div>

      {/* Skills & Links */}
      <div style={{ marginBottom: 24 }}>
        <div style={SECTION_TITLE_STYLE}>Skills & Links</div>
        <Row label="Skills" value={skillsLinks.skills.length ? skillsLinks.skills.join(', ') : undefined} />
        <Row label="LinkedIn" value={skillsLinks.linkedinUrl || undefined} />
        <Row label="GitHub" value={skillsLinks.githubUrl || undefined} />
        <Row label="Resume" value={skillsLinks.resumeUrl || undefined} />
        <Row label="Experience" value={skillsLinks.experienceLevel || undefined} />
      </div>

      {/* Logistics */}
      <div style={{ marginBottom: 24 }}>
        <div style={SECTION_TITLE_STYLE}>Logistics</div>
        <Row label="T-shirt size" value={logistics.tshirtSize || undefined} />
        <Row label="Dietary" value={logistics.dietaryRestrictions || undefined} />
        <Row label="Emergency contact" value={[logistics.emergencyContactName, logistics.emergencyContactPhone].filter(Boolean).join(' — ') || undefined} />
      </div>

      {/* Short Answers */}
      <div style={{ marginBottom: 24 }}>
        <div style={SECTION_TITLE_STYLE}>Short Answers</div>
        <Row label="What to build" value={shortAnswers.whatBuild || undefined} />
        <Row label="Why participate" value={shortAnswers.whyParticipate || undefined} />
      </div>

      {/* Code of Conduct */}
      <div style={{
        padding: '14px 16px', background: `${GOLD}10`, border: `1px solid ${GOLD}30`,
        borderRadius: RADIUS.md, marginBottom: 20,
      }}>
        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
          <input type="checkbox" required style={{ marginTop: 2, accentColor: GOLD }} />
          <span style={{ fontSize: 13, color: TEXT_SECONDARY, lineHeight: 1.5 }}>
            I have read and agree to the <strong style={{ color: TEXT_PRIMARY }}>MLH Code of Conduct</strong> and the event rules. I understand that violating these policies may result in removal from the event.
          </span>
        </label>
      </div>

      <button onClick={onSubmit} disabled={submitting}
        style={{
          width: '100%', padding: '14px 20px', background: SUCCESS, border: 'none',
          borderRadius: RADIUS.md, color: '#000', fontSize: 16, fontWeight: 700,
          cursor: submitting ? 'not-allowed' : 'pointer', opacity: submitting ? 0.6 : 1,
        }}>
        {submitting ? 'Submitting...' : 'Submit Application'}
      </button>
    </div>
  );
}
