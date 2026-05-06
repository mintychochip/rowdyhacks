import { TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, INPUT_BG, BORDER, RADIUS, TYPO } from '../../theme';

const LABEL_STYLE: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 500, color: TEXT_SECONDARY, marginBottom: 6, letterSpacing: '0.01em',
};

const FIELD_STYLE: React.CSSProperties = {
  width: '100%', padding: '10px 14px', background: INPUT_BG,
  border: `1px solid ${BORDER}`, borderRadius: RADIUS.md,
  color: TEXT_PRIMARY, fontSize: 14, fontFamily: TYPO.body.fontFamily,
  boxSizing: 'border-box', outline: 'none', transition: 'border-color 0.15s ease',
  resize: 'vertical' as const,
};

const SECTION_TITLE_STYLE: React.CSSProperties = {
  fontSize: 11, fontWeight: 600, color: TEXT_MUTED, textTransform: 'uppercase' as const,
  letterSpacing: '0.06em', marginBottom: 14, paddingBottom: 8,
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div>
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
    </div>
  );
}
