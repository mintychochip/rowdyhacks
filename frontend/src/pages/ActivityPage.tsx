import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import * as api from '../services/api';
import { CARD_BG, PRIMARY, TEXT_PRIMARY, TEXT_MUTED, BORDER, RADIUS, SPACE, CYAN, GOLD, SUCCESS } from '../theme';

interface ActivityEvent {
  id: string;
  event_type: string;
  title: string;
  detail: string | null;
  created_at: string;
}

const EVENT_ICONS: Record<string, { icon: string; color: string }> = {
  registration: { icon: 'person_add', color: PRIMARY },
  checkin: { icon: 'qr_code_scanner', color: SUCCESS },
  announcement: { icon: 'campaign', color: GOLD },
  judging: { icon: 'gavel', color: CYAN },
  submission: { icon: 'upload_file', color: '#a855f7' },
};

export default function ActivityPage() {
  const { hackathonId } = useParams<{ hackathonId: string }>();
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!hackathonId) return;

    api.getActivity(hackathonId).then((d: { events: ActivityEvent[] }) => {
      setEvents(d.events);
      setLoading(false);
    }).catch(() => setLoading(false));

    // WebSocket for live updates
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsHost = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '').replace(/\/api$/, '') || window.location.host;
    const ws = new WebSocket(`${wsProtocol}://${wsHost}/api/ws/hackathon/${hackathonId}`);
    wsRef.current = ws;

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.type === 'activity' && data.event) {
          setEvents(prev => [data.event, ...prev].slice(0, 200));
        }
      } catch { /* ignore */ }
    };

    ws.onclose = () => {};
    ws.onerror = () => {};

    return () => {
      ws.close();
    };
  }, [hackathonId]);

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = (now.getTime() - d.getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div style={{ padding: SPACE.lg, maxWidth: 700, margin: '0 auto' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, color: TEXT_PRIMARY, marginBottom: SPACE.lg }}>
        <span className="material-symbols-outlined" style={{ verticalAlign: 'middle', marginRight: 8, color: PRIMARY }}>timeline</span>
        Activity Feed
        <span style={{
          display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
          background: SUCCESS, marginLeft: 10, verticalAlign: 'middle',
          animation: 'pulse 2s infinite',
        }} />
      </h1>

      {loading ? (
        <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: 40 }}>Loading...</p>
      ) : events.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, display: 'block', marginBottom: 12 }}>hourglass_empty</span>
          No activity yet.
        </div>
      ) : (
        <div style={{ position: 'relative' }}>
          {/* Timeline line */}
          <div style={{
            position: 'absolute', left: 19, top: 0, bottom: 0, width: 2,
            background: BORDER,
          }} />

          {events.map(e => {
            const config = EVENT_ICONS[e.event_type] || { icon: 'info', color: TEXT_MUTED };
            return (
              <div key={e.id} style={{
                display: 'flex', gap: SPACE.md, marginBottom: SPACE.md,
                position: 'relative',
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: '50%',
                  background: `${config.color}15`, border: `2px solid ${config.color}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0, zIndex: 1,
                }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 18, color: config.color }}>{config.icon}</span>
                </div>
                <div style={{
                  flex: 1, background: CARD_BG, borderRadius: RADIUS.md,
                  padding: `${SPACE.sm} ${SPACE.md}`, border: `1px solid ${BORDER}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 14, fontWeight: 500, color: TEXT_PRIMARY }}>{e.title}</span>
                    <span style={{ fontSize: 11, color: TEXT_MUTED }}>{formatTime(e.created_at)}</span>
                  </div>
                  {e.detail && <p style={{ fontSize: 13, color: TEXT_MUTED, margin: '4px 0 0' }}>{e.detail}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
