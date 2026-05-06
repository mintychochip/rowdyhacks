import { TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, INPUT_BG, BORDER, RADIUS, TYPO } from '../../theme';

const LABEL_STYLE: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 500, color: TEXT_SECONDARY, marginBottom: 6, letterSpacing: '0.01em',
};

const FIELD_STYLE: React.CSSProperties = {
  width: '100%', padding: '10px 14px', background: INPUT_BG,
  border: `1px solid ${BORDER}`, borderRadius: RADIUS.md,
  color: TEXT_PRIMARY, fontSize: 14, fontFamily: TYPO.body.fontFamily,
  boxSizing: 'border-box', outline: 'none', transition: 'border-color 0.15s ease',
};

const TEXTAREA_STYLE: React.CSSProperties = {
  ...FIELD_STYLE, resize: 'vertical' as const,
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

const SECTION_TITLE_STYLE: React.CSSProperties = {
  fontSize: 11, fontWeight: 600, color: TEXT_MUTED, textTransform: 'uppercase' as const,
  letterSpacing: '0.06em', marginBottom: 14, paddingBottom: 8,
  borderBottom: `1px solid ${BORDER}`,
};

const TSHIRT_OPTIONS = [
  { value: '', label: 'Select your size' },
  { value: 'XS', label: 'XS' },
  { value: 'S', label: 'S' },
  { value: 'M', label: 'M' },
  { value: 'L', label: 'L' },
  { value: 'XL', label: 'XL' },
  { value: 'XXL', label: 'XXL' },
];

const DIETARY_OPTIONS = [
  { value: '', label: 'None' },
  { value: 'vegetarian', label: 'Vegetarian' },
  { value: 'vegan', label: 'Vegan' },
  { value: 'gluten-free', label: 'Gluten-free' },
  { value: 'halal', label: 'Halal' },
  { value: 'kosher', label: 'Kosher' },
  { value: 'nut-allergy', label: 'Nut Allergy' },
];

const GRADUATION_OPTIONS = [
  { value: '', label: 'N/A' },
  { value: '2026', label: '2026' },
  { value: '2027', label: '2027' },
  { value: '2028', label: '2028' },
  { value: '2029', label: '2029' },
];

const EXPERIENCE_OPTIONS = [
  { value: '', label: 'Prefer not to say' },
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
];

import type { LogisticsData } from './types';

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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={LABEL_STYLE}>T-shirt size</label>
            <select value={data.tshirtSize} onChange={update('tshirtSize')} style={SELECT_STYLE}>
              {TSHIRT_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value} style={{ background: INPUT_BG, color: TEXT_PRIMARY }}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={LABEL_STYLE}>Dietary restrictions</label>
            <textarea value={data.dietaryRestrictions} onChange={update('dietaryRestrictions')}
              placeholder="Any food allergies or dietary needs..."
              rows={2} style={TEXTAREA_STYLE} />
          </div>
        </div>
      </div>

      {/* Emergency Contact */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Emergency Contact</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
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

      {/* Additional Info */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Additional Info</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={LABEL_STYLE}>T-Shirt Size</label>
            <select value={data.t_shirt_size || ''} onChange={update('t_shirt_size')} style={SELECT_STYLE}>
              {TSHIRT_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value} style={{ background: INPUT_BG, color: TEXT_PRIMARY }}>{opt.label}</option>
              ))}
            </select>
            <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 4 }}>For event swag</div>
          </div>
          <div>
            <label style={LABEL_STYLE}>Dietary Restrictions</label>
            <select value={data.dietary_restrictions || ''} onChange={update('dietary_restrictions')} style={SELECT_STYLE}>
              {DIETARY_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value} style={{ background: INPUT_BG, color: TEXT_PRIMARY }}>{opt.label}</option>
              ))}
            </select>
            <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 4 }}>For catering purposes</div>
          </div>
          <div>
            <label style={LABEL_STYLE}>Accessibility / Special Needs</label>
            <textarea value={data.special_needs || ''} onChange={update('special_needs')}
              placeholder="Any accessibility requirements we should know about?"
              rows={2} style={TEXTAREA_STYLE} />
            <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 4 }}>Helps us accommodate everyone</div>
          </div>
          <div>
            <label style={LABEL_STYLE}>School or Company</label>
            <input value={data.school_company || ''} onChange={update('school_company')}
              placeholder="University or employer" style={FIELD_STYLE} />
          </div>
          <div>
            <label style={LABEL_STYLE}>Graduation Year</label>
            <select value={data.graduation_year?.toString() || ''} onChange={update('graduation_year')} style={SELECT_STYLE}>
              {GRADUATION_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value} style={{ background: INPUT_BG, color: TEXT_PRIMARY }}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={LABEL_STYLE}>Experience Level</label>
            <select value={data.experience_level || ''} onChange={update('experience_level')} style={SELECT_STYLE}>
              {EXPERIENCE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value} style={{ background: INPUT_BG, color: TEXT_PRIMARY }}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
