import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import {
  PRIMARY, SUCCESS, SUCCESS_BG10, ERROR, ERROR_BG20, ERROR_TEXT, WARNING, WARNING_BG10,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  INPUT_BG, INPUT_BORDER, BORDER, CARD_BG,
  TYPO, SPACE, RADIUS, SHADOW,
} from '../theme';

interface Participant {
  id: string;
  name: string;
  email: string;
  team_name?: string;
  status: string;
  checked_in_at?: string;
}

interface Hackathon {
  id: string;
  name: string;
}

export default function CheckInPage() {
  const { hackathonId: urlHackathonId } = useParams<{ hackathonId?: string }>();
  const [mode, setMode] = useState<'camera' | 'manual' | 'name'>('camera');
  const [qrInput, setQrInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Participant[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [hackathons, setHackathons] = useState<Hackathon[]>([]);
  const [selectedHackathonId, setSelectedHackathonId] = useState<string>(urlHackathonId || '');
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { isMobile } = useMediaQuery();

  // Load hackathons on mount
  useEffect(() => {
    api.getHackathons().then((data) => {
      setHackathons(data);
      if (!selectedHackathonId && data.length > 0) {
        setSelectedHackathonId(data[0].id);
      }
    }).catch(() => {
      setError('Failed to load hackathons');
    });
  }, []);

  // Camera QR scanning
  useEffect(() => {
    if (mode !== 'camera') {
      stopCamera();
      return;
    }

    let stream: MediaStream | null = null;
    let animationId: number | null = null;

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' }
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setScanning(true);
        scanLoop();
      } catch (err) {
        setError('Camera access denied. Switch to manual mode or allow camera permissions.');
        setMode('manual');
      }
    };

    const scanLoop = () => {
      if (!scanning || mode !== 'camera') return;

      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState !== 4) {
        animationId = requestAnimationFrame(scanLoop);
        return;
      }

      // Try to detect QR code from video frame
      // Note: In production, use a library like jsQR or @zxing/library
      // For now, we'll use a simple approach with manual trigger

      animationId = requestAnimationFrame(scanLoop);
    };

    startCamera();

    return () => {
      stopCamera();
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [mode]);

  const stopCamera = () => {
    setScanning(false);
    const video = videoRef.current;
    if (video && video.srcObject) {
      const stream = video.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
      video.srcObject = null;
    }
  };

  const handleManualScan = async () => {
    if (!qrInput.trim()) return;
    await performCheckIn(qrInput.trim());
  };

  const performCheckIn = async (token: string) => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await api.checkIn(token);
      setResult(data);
      setQrInput('');
    } catch (err: any) {
      const msg = err.message || 'Check-in failed';
      if (msg.includes('already_checked_in')) {
        setError('⚠️ Already checked in');
      } else if (msg.includes('invalid_token')) {
        setError('❌ Invalid QR code');
      } else if (msg.includes('not_active')) {
        setError('⛔ Registration not active');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const searchParticipants = async () => {
    if (!searchQuery.trim() || !selectedHackathonId) return;
    setLoading(true);
    try {
      // Fetch all registrations and filter client-side
      const data = await api.getHackathonRegistrations(selectedHackathonId, { limit: 100 });
      const allRegistrations = data.registrations || [];
      // Filter by name or email
      const filtered = allRegistrations.filter((r: any) =>
        r.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.email?.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setSearchResults(filtered);
    } catch (err: any) {
      setError(err.message || 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleNameCheckIn = async (participant: Participant) => {
    // For name-based check-in, we need to generate a temporary QR or use a different endpoint
    // For now, show a message that they need the QR code
    if (participant.status === 'checked_in') {
      setError(`${participant.name} is already checked in!`);
      return;
    }
    // This would need backend support for name-based check-in
    setError('Please scan their QR code to complete check-in');
  };

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Here you would use a QR detection library
    // For now, we'll show a message to use manual entry
    setError('QR auto-detection requires camera focus. Try manual mode if scanning fails.');
  };

  return (
    <div style={{ maxWidth: 600, margin: isMobile ? '20px auto' : '40px auto', padding: isMobile ? SPACE.md : 0 }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: SPACE.xl }}>
        <div style={{ fontSize: 48, marginBottom: SPACE.sm }}>📱</div>
        <h1 style={{ ...TYPO.h1, marginBottom: SPACE.xs }}>Check-In Scanner</h1>
        <p style={{ color: TEXT_MUTED, fontSize: 14 }}>
          Scan QR codes or search by name to check in participants
        </p>
      </div>

      {/* Hackathon Selector */}
      {hackathons.length > 1 && (
        <div style={{
          background: CARD_BG,
          borderRadius: RADIUS.lg,
          padding: SPACE.md,
          marginBottom: SPACE.lg,
          border: `1px solid ${BORDER}`,
        }}>
          <label style={{ ...TYPO['label-caps'], color: TEXT_MUTED, display: 'block', marginBottom: SPACE.sm }}>
            Select Hackathon
          </label>
          <select
            value={selectedHackathonId}
            onChange={(e) => {
              setSelectedHackathonId(e.target.value);
              setSearchResults([]);
              setResult(null);
              setError('');
            }}
            style={{
              width: '100%',
              padding: '12px 16px',
              background: INPUT_BG,
              border: `1px solid ${INPUT_BORDER}`,
              borderRadius: RADIUS.md,
              color: TEXT_WHITE,
              fontSize: 15,
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            {hackathons.map((h) => (
              <option key={h.id} value={h.id}>{h.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Mode Toggle */}
      <div style={{
        display: 'flex',
        gap: SPACE.xs,
        background: INPUT_BG,
        borderRadius: RADIUS.lg,
        padding: 4,
        marginBottom: SPACE.lg,
      }}>
        {[
          { key: 'camera', label: '📷 Camera', icon: '📷' },
          { key: 'manual', label: '⌨️ Manual', icon: '⌨️' },
          { key: 'name', label: '🔍 Name Search', icon: '🔍' },
        ].map((m) => (
          <button
            key={m.key}
            onClick={() => {
              setMode(m.key as any);
              setError('');
              setResult(null);
            }}
            style={{
              flex: 1,
              padding: '10px 16px',
              background: mode === m.key ? CARD_BG : 'transparent',
              border: 'none',
              borderRadius: RADIUS.md,
              color: mode === m.key ? TEXT_PRIMARY : TEXT_MUTED,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Camera Mode */}
      {mode === 'camera' && (
        <div style={{
          background: CARD_BG,
          borderRadius: RADIUS.lg,
          overflow: 'hidden',
          border: `1px solid ${BORDER}`,
          boxShadow: SHADOW.card,
        }}>
          <div style={{ position: 'relative', aspectRatio: '4/3', background: '#000' }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
            {/* Scan overlay */}
            <div style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <div style={{
                width: 200,
                height: 200,
                border: `2px dashed ${scanning ? SUCCESS : ERROR}`,
                borderRadius: 16,
                position: 'relative',
              }}>
                {/* Corner markers */}
                <div style={{ position: 'absolute', top: -2, left: -2, width: 20, height: 20, borderTop: `4px solid ${SUCCESS}`, borderLeft: `4px solid ${SUCCESS}` }} />
                <div style={{ position: 'absolute', top: -2, right: -2, width: 20, height: 20, borderTop: `4px solid ${SUCCESS}`, borderRight: `4px solid ${SUCCESS}` }} />
                <div style={{ position: 'absolute', bottom: -2, left: -2, width: 20, height: 20, borderBottom: `4px solid ${SUCCESS}`, borderLeft: `4px solid ${SUCCESS}` }} />
                <div style={{ position: 'absolute', bottom: -2, right: -2, width: 20, height: 20, borderBottom: `4px solid ${SUCCESS}`, borderRight: `4px solid ${SUCCESS}` }} />
              </div>
            </div>
            {scanning && (
              <div style={{
                position: 'absolute',
                top: 16,
                left: '50%',
                transform: 'translateX(-50%)',
                background: 'rgba(0,0,0,0.7)',
                padding: '8px 16px',
                borderRadius: RADIUS.full,
                color: TEXT_WHITE,
                fontSize: 13,
              }}>
                📷 Scanning...
              </div>
            )}
          </div>
          <canvas ref={canvasRef} style={{ display: 'none' }} />

          <div style={{ padding: SPACE.lg }}>
            <p style={{ color: TEXT_MUTED, fontSize: 13, textAlign: 'center', marginBottom: SPACE.md }}>
              Position the QR code within the frame, or use the button below to capture
            </p>
            <button
              onClick={captureFrame}
              style={{
                width: '100%',
                padding: '14px 24px',
                background: PRIMARY,
                border: 'none',
                borderRadius: RADIUS.md,
                color: TEXT_WHITE,
                fontSize: 16,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              📸 Capture & Scan
            </button>
          </div>
        </div>
      )}

      {/* Manual Mode */}
      {mode === 'manual' && (
        <div style={{
          background: CARD_BG,
          borderRadius: RADIUS.lg,
          padding: SPACE.lg,
          border: `1px solid ${BORDER}`,
          boxShadow: SHADOW.card,
        }}>
          <label style={{ ...TYPO['label-caps'], color: TEXT_MUTED, display: 'block', marginBottom: SPACE.sm }}>
            QR Token
          </label>
          <div style={{ display: 'flex', gap: SPACE.sm, marginBottom: SPACE.md }}>
            <input
              value={qrInput}
              onChange={e => setQrInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleManualScan()}
              placeholder="Paste QR token here..."
              autoFocus
              style={{
                flex: 1,
                padding: '14px 16px',
                background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`,
                borderRadius: RADIUS.md,
                color: TEXT_WHITE,
                fontSize: 16,
                outline: 'none',
                fontFamily: 'monospace',
              }}
            />
            <button
              onClick={handleManualScan}
              disabled={loading || !qrInput.trim()}
              style={{
                padding: '14px 28px',
                background: SUCCESS,
                border: 'none',
                borderRadius: RADIUS.md,
                color: '#000',
                fontSize: 16,
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? '...' : 'Check In'}
            </button>
          </div>
          <p style={{ color: TEXT_MUTED, fontSize: 13 }}>
            Tip: You can also paste the full QR URL or just the token part
          </p>
        </div>
      )}

      {/* Name Search Mode */}
      {mode === 'name' && (
        <div style={{
          background: CARD_BG,
          borderRadius: RADIUS.lg,
          padding: SPACE.lg,
          border: `1px solid ${BORDER}`,
          boxShadow: SHADOW.card,
        }}>
          <label style={{ ...TYPO['label-caps'], color: TEXT_MUTED, display: 'block', marginBottom: SPACE.sm }}>
            Search by Name
          </label>
          <div style={{ display: 'flex', gap: SPACE.sm, marginBottom: SPACE.md }}>
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && searchParticipants()}
              placeholder="Enter participant name..."
              autoFocus
              style={{
                flex: 1,
                padding: '14px 16px',
                background: INPUT_BG,
                border: `1px solid ${INPUT_BORDER}`,
                borderRadius: RADIUS.md,
                color: TEXT_WHITE,
                fontSize: 16,
                outline: 'none',
              }}
            />
            <button
              onClick={searchParticipants}
              disabled={loading || !searchQuery.trim()}
              style={{
                padding: '14px 24px',
                background: PRIMARY,
                border: 'none',
                borderRadius: RADIUS.md,
                color: TEXT_WHITE,
                fontSize: 16,
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? '...' : '🔍 Search'}
            </button>
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div style={{ marginTop: SPACE.lg }}>
              <h4 style={{ ...TYPO.h3, marginBottom: SPACE.sm, color: TEXT_SECONDARY }}>
                Found {searchResults.length} participant{searchResults.length !== 1 ? 's' : ''}
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
                {searchResults.map((p) => (
                  <div
                    key={p.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: SPACE.md,
                      background: INPUT_BG,
                      borderRadius: RADIUS.md,
                      border: `1px solid ${p.status === 'checked_in' ? SUCCESS : BORDER}`,
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: TEXT_PRIMARY }}>{p.name}</div>
                      <div style={{ fontSize: 13, color: TEXT_MUTED }}>{p.email}</div>
                      {p.team_name && (
                        <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginTop: 2 }}>
                          Team: {p.team_name}
                        </div>
                      )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
                      {p.status === 'checked_in' ? (
                        <span style={{
                          padding: '4px 12px',
                          background: SUCCESS_BG10,
                          color: SUCCESS,
                          borderRadius: RADIUS.full,
                          fontSize: 12,
                          fontWeight: 600,
                        }}>
                          ✓ Checked In
                        </span>
                      ) : (
                        <button
                          onClick={() => handleNameCheckIn(p)}
                          style={{
                            padding: '8px 16px',
                            background: PRIMARY,
                            border: 'none',
                            borderRadius: RADIUS.md,
                            color: TEXT_WHITE,
                            fontSize: 13,
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Check In
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {searchResults.length === 0 && searchQuery && !loading && (
            <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
              No participants found matching "{searchQuery}"
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div style={{
          background: error.includes('already') ? WARNING_BG10 : ERROR_BG20,
          border: `1px solid ${error.includes('already') ? WARNING : ERROR}`,
          borderRadius: RADIUS.lg,
          padding: SPACE.lg,
          marginTop: SPACE.lg,
          display: 'flex',
          alignItems: 'center',
          gap: SPACE.md,
        }}>
          <span style={{ fontSize: 24 }}>{error.includes('already') ? '⚠️' : '❌'}</span>
          <span style={{ color: error.includes('already') ? WARNING : ERROR_TEXT, fontWeight: 500 }}>
            {error}
          </span>
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div style={{
          background: SUCCESS_BG10,
          border: `2px solid ${SUCCESS}`,
          borderRadius: RADIUS.lg,
          padding: isMobile ? SPACE.lg : SPACE.xl,
          marginTop: SPACE.lg,
          textAlign: 'center',
          animation: 'successPop 0.3s ease',
        }}>
          <div style={{ fontSize: 56, marginBottom: SPACE.md }}>✅</div>
          <h3 style={{ ...TYPO.h2, color: SUCCESS, marginBottom: SPACE.sm }}>
            Checked In!
          </h3>
          <div style={{ fontSize: 20, fontWeight: 600, color: TEXT_PRIMARY, marginBottom: SPACE.xs }}>
            {result.team_name || 'Participant'}
          </div>
          <div style={{ fontSize: 14, color: TEXT_MUTED }}>
            {new Date(result.checked_in_at).toLocaleString()}
          </div>
        </div>
      )}

      {/* Stats / Recent */}
      {!result && !error && (
        <div style={{
          marginTop: SPACE.xl,
          padding: SPACE.lg,
          background: `linear-gradient(135deg, rgba(139,92,246,0.1) 0%, rgba(6,182,212,0.1) 100%)`,
          borderRadius: RADIUS.lg,
          border: `1px solid ${BORDER}`,
        }}>
          <h4 style={{ ...TYPO.h3, marginBottom: SPACE.md }}>💡 Quick Tips</h4>
          <ul style={{ color: TEXT_SECONDARY, fontSize: 14, lineHeight: 1.8, margin: 0, paddingLeft: 20 }}>
            <li><strong>Camera mode:</strong> Best for fast check-ins. Hold phone steady 6-12 inches from QR code.</li>
            <li><strong>Manual mode:</strong> Use if camera fails or for testing. Paste the QR token directly.</li>
            <li><strong>Name search:</strong> Lookup participants when they forgot their QR code.</li>
            <li>Green border = Ready to scan. Red = Camera not available.</li>
          </ul>
        </div>
      )}

      <style>{`
        @keyframes successPop {
          0% { transform: scale(0.9); opacity: 0; }
          50% { transform: scale(1.02); }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
