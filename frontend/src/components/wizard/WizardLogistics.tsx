import { PRIMARY, GOLD, TEXT_MUTED, BORDER, RADIUS } from '../../theme';

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

const TSHIRT_OPTIONS = [
  { value: '', label: 'Select your size' },
  { value: 'S', label: 'S' },
  { value: 'M', label: 'M' },
  { value: 'L', label: 'L' },
  { value: 'XL', label: 'XL' },
  { value: 'XXL', label: 'XXL' },
];

export interface LogisticsData {
  tshirtSize: string;
  dietaryRestrictions: string;
  emergencyContactName: string;
  emergencyContactPhone: string;
}

interface Props {
  data: LogisticsData;
  onChange: (data: LogisticsData) => void;
}

export default function WizardLogistics({ data, onChange }: Props) {
  const update = (field: keyof LogisticsData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    onChange({ ...data, [field]: e.target.value });
  };

  return (
    <div>
      {/* Personal Info */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Personal Info</div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>T-shirt size</label>
          <select value={data.tshirtSize} onChange={update('tshirtSize')} style={FIELD_STYLE}>
            {TSHIRT_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={LABEL_STYLE}>Dietary restrictions</label>
          <textarea value={data.dietaryRestrictions} onChange={update('dietaryRestrictions')}
            placeholder="Any food allergies or dietary needs..."
            rows={2} style={{ ...FIELD_STYLE, resize: 'vertical' }} />
        </div>
      </div>

      {/* Emergency Contact */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Emergency Contact</div>
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>Contact name</label>
          <input value={data.emergencyContactName} onChange={update('emergencyContactName')}
            placeholder="Emergency contact full name" style={FIELD_STYLE} />
        </div>
        <div>
          <label style={LABEL_STYLE}>Contact phone</label>
          <input value={data.emergencyContactPhone} onChange={update('emergencyContactPhone')}
            placeholder="(555) 555-5555" style={FIELD_STYLE} />
        </div>
      </div>
    </div>
  );
}
