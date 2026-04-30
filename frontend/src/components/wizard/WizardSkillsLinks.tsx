import { PRIMARY, GOLD, TEXT_MUTED, BORDER, RADIUS } from '../../theme';
import TagInput from '../TagInput';

const LABEL_STYLE: React.CSSProperties = {
  display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 6,
};

const FIELD_STYLE: React.CSSProperties = {
  width: '100%', padding: '12px 16px', background: '#0a0f1e',
  border: `2px solid ${PRIMARY}40`, borderRadius: RADIUS.md,
  color: '#e8e8f0', fontSize: 15, boxSizing: 'border-box', outline: 'none',
};

const SECTION_TITLE_STYLE: React.CSSProperties = {
  fontSize: 13, color: GOLD, fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.08em', marginBottom: 14, paddingBottom: 8,
  borderBottom: `1px solid ${BORDER}`,
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
        <div style={SECTION_TITLE_STYLE}>Tech Stack</div>
        <label style={LABEL_STYLE}>Skills & technologies</label>
        <TagInput
          value={data.skills}
          onChange={(skills) => onChange({ ...data, skills })}
          placeholder="Type to search technologies..."
        />
      </div>

      {/* Professional Links */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Professional Links <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0, color: TEXT_MUTED, fontSize: 11 }}>(all optional)</span></div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>LinkedIn URL</label>
          <input value={data.linkedinUrl} onChange={update('linkedinUrl')}
            placeholder="https://linkedin.com/in/you" style={FIELD_STYLE} />
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>GitHub URL</label>
          <input value={data.githubUrl} onChange={update('githubUrl')}
            placeholder="https://github.com/you" style={FIELD_STYLE} />
        </div>
        <div>
          <label style={LABEL_STYLE}>Resume URL</label>
          <input value={data.resumeUrl} onChange={update('resumeUrl')}
            placeholder="https://drive.google.com/..." style={FIELD_STYLE} />
        </div>
      </div>

      {/* Experience */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Experience</div>
        <label style={LABEL_STYLE}>Experience level</label>
        <select value={data.experienceLevel} onChange={update('experienceLevel')} style={FIELD_STYLE}>
          {EXPERIENCE_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
