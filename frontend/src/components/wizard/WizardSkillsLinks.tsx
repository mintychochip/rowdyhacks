import { PRIMARY, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, INPUT_BG, BORDER, RADIUS, TYPO } from '../../theme';
import TagInput from '../TagInput';

const LABEL_STYLE: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 500, color: TEXT_SECONDARY, marginBottom: 6, letterSpacing: '0.01em',
};

const FIELD_STYLE: React.CSSProperties = {
  width: '100%', padding: '10px 14px', background: INPUT_BG,
  border: `1px solid ${BORDER}`, borderRadius: RADIUS.md,
  color: TEXT_PRIMARY, fontSize: 14, fontFamily: TYPO.body.fontFamily,
  boxSizing: 'border-box', outline: 'none', transition: 'border-color 0.15s ease',
};

const SECTION_TITLE_STYLE: React.CSSProperties = {
  fontSize: 11, fontWeight: 600, color: TEXT_MUTED, textTransform: 'uppercase' as const,
  letterSpacing: '0.06em', marginBottom: 14, paddingBottom: 8,
  borderBottom: `1px solid ${BORDER}`,
};

const SELECT_STYLE: React.CSSProperties = {
  ...FIELD_STYLE,
  cursor: 'pointer',
  appearance: 'none' as const,
  backgroundImage: `url("data:image/svg+xml,%3Csvg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2371717a' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'right 12px center',
  paddingRight: 36,
};

const EXPERIENCE_OPTIONS = [
  { value: '', label: 'Select your experience level' },
  { value: 'beginner', label: 'Beginner — New to hackathons' },
  { value: 'intermediate', label: 'Intermediate — Some experience' },
  { value: 'advanced', label: 'Advanced — Hackathon veteran' },
];

import type { SkillsLinksData } from './types';

interface Props {
  data: SkillsLinksData;
  onChange: (data: SkillsLinksData) => void;
}

export default function WizardSkillsLinks({ data, onChange }: Props) {
  const update = (field: keyof SkillsLinksData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    onChange({ ...data, [field]: e.target.value });
  };

  return (
    <div>
      {/* Skills */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Skills</div>
        <label style={LABEL_STYLE}>Technologies you work with</label>
        <TagInput
          value={data.skills}
          onChange={(skills) => onChange({ ...data, skills })}
          placeholder="Type to search technologies..."
        />
      </div>

      {/* Professional Links */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Links <span style={{ fontWeight: 400, textTransform: 'none' as const, letterSpacing: 0, color: TEXT_MUTED, fontSize: 11 }}>(optional)</span></div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={LABEL_STYLE}>LinkedIn</label>
            <input value={data.linkedinUrl} onChange={update('linkedinUrl')}
              placeholder="https://linkedin.com/in/you" style={FIELD_STYLE} />
          </div>
          <div>
            <label style={LABEL_STYLE}>GitHub</label>
            <input value={data.githubUrl} onChange={update('githubUrl')}
              placeholder="https://github.com/you" style={FIELD_STYLE} />
          </div>
          <div>
            <label style={LABEL_STYLE}>Resume</label>
            <input value={data.resumeUrl} onChange={update('resumeUrl')}
              placeholder="https://drive.google.com/..." style={FIELD_STYLE} />
          </div>
        </div>
      </div>

      {/* Experience */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Experience</div>
        <label style={LABEL_STYLE}>Experience level</label>
        <select value={data.experienceLevel} onChange={update('experienceLevel')} style={SELECT_STYLE}>
          {EXPERIENCE_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value} style={{ background: INPUT_BG, color: TEXT_PRIMARY }}>{opt.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
