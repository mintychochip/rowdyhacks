import { useState } from 'react';
import * as api from '../services/api';
import { SUCCESS, SUCCESS_BG10, ERROR, ERROR_BG20, ERROR_TEXT, TEXT_PRIMARY, TEXT_MUTED, INPUT_BG, INPUT_BORDER } from '../theme';

export default function CheckInPage() {
  const [qrInput, setQrInput] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCheckIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!qrInput.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await api.checkIn(qrInput.trim());
      setResult(data);
      setQrInput('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 500, margin: '40px auto' }}>
      <h2 style={{ fontSize: 24, marginBottom: 8 }}>Check-In Scanner</h2>
      <p style={{ color: TEXT_MUTED, marginBottom: 24, fontSize: 14 }}>Paste a QR token to check in a participant</p>

      <form onSubmit={handleCheckIn}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input
            value={qrInput}
            onChange={e => setQrInput(e.target.value)}
            placeholder="qr_abc123..."
            style={{ flex: 1, padding: '12px 16px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 8, color: '#fff', fontSize: 15, outline: 'none', boxSizing: 'border-box' }}
          />
          <button type="submit" disabled={loading}
            style={{ padding: '12px 24px', background: SUCCESS, border: 'none', borderRadius: 8, color: '#000', fontSize: 15, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1 }}>
            Check In
          </button>
        </div>
      </form>

      {error && (
        <div style={{ background: ERROR_BG20, border: `1px solid ${ERROR}`, borderRadius: 8, padding: 16, marginBottom: 16, color: ERROR_TEXT, fontSize: 14 }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ background: SUCCESS_BG10, border: `2px solid ${SUCCESS}`, borderRadius: 12, padding: 24, textAlign: 'center' }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>Checked In!</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: TEXT_PRIMARY }}>{result.team_name || 'Participant'}</div>
          <div style={{ fontSize: 13, color: TEXT_MUTED, marginTop: 4 }}>
            {new Date(result.checked_in_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}
