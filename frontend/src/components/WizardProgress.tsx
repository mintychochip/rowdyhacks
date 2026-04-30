import { PRIMARY, GOLD, TEXT_PRIMARY, TEXT_MUTED, BORDER, RADIUS } from '../theme';

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
    <div style={{ display: 'flex', justifyContent: 'center', gap: 0, marginBottom: 32 }}>
      {STEPS.map((s, i) => {
        const isActive = s.step === currentStep;
        const isComplete = s.step < currentStep;
        const isLast = i === STEPS.length - 1;

        let dotBg = 'transparent';
        let dotBorder = `2px solid ${BORDER}`;
        let dotColor = TEXT_MUTED;
        if (isComplete) {
          dotBg = GOLD;
          dotBorder = `2px solid ${GOLD}`;
          dotColor = '#000';
        } else if (isActive) {
          dotBg = PRIMARY;
          dotBorder = `2px solid ${PRIMARY}`;
          dotColor = '#fff';
        }

        return (
          <div key={s.step} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
              <div style={{
                width: 32, height: 32, borderRadius: RADIUS.full,
                background: dotBg, border: dotBorder,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, fontWeight: 700, color: dotColor,
                transition: 'all 0.2s',
              }}>
                {isComplete ? '\u2713' : s.step}
              </div>
              <span style={{
                fontSize: 10, fontWeight: 600, color: isActive ? TEXT_PRIMARY : TEXT_MUTED,
                textTransform: 'uppercase', letterSpacing: '0.05em',
                whiteSpace: 'nowrap',
              }}>
                {s.label}
              </span>
            </div>
            {!isLast && (
              <div style={{
                width: 48, height: 2, margin: '0 4px 20px 4px',
                background: isComplete ? GOLD : BORDER,
                transition: 'background 0.2s',
              }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
