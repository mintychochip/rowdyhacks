import { useState, useMemo } from 'react';
import { CARD_BG, INPUT_BG, PRIMARY, SUCCESS, SUCCESS_BG10, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER, BORDER_LIGHT, GOLD, TYPO, SPACE, RADIUS } from '../theme';

interface ScheduleEvent {
  datetime: string;
  end_datetime?: string;
  title: string;
  description?: string;
  location?: string;
}

interface Props {
  events: ScheduleEvent[];
}

const HOUR_H = 72;

function timeToY(date: Date, dayStart: Date): number {
  return ((date.getHours() * 60 + date.getMinutes()) / 60) * HOUR_H;
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

function fmtDay(d: Date): string {
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

export default function ScheduleGrid({ events }: Props) {
  const now = Date.now();

  const days = useMemo(() => {
    if (!events || events.length === 0) return [];
    const parsed = events.map(e => ({
      ...e,
      start: new Date(e.datetime),
      end: e.end_datetime ? new Date(e.end_datetime) : new Date(new Date(e.datetime).getTime() + 60 * 60 * 1000),
    })).sort((a, b) => a.start.getTime() - b.start.getTime());

    // Split multi-day events across days
    const map: Record<string, typeof parsed> = {};
    for (const ev of parsed) {
      const dayMs = 24 * 60 * 60 * 1000;
      // Cap to max 3 days to avoid infinite loops
      for (let d = new Date(ev.start); d < ev.end && d.getTime() < ev.start.getTime() + 3 * dayMs; d = new Date(d.getTime() + dayMs)) {
        d.setHours(0, 0, 0, 0);
        const dayEnd = new Date(d.getTime() + dayMs);
        const key = d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
        const segStart = ev.start > d ? ev.start : d;
        const segEnd = ev.end < dayEnd ? ev.end : dayEnd;
        if (segStart < segEnd) {
          (map[key] ||= []).push({ ...ev, start: segStart, end: segEnd });
        }
      }
    }
    return Object.entries(map);
  }, [events]);

  // Default to today's tab, or the first day
  const todayKey = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  const defaultIdx = Math.max(0, days.findIndex(([key]) => key === todayKey));
  const [activeIdx, setActiveIdx] = useState(defaultIdx);

  if (days.length === 0) return null;

  const [dayLabel, dayEvents] = days[activeIdx];

  // Time range
  const dayStart = new Date(dayEvents[0].start);
  dayStart.setHours(Math.floor(dayStart.getHours()), 0, 0, 0);
  const dayEnd = new Date(dayEvents[dayEvents.length - 1].end);
  dayEnd.setHours(Math.ceil(dayEnd.getHours()) + 1 || 24, 0, 0, 0);
  const height = ((dayEnd.getTime() - dayStart.getTime()) / (1000 * 60 * 60)) * HOUR_H;

  // Assign columns for overlaps
  const cols: number[] = new Array(dayEvents.length).fill(0);
  for (let i = 0; i < dayEvents.length; i++) {
    const used = new Set<number>();
    for (let j = 0; j < i; j++) {
      if (dayEvents[j].end > dayEvents[i].start && dayEvents[j].start < dayEvents[i].end) {
        used.add(cols[j]);
      }
    }
    let c = 0; while (used.has(c)) c++;
    cols[i] = c;
  }
  const maxCols = Math.max(...cols, 0) + 1;

  const hours: Date[] = [];
  for (let h = dayStart.getTime(); h < dayEnd.getTime(); h += 60 * 60 * 1000) {
    hours.push(new Date(h));
  }

  return (
    <div style={{
      background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
      padding: SPACE.lg, overflow: 'hidden',
    }}>
      {/* Day tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: SPACE.lg, flexWrap: 'wrap' }}>
        {days.map(([key, evs], i) => {
          const active = i === activeIdx;
          const dayDate = evs[0].start;
          const isToday = key === todayKey;
          return (
            <button
              key={key}
              onClick={() => setActiveIdx(i)}
              style={{
                padding: '8px 16px',
                background: active ? PRIMARY : INPUT_BG,
                border: active ? `1px solid ${PRIMARY}` : `1px solid ${BORDER_LIGHT}`,
                borderRadius: RADIUS.md,
                color: active ? '#fff' : TEXT_SECONDARY,
                fontSize: 13, fontWeight: active ? 700 : 500,
                cursor: 'pointer', textAlign: 'left',
              }}>
              <div>{fmtDay(dayDate)}</div>
              {isToday && <div style={{ fontSize: 10, color: active ? '#fff' : GOLD, opacity: active ? 0.8 : 1 }}>Today</div>}
            </button>
          );
        })}
      </div>

      {/* Grid */}
      <div style={{ display: 'flex', position: 'relative', height, minHeight: 200, overflow: 'hidden' }}>
        {/* Time column */}
        <div style={{
          width: 52, flexShrink: 0, position: 'relative',
          borderRight: `1px solid ${BORDER_LIGHT}`,
        }}>
          {hours.map((h, i) => (
            <div key={i} style={{
              position: 'absolute', top: timeToY(h, dayStart),
              fontSize: 10, color: TEXT_MUTED,
              transform: 'translateY(-50%)',
            }}>
              {h.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
            </div>
          ))}
        </div>

        {/* Events area */}
        <div style={{ flex: 1, position: 'relative' }}>
          {hours.map((h, i) => (
            <div key={i} style={{
              position: 'absolute', top: timeToY(h, dayStart), left: 0, right: 0,
              height: 1, background: BORDER_LIGHT, opacity: 0.4,
            }} />
          ))}

          {/* Now line */}
          {(() => {
            const n = new Date(now);
            if (n >= dayStart && n <= dayEnd) {
              return (
                <div style={{
                  position: 'absolute', top: timeToY(n, dayStart), left: 0, right: 0,
                  height: 2, background: SUCCESS, zIndex: 5, opacity: 0.7,
                }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%', background: SUCCESS,
                    position: 'absolute', left: -3, top: -2,
                  }} />
                </div>
              );
            }
            return null;
          })()}

          {dayEvents.map((ev, i) => {
            const top = timeToY(ev.start, dayStart);
            const h = timeToY(ev.end, dayStart) - top;
            const colWidth = (100 / maxCols);
            const live = now >= ev.start.getTime() && now <= ev.end.getTime();
            const past = ev.end.getTime() < now;

            return (
              <div key={i} style={{
                position: 'absolute', top, left: `${cols[i] * colWidth}%`,
                height: Math.max(h, 28),
                width: `calc(${colWidth}% - 4px)`,
                padding: '6px 8px', borderRadius: RADIUS.sm,
                background: live ? SUCCESS_BG10 : INPUT_BG,
                border: live ? `1px solid ${SUCCESS}50` : `1px solid ${BORDER_LIGHT}`,
                opacity: past ? 0.5 : 1,
                overflow: 'hidden', boxSizing: 'border-box',
                zIndex: live ? 3 : 1,
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: live ? SUCCESS : TEXT_PRIMARY, lineHeight: 1.3 }}>
                  {ev.title}
                </div>
                <div style={{ fontSize: 10, color: TEXT_MUTED, lineHeight: 1.4 }}>
                  {formatTime(ev.start)} – {formatTime(ev.end)}
                </div>
                {ev.location && h > 50 && (
                  <div style={{ fontSize: 10, color: TEXT_SECONDARY, marginTop: 1 }}>{ev.location}</div>
                )}
                {live && (
                  <span style={{
                    display: 'inline-block', marginTop: 4,
                    fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
                    padding: '1px 6px', borderRadius: RADIUS.full,
                    background: SUCCESS_BG10, color: SUCCESS, letterSpacing: '0.05em',
                  }}>
                    LIVE
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
