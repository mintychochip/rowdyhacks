import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import UrlInput from '../components/UrlInput';
import ReportCard from '../components/ReportCard';
import CheckResultRow from '../components/CheckResultRow';
import { useAnalysis } from '../hooks/useAnalysis';
import {
  PRIMARY, SUCCESS, ERROR_TEXT,
  TEXT_MUTED, TEXT_DIM, TEXT_WHITE,
  INPUT_BG, INPUT_BORDER, BORDER, CARD_BG,
  TYPO, SPACE, RADIUS,
} from '../theme';
import { Button } from '../components/Primitives';

function groupByCategory(checks: Array<{ check_category: string; score: number }>) {
  const groups: Record<string, number[]> = {};
  for (const c of checks) {
    (groups[c.check_category] ||= []).push(c.score);
  }
  return Object.entries(groups).map(([category, scores]) => ({
    category,
    score: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
  }));
}

function ElapsedTimer({ running }: { running: boolean }) {
  const [elapsed, setElapsed] = useState(0);
  const ref = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (running) {
      setElapsed(0);
      ref.current = setInterval(() => setElapsed(e => e + 1), 1000);
    } else {
      if (ref.current) clearInterval(ref.current);
    }
    return () => { if (ref.current) clearInterval(ref.current); };
  }, [running]);

  if (!running || elapsed < 2) return null;
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return (
    <div style={{ ...TYPO['body-sm'], color: TEXT_DIM, marginTop: SPACE.md }}>
      Elapsed: {mins}:{secs.toString().padStart(2, '0')}
    </div>
  );
}

const STAGES = [
  { key: 'scraping', label: 'Scraping Devpost page', desc: 'Extracting project info, tech stack, and team members' },
  { key: 'cloning', label: 'Cloning repository', desc: 'Downloading source code for analysis' },
  { key: 'checking', label: 'Running integrity checks', desc: 'Analyzing commits, code, assets, and more' },
  { key: 'scoring', label: 'Computing risk score', desc: 'Aggregating results into final report' },
];

