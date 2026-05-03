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

      {/* Additional Info */}
      <div style={{ marginBottom: 28 }}>
        <div style={SECTION_TITLE_STYLE}>Additional Info</div>

        {/* T-Shirt Size */}
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>T-Shirt Size</label>
          <select
            value={data.t_shirt_size || ''}
            onChange={update('t_shirt_size')}
            style={FIELD_STYLE}
          >
            {TSHIRT_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <div style={{ fontSize: 12, color: '#8a8fa3', marginTop: 4 }}>For event swag</div>
        </div>

        {/* Dietary Restrictions */}
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>Dietary Restrictions</label>
          <select
            value={data.dietary_restrictions || ''}
            onChange={update('dietary_restrictions')}
            style={FIELD_STYLE}
          >
            {DIETARY_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <div style={{ fontSize: 12, color: '#8a8fa3', marginTop: 4 }}>For catering purposes</div>
        </div>

        {/* Special Needs */}
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>Accessibility / Special Needs</label>
          <textarea
            value={data.special_needs || ''}
            onChange={update('special_needs')}
            placeholder="Any accessibility requirements we should know about?"
            rows={2}
            style={{ ...FIELD_STYLE, resize: 'vertical' }}
          />
          <div style={{ fontSize: 12, color: '#8a8fa3', marginTop: 4 }}>Optional - helps us accommodate everyone</div>
        </div>

        {/* School or Company */}
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>School or Company</label>
          <input
            value={data.school_company || ''}
            onChange={update('school_company')}
            placeholder="University or employer"
            style={FIELD_STYLE}
          />
        </div>

        {/* Graduation Year */}
        <div style={{ marginBottom: 14 }}>
          <label style={LABEL_STYLE}>Graduation Year (if student)</label>
          <select
            value={data.graduation_year?.toString() || ''}
            onChange={update('graduation_year')}
            style={FIELD_STYLE}
          >
            {GRADUATION_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Experience Level */}
        <div>
          <label style={LABEL_STYLE}>Experience Level</label>
          <select
            value={data.experience_level || ''}
            onChange={update('experience_level')}
            style={FIELD_STYLE}
          >
            {EXPERIENCE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
