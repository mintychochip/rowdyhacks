import { useState } from 'react';
import { PRIMARY, ERROR_TEXT, TEXT_MUTED, INPUT_BG, INPUT_BORDER } from '../theme';

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
}

export default function UrlInput({ onSubmit, disabled }: Props) {
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
    <form onSubmit={handleSubmit} style={{ textAlign: 'center', padding: '40px 0' }}>
      <h2 style={{ marginBottom: 8, fontSize: 28 }}>Check a Submission</h2>
      <p style={{ color: TEXT_MUTED, marginBottom: 24, fontSize: 15 }}>Paste a Devpost or GitHub URL to analyze</p>
      <div style={{ display: 'flex', gap: 8, maxWidth: 600, margin: '0 auto' }}>
        <input
          type="text"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://devpost.com/software/your-project"
          disabled={disabled}
          style={{ flex: 1, padding: '12px 16px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 8, color: '#fff', fontSize: 15, outline: 'none' }}
        />
        <button type="submit" disabled={disabled}
          style={{ padding: '12px 24px', background: PRIMARY, border: 'none', borderRadius: 8, color: '#fff', fontSize: 15, fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.6 : 1 }}>
          Analyze
        </button>
      </div>
      {localError && <p style={{ color: ERROR_TEXT, marginTop: 12, fontSize: 14 }}>{localError}</p>}
    </form>
  );
}