function ProgressSteps({ currentStage }: { currentStage: string }) {
  const currentIdx = STAGES.findIndex(s => s.key === currentStage);

  return (
    <div style={{ maxWidth: 400, margin: '0 auto' }}>
      {STAGES.map((s, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        const pending = i > currentIdx;

        return (
          <div key={s.key} style={{ display: 'flex', gap: SPACE.sm + 4, alignItems: 'flex-start', marginBottom: i < STAGES.length - 1 ? SPACE.md : 0 }}>
            <div style={{
              width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
              background: done ? SUCCESS : active ? PRIMARY : INPUT_BG,
              border: pending ? `2px solid ${INPUT_BORDER}` : 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, color: done || active ? TEXT_WHITE : TEXT_DIM,
              transition: 'all 0.3s ease',
            }}>
              {done ? '\u2713' : active ? '\u25CF' : i + 1}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{
                ...TYPO['body-lg'], fontWeight: active ? 600 : 400,
                color: active ? TEXT_WHITE : done ? TEXT_MUTED : TEXT_DIM,
                transition: 'color 0.3s ease',
              }}>
                {s.label}
              </div>
              {active && (
                <div style={{ ...TYPO['body-sm'], color: PRIMARY, marginTop: SPACE.xs / 2 }}>
                  {s.desc}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CheckProgressBars({ progress, labels }: { progress: any; labels: Record<string, string> }) {
  if (!progress) return null;
  const { completed, pending, current } = progress;
  const all = [...completed, ...pending];
  const done = completed.length;
  const total = all.length;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div style={{ maxWidth: 360, margin: '20px auto 0' }}>
      <div style={{ ...TYPO['body-sm'], color: TEXT_MUTED, marginBottom: SPACE.xs + 2 }}>
        Checks: {done}/{total} ({pct}%)
      </div>
      <div style={{ height: 4, background: INPUT_BG, borderRadius: 2, marginBottom: SPACE.sm + 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          background: PRIMARY, borderRadius: 2,
          transition: 'width 0.3s ease',
        }} />
      </div>
      {all.map((name: string) => {
        const isDone = completed.includes(name);
        const isCurrent = name === current;
        const label = labels[name] || name.replace(/_/g, ' ');
        return (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm, marginBottom: SPACE.xs, fontSize: 12 }}>
            <span style={{
              width: 16, height: 16, borderRadius: '50%', flexShrink: 0,
              background: isDone ? SUCCESS : isCurrent ? PRIMARY : INPUT_BG,
              border: !isDone && !isCurrent ? `1.5px solid ${INPUT_BORDER}` : 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 9, color: TEXT_WHITE,
            }}>
              {isDone ? '\u2713' : isCurrent ? '\u25CF' : ''}
            </span>
            <span style={{
              color: isCurrent ? TEXT_WHITE : isDone ? SUCCESS : TEXT_MUTED,
              fontWeight: isCurrent ? 500 : 400,
            }}>
              {label}
              {isCurrent && <span style={{ color: PRIMARY, marginLeft: SPACE.xs + 2, fontSize: 10 }}>running...</span>}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function AnalyzePage() {
  const { submit, reset, result, status, stage, checkProgress, CHECK_LABELS, error } = useAnalysis();
  const { isMobile } = useMediaQuery();

  return (
    <div>
      {status === 'idle' && <UrlInput onSubmit={submit} />}
      {status === 'loading' && (
        <div style={{ textAlign: 'center', padding: isMobile ? 30 : 60 }}>
          <div style={{ ...TYPO.h2, marginBottom: SPACE.sm }} data-mobile-h1>Submitting...</div>
          <div style={{ color: TEXT_MUTED }}>Validating URL and starting analysis</div>
          <ElapsedTimer running={true} />
        </div>
      )}
      {status === 'polling' && (
        <div style={{ textAlign: 'center', padding: isMobile ? '30px 14px' : '60px 20px' }}>
          <div style={{ ...TYPO.h2, marginBottom: SPACE.lg, fontWeight: 600 }} data-mobile-h1>
            Analyzing Submission
          </div>
          <ProgressSteps currentStage={stage} />
          {stage === 'checking' && <CheckProgressBars progress={checkProgress} labels={CHECK_LABELS} />}
          <ElapsedTimer running={true} />
        </div>
      )}
      {status === 'error' && (
        <div style={{ textAlign: 'center', padding: isMobile ? 30 : 60 }}>
          <div style={{ color: ERROR_TEXT, marginBottom: SPACE.md }}>{error}</div>
          <Button onClick={reset}>Try Again</Button>
        </div>
      )}
      {status === 'done' && result && (() => {
        const checks = (result.check_results || []);
        const cats = groupByCategory(checks);
        return (
          <div>
            <ReportCard
              projectTitle={result.project_title || undefined}
              riskScore={result.risk_score ?? 0}
              verdict={result.verdict ?? 'unknown'}
              categories={cats}
              checks={checks}
            />

            {/* Drill down */}
            <details style={{ marginTop: SPACE.sm }}>
              <summary style={{
                cursor: 'pointer', padding: `${SPACE.sm + 4}px ${SPACE.md}px`,
                background: CARD_BG, border: `1px solid ${BORDER}`,
                borderRadius: RADIUS.md + 2, ...TYPO['label-caps'],
                textTransform: 'uppercase', color: TEXT_MUTED, fontWeight: 600,
              }}>
                Drill Down — All {checks.length} Checks
              </summary>
              <div style={{ marginTop: SPACE.sm }}>
                {checks.map(cr => (
                  <CheckResultRow key={cr.check_name} check={cr} />
                ))}
              </div>
            </details>

            <div style={{ display: 'flex', justifyContent: 'center', gap: SPACE.sm + 4, marginTop: 20 }}>
              <Link to={`/report/${result.id}`} style={{ ...TYPO['body-sm'], color: PRIMARY, textDecoration: 'none' }}>
                Full Report
              </Link>
              <Button variant="secondary" onClick={reset} style={{ fontSize: 13 }}>
                New Check
              </Button>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
