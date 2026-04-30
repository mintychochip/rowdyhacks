import { PRIMARY, GOLD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, INPUT_BG, INPUT_BORDER, BORDER, RADIUS } from '../../theme';

const FIELD_STYLE: React.CSSProperties = {
  width: '100%', padding: '12px 16px', background: '#0a0f1e',
  border: `2px solid ${PRIMARY}40`, borderRadius: RADIUS.md,
  color: TEXT_PRIMARY, fontSize: 15, boxSizing: 'border-box', outline: 'none',
};

const LABEL_STYLE: React.CSSProperties = {
  display: 'block', fontSize: 13, color: TEXT_MUTED, marginBottom: 6,
};

const SECTION_TITLE_STYLE: React.CSSProperties = {
  fontSize: 13, color: GOLD, fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.08em', marginBottom: 14, paddingBottom: 8,
  borderBottom: `1px solid ${BORDER}`,
};

export interface AboutYouData {
  age: string;
  school: string;
  major: string;
  pronouns: string;
  phone: string;
}

interface Props {
  data: AboutYouData;
  onChange: (data: AboutYouData) => void;
  userName: string;
  userEmail: string;
}

export default function WizardAboutYou({ data, onChange, userName, userEmail }: Props) {
  const update = (field: keyof AboutYouData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...data, [field]: e.target.value });
  };

  return (
    <div>
      {/* Applicant Info (read-only) */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Account</div>
        <div style={{ padding: '12px 16px', background: INPUT_BG, borderRadius: RADIUS.md, border: `1px solid ${BORDER}` }}>
          <div style={{ fontSize: 11, color: TEXT_MUTED, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 2 }}>Name</div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{userName}</div>
          <div style={{ fontSize: 13, color: TEXT_MUTED, marginTop: 4 }}>{userEmail}</div>
        </div>
      </div>

      {/* About You */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>About You</div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>Age</label>
          <input type="number" value={data.age} onChange={update('age')}
            placeholder="Your age" style={FIELD_STYLE} min={0} max={150} />
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>School</label>
          <input value={data.school} onChange={update('school')}
            placeholder="Your school or university" style={FIELD_STYLE} />
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>Major</label>
          <input value={data.major} onChange={update('major')}
            placeholder="Your major or field of study" style={FIELD_STYLE} />
        </div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>Pronouns</label>
          <input value={data.pronouns} onChange={update('pronouns')}
            placeholder="e.g. they/them, she/her, he/him" style={FIELD_STYLE} />
        </div>
        <div>
          <label style={LABEL_STYLE}>Phone number</label>
          <input value={data.phone} onChange={update('phone')}
            placeholder="(555) 555-5555" style={FIELD_STYLE} />
        </div>
      </div>
    </div>
  );
}
