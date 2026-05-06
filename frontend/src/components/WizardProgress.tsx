import { PRIMARY, TEXT_PRIMARY, TEXT_MUTED, BORDER, RADIUS } from '../theme';

const STEPS = [
  { label: 'About You', step: 1 },
  { label: 'Skills & Links', step: 2 },
  { label: 'Logistics', step: 3 },
  { label: 'Short Answers', step: 4 },
  { label: 'Review', step: 5 },
];

interface WizardProgressProps {
  currentStep: number;
}

export default function WizardProgress({ currentStep }: WizardProgressProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', gap: 0, marginBottom: 36 }}>
      {STEPS.map((s, i) => {
        const isActive = s.step === currentStep;
        const isComplete = s.step < currentStep;
        const isLast = i === STEPS.length - 1;

        return (
          <div key={s.step} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
              {/* Step dot */}
              <div style={{
                width: isActive ? 36 : 28, height: isActive ? 36 : 28,
                borderRadius: RADIUS.full,
                background: isComplete ? PRIMARY : 'transparent',
                border: isComplete
                  ? `1.5px solid ${PRIMARY}`
                  : isActive
                    ? `1.5px solid ${PRIMARY}`
                    : `1.5px solid ${BORDER}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: isActive ? 12 : 11, fontWeight: 600,
                color: isComplete ? '#fff' : isActive ? PRIMARY : TEXT_MUTED,
                transition: 'all 0.2s ease',
                boxShadow: isActive ? `0 0 0 3px rgba(94, 106, 210, 0.12)` : 'none',
              }}>
                {isComplete ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : s.step}
              </div>
              {/* Label */}
              <span style={{
                fontSize: 10, fontWeight: isActive ? 600 : 500,
                color: isActive ? TEXT_PRIMARY : TEXT_MUTED,
                textTransform: 'uppercase', letterSpacing: '0.06em',
                whiteSpace: 'nowrap',
              }}>
                {s.label}
              </span>
            </div>
            {/* Connector line */}
            {!isLast && (
              <div style={{
                width: 48, height: 1.5, margin: '0 6px 22px 6px',
                background: isComplete ? PRIMARY : BORDER,
                transition: 'background 0.3s ease',
              }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
