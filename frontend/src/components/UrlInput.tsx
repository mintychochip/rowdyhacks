import { useState } from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { PRIMARY, GOLD, ERROR_TEXT, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE, INPUT_BG, INPUT_BORDER, CARD_BG, BORDER, TYPO, SPACE, RADIUS, SHADOW } from '../theme';

function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    const h = parsed.hostname;
    const labels = h.split('.');
    const isDevpost = labels.length >= 2 &&
      labels[labels.length - 2] === 'devpost' &&
      labels[labels.length - 1] === 'com';
    const isGithub = h === 'github.com' || h === 'www.github.com';
    return isDevpost || isGithub;
  } catch { return false; }
}

interface Props {
  onSubmit: (url: string) => void;
  disabled?: boolean;
  hackathonName?: string;
}

export default function UrlInput({ onSubmit, disabled, hackathonName }: Props) {
  const { isMobile } = useMediaQuery();
  const [url, setUrl] = useState('');
  const [localError, setLocalError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) { setLocalError('Please enter a URL'); return; }
    if (!isValidUrl(url.trim())) { setLocalError('Must be a Devpost or GitHub URL'); return; }
    setLocalError('');
    onSubmit(url.trim());
  };

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: `${SPACE.xl}px 0` }}>
      {/* Card */}
      <div style={{
        background: CARD_BG, border: `1px solid ${BORDER}`,
        borderRadius: RADIUS.lg, padding: SPACE.xl, boxShadow: SHADOW.card,
      }}>
        {/* Icon + Title */}
        <div style={{ textAlign: 'center', marginBottom: SPACE.md }}>
          <div style={{
            width: 48, height: 48, borderRadius: RADIUS.md,
            background: 'rgba(26,92,231,0.15)', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <span className="material-symbols-outlined" style={{ fontSize: 28, color: PRIMARY }}>verified</span>
          </div>
          <h2 data-mobile-h1 style={{ ...TYPO.h2, color: TEXT_PRIMARY, marginBottom: SPACE.sm }}>
            Check a Submission
          </h2>
          <p style={{ ...TYPO['body-lg'], color: TEXT_MUTED, maxWidth: 440, margin: '0 auto' }}>
            Paste a Devpost project URL to run integrity checks — commit history, code quality, team legitimacy, and more.
          </p>
        </div>

        {/* Hackathon badge */}
        {hackathonName && (
          <div style={{
            textAlign: 'center', marginBottom: SPACE.lg,
          }}>
            <span style={{
              display: 'inline-block', padding: '4px 14px', borderRadius: RADIUS.full,
              background: 'rgba(26,92,231,0.15)', border: '1px solid rgba(26,92,231,0.25)',
              color: PRIMARY, fontSize: 13, fontWeight: 600,
            }}>
              Submitting to {hackathonName}
            </span>
          </div>
        )}

        {/* Input + Button row */}
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', gap: SPACE.sm, maxWidth: 600, margin: '0 auto', flexDirection: isMobile ? 'column' : 'row' }}>
            <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center' }}>
              <span className="material-symbols-outlined" style={{
                position: 'absolute', left: 12, fontSize: 18, color: TEXT_MUTED, pointerEvents: 'none',
              }}>link</span>
              <input
                type="text"
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="https://devpost.com/software/your-project"
                disabled={disabled}
                style={{
                  width: '100%', padding: '12px 12px 12px 40px',
                  background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
                  borderRadius: RADIUS.sm, color: TEXT_WHITE,
                  fontSize: 14, outline: 'none', fontFamily: 'inherit',
                }}
              />
            </div>
            <button type="submit" disabled={disabled}
              style={{
                padding: '12px 28px', background: disabled ? '#1a5ce760' : PRIMARY,
                border: 'none', borderRadius: RADIUS.sm, color: TEXT_WHITE,
                fontSize: 14, fontWeight: 600, fontFamily: 'inherit',
                cursor: disabled ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
              }}>
              Start Analysis
            </button>
          </div>
          {localError && (
            <p style={{ color: ERROR_TEXT, marginTop: SPACE.sm, fontSize: 13, textAlign: 'center' }}>{localError}</p>
          )}
        </form>

        {/* Footer hint */}
        <p style={{
          textAlign: 'center', marginTop: SPACE.md,
          ...TYPO['body-sm'], color: TEXT_MUTED,
        }}>
          Supports Devpost project pages and GitHub repositories
        </p>
      </div>
    </div>
  );
}
