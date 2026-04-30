import { PRIMARY, GOLD, TEXT_MUTED, BORDER, RADIUS } from '../../theme';

const LABEL_STYLE: React.CSSProperties = {
  display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 6,
};

const FIELD_STYLE: React.CSSProperties = {
  width: '100%', padding: '12px 16px', background: '#0a0f1e',
  border: `2px solid ${PRIMARY}40`, borderRadius: RADIUS.md,
  color: '#e8e8f0', fontSize: 15, boxSizing: 'border-box', outline: 'none',
  resize: 'vertical' as const,
};

const SECTION_TITLE_STYLE: React.CSSProperties = {
  fontSize: 13, color: GOLD, fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.08em', marginBottom: 14, paddingBottom: 8,
  borderBottom: `1px solid ${BORDER}`,
};

import type { ShortAnswersData } from './types';

interface Props {
  data: ShortAnswersData;
  onChange: (data: ShortAnswersData) => void;
}

export default function WizardShortAnswers({ data, onChange }: Props) {
  const update = (field: keyof ShortAnswersData) => (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ ...data, [field]: e.target.value });
  };

  return (
    <div>
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Short Answer</div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>What do you hope to build?</label>
          <textarea value={data.whatBuild} onChange={update('whatBuild')}
            placeholder="Describe your project idea or what you'd like to create..."
            rows={4} style={FIELD_STYLE} />
        </div>
        <div>
          <label style={LABEL_STYLE}>Why do you want to participate?</label>
          <textarea value={data.whyParticipate} onChange={update('whyParticipate')}
            placeholder="Tell us what excites you about this hackathon..."
            rows={4} style={FIELD_STYLE} />
        </div>
      </div>
    </div>
  );
}
