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
  role?: string;
}

interface Hackathon {
  id: string;
  name: string;
}

export default function CheckInPage() {
  const { hackathonId: urlHackathonId } = useParams<{ hackathonId?: string }>();
  const { isMobile } = useMediaQuery();
  // Default to camera on mobile, manual on desktop (camera often blocked on web)
  const [mode, setMode] = useState<'camera' | 'manual' | 'name'>(isMobile ? 'camera' : 'manual');
  const [qrInput, setQrInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [allParticipants, setAllParticipants] = useState<Participant[]>([]);
  const [searchResults, setSearchResults] = useState<Participant[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [hackathons, setHackathons] = useState<Hackathon[]>([]);
  const [selectedHackathonId, setSelectedHackathonId] = useState<string>(urlHackathonId || '');
  const [cameraSupported, setCameraSupported] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

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

    // Check if camera is supported in this environment
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraSupported(false);
      setError('Camera not available in this browser. Using manual mode.');
      setMode('manual');
      return;
    }

    let stream: MediaStream | null = null;
    let animationId: number | null = null;

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: isMobile ? 'environment' : 'user' }
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setScanning(true);
        scanLoop();
      } catch (err: any) {
        const isPermissionDenied = err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError';
        const isNotFound = err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError';
        if (isPermissionDenied) {
          setError('Camera access denied. Click the camera icon in your browser address bar to allow access, or switch to manual mode.');
        } else if (isNotFound) {
          setError('No camera found. Please use manual mode to enter QR codes.');
        } else {
          setError(`Camera error: ${err.message || 'Unknown error'}. Switch to manual mode.`);
        }
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

  // Load all participants when switching to name search mode
  useEffect(() => {
    if (mode === 'name' && selectedHackathonId) {
      loadAllParticipants();
    }
  }, [mode, selectedHackathonId]);

  // Real-time filtering as user types
  useEffect(() => {
    if (mode !== 'name') return;

    if (!searchQuery.trim()) {
      // Show all participants sorted by status (pending/accepted first, checked_in last)
      const sorted = [...allParticipants].sort((a, b) => {
        if (a.status === b.status) return a.name.localeCompare(b.name);
        if (a.status === 'checked_in') return 1;
        if (b.status === 'checked_in') return -1;
        return a.name.localeCompare(b.name);
      });
      setSearchResults(sorted);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = allParticipants.filter((p) =>
        p.name?.toLowerCase().includes(query) ||
        p.email?.toLowerCase().includes(query) ||
        p.team_name?.toLowerCase().includes(query)
      );
      setSearchResults(filtered);
    }
  }, [searchQuery, allParticipants, mode]);

  const loadAllParticipants = async () => {
    if (!selectedHackathonId) return;
    setLoading(true);
    setError('');
    try {
      // Fetch all registrations - backend max is 100 per request, so we may need pagination for large events
      const data = await api.getHackathonRegistrations(selectedHackathonId, { limit: 100 });
      // Handle both {registrations: [...]} and direct array response
      const registrations = Array.isArray(data) ? data : (data.registrations || []);
      // Map API response to Participant interface
      const participants: Participant[] = registrations.map((r: any) => ({
        id: r.id,
        name: r.user_name || r.name || 'Unknown',
        email: r.user_email || r.email || '',
        team_name: r.team_name,
        status: r.status,
        checked_in_at: r.checked_in_at,
        role: r.user_role,
      }));
      setAllParticipants(participants);
      // Initially show all (sorted: pending/accepted first, checked_in last)
      const sorted = [...participants].sort((a, b) => {
        if (a.status === b.status) return a.name.localeCompare(b.name);
        if (a.status === 'checked_in') return 1;
        if (b.status === 'checked_in') return -1;
        return a.name.localeCompare(b.name);
      });
      setSearchResults(sorted);
    } catch (err: any) {
      // Handle FastAPI validation errors which are arrays of {loc, msg, type}
      let errorMsg: string;
      if (Array.isArray(err)) {
        errorMsg = err.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
      } else if (typeof err === 'object' && err !== null) {
        errorMsg = err.message || err.detail || JSON.stringify(err);
      } else {
        errorMsg = String(err) || 'Failed to load participants';
      }
      console.error('Failed to load participants:', err);
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const searchParticipants = async () => {
    // Real-time filtering handles this automatically
    // This function kept for Enter key compatibility
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
          { key: 'camera', label: '📷 Camera', icon: '📷', disabled: !cameraSupported },
          { key: 'manual', label: '⌨️ Manual', icon: '⌨️', disabled: false },
          { key: 'name', label: '🔍 Name Search', icon: '🔍', disabled: false },
        ].map((m) => (
          <button
            key={m.key}
            onClick={() => {
              if (m.disabled) return;
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
              color: m.disabled ? TEXT_MUTED : (mode === m.key ? TEXT_PRIMARY : TEXT_MUTED),
              fontSize: 14,
              fontWeight: 600,
              cursor: m.disabled ? 'not-allowed' : 'pointer',
              opacity: m.disabled ? 0.4 : 1,
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
            Search by Name, Email, or Team
          </label>
          <div style={{ display: 'flex', gap: SPACE.sm, marginBottom: SPACE.md }}>
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder={loading ? 'Loading participants...' : 'Type to filter participants...'}
              autoFocus
              disabled={loading}
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
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                style={{
                  padding: '14px 20px',
                  background: INPUT_BG,
                  border: `1px solid ${INPUT_BORDER}`,
                  borderRadius: RADIUS.md,
                  color: TEXT_MUTED,
                  fontSize: 14,
                  cursor: 'pointer',
                }}
              >
                ✕ Clear
              </button>
            )}
          </div>

          {/* Results Count */}
          <div style={{ marginBottom: SPACE.md, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: TEXT_MUTED, fontSize: 13 }}>
              {loading
                ? 'Loading participants...'
                : searchQuery.trim()
                  ? `${searchResults.length} result${searchResults.length !== 1 ? 's' : ''} for "${searchQuery}"`
                  : `${allParticipants.length} total participant${allParticipants.length !== 1 ? 's' : ''} (pending/accepted first)`
              }
            </span>
            <button
              onClick={loadAllParticipants}
              disabled={loading}
              style={{
                padding: '6px 12px',
                background: 'transparent',
                border: `1px solid ${BORDER}`,
                borderRadius: RADIUS.md,
                color: TEXT_SECONDARY,
                fontSize: 12,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.5 : 1,
              }}
            >
              🔄 Refresh
            </button>
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div style={{ maxHeight: '400px', overflow: 'auto' }}>
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
                      <div style={{ fontWeight: 600, color: TEXT_PRIMARY, display: 'flex', alignItems: 'center', gap: SPACE.xs }}>
                        {p.name}
                        {p.role && p.role !== 'participant' && (
                          <span style={{
                            padding: '2px 8px',
                            background: p.role === 'judge' ? '#8b5cf6' : PRIMARY,
                            borderRadius: RADIUS.sm,
                            fontSize: 11,
                            fontWeight: 700,
                            color: '#fff',
                            textTransform: 'uppercase',
                          }}>
                            {p.role}
                          </span>
                        )}
                      </div>
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

          {searchResults.length === 0 && !loading && (
            <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
              {searchQuery.trim()
                ? `No participants found matching "${searchQuery}"`
                : allParticipants.length === 0
                  ? 'No participants found for this hackathon'
                  : 'All participants filtered out'
              }
            </div>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div style={{
          background: error.includes?.('already') ? WARNING_BG10 : ERROR_BG20,
          border: `1px solid ${error.includes?.('already') ? WARNING : ERROR}`,
          borderRadius: RADIUS.lg,
          padding: SPACE.lg,
          marginTop: SPACE.lg,
          display: 'flex',
          alignItems: 'center',
          gap: SPACE.md,
        }}>
          <span style={{ fontSize: 24 }}>{error.includes?.('already') ? '⚠️' : '❌'}</span>
          <span style={{ color: error.includes?.('already') ? WARNING : ERROR_TEXT, fontWeight: 500 }}>
            {typeof error === 'string' ? error : JSON.stringify(error)}
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
            {!cameraSupported && <li style={{ color: WARNING }}><strong>Web browser detected:</strong> Camera mode not available. Use Manual or Name Search mode.</li>}
            <li><strong>Camera mode:</strong> {cameraSupported ? 'Best for fast check-ins. Hold phone steady 6-12 inches from QR code.' : 'Not available in this browser.'}</li>
            <li><strong>Manual mode:</strong> Paste the QR token directly. Best for desktop browsers.</li>
            <li><strong>Name search:</strong> Lookup participants when they forgot their QR code.</li>
            {cameraSupported && <li>Green border = Ready to scan. Red = Camera not available.</li>}
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
