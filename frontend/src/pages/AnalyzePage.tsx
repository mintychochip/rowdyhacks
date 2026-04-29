import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import UrlInput from '../components/UrlInput';
import ReportCard from '../components/ReportCard';
import CheckResultRow from '../components/CheckResultRow';
import { useAnalysis } from '../hooks/useAnalysis';
import { PRIMARY, PRIMARY_DISABLED, SUCCESS, ERROR_TEXT, TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, TEXT_WHITE, INPUT_BG, INPUT_BORDER, BORDER, CARD_BG } from '../theme';

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
    <div style={{ fontSize: 13, color: TEXT_DIM, marginTop: 16 }}>
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
          <div key={s.key} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: i < STAGES.length - 1 ? 16 : 0 }}>
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
                fontSize: 14, fontWeight: active ? 600 : 400,
                color: active ? TEXT_WHITE : done ? TEXT_MUTED : TEXT_DIM,
                transition: 'color 0.3s ease',
              }}>
                {s.label}
              </div>
              {active && (
                <div style={{ fontSize: 12, color: PRIMARY, marginTop: 2 }}>{s.desc}</div>
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
      <div style={{ fontSize: 12, color: '#808090', marginBottom: 6 }}>
        Checks: {done}/{total} ({pct}%)
      </div>
      <div style={{ height: 4, background: '#1a1a2e', borderRadius: 2, marginBottom: 12, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: '#6c5ce7', borderRadius: 2, transition: 'width 0.3s ease' }} />
      </div>
      {all.map((name: string) => {
        const isDone = completed.includes(name);
        const isCurrent = name === current;
        const label = labels[name] || name.replace(/_/g, ' ');
        return (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, fontSize: 12 }}>
            <span style={{
              width: 16, height: 16, borderRadius: '50%', flexShrink: 0,
              background: isDone ? '#00c853' : isCurrent ? '#6c5ce7' : '#1a1a2e',
              border: !isDone && !isCurrent ? '1.5px solid #333' : 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 9, color: '#fff',
            }}>
              {isDone ? '\u2713' : isCurrent ? '\u25CF' : ''}
            </span>
            <span style={{
              color: isCurrent ? '#fff' : isDone ? '#00c853' : '#555',
              fontWeight: isCurrent ? 500 : 400,
            }}>
              {label}
              {isCurrent && <span style={{ color: '#6c5ce7', marginLeft: 6, fontSize: 10 }}>running...</span>}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function AnalyzePage() {
  const { submit, reset, result, status, stage, checkProgress, CHECK_LABELS, error } = useAnalysis();

  return (
    <div>
      {status === 'idle' && <UrlInput onSubmit={submit} />}
      {status === 'loading' && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 18, marginBottom: 8 }}>Submitting...</div>
          <div style={{ color: TEXT_MUTED }}>Validating URL and starting analysis</div>
          <ElapsedTimer running={true} />
        </div>
      )}
      {status === 'polling' && (
        <div style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div style={{ fontSize: 18, marginBottom: 24, fontWeight: 600 }}>Analyzing Submission</div>
          <ProgressSteps currentStage={stage} />
          {stage === 'checking' && <CheckProgressBars progress={checkProgress} labels={CHECK_LABELS} />}
          <ElapsedTimer running={true} />
        </div>
      )}
      {status === 'error' && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ color: ERROR_TEXT, marginBottom: 16 }}>{error}</div>
          <button onClick={reset} style={{ padding: '10px 20px', background: PRIMARY, border: 'none', borderRadius: 8, color: TEXT_WHITE, cursor: 'pointer' }}>Try Again</button>
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
            <details style={{ marginTop: 8 }}>
              <summary style={{
                cursor: 'pointer', padding: '12px 16px', background: CARD_BG,
                border: `1px solid ${BORDER}`, borderRadius: 10, fontSize: 13,
                color: TEXT_MUTED, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1,
              }}>
                Drill Down — All {checks.length} Checks
              </summary>
              <div style={{ marginTop: 8 }}>
                {checks.map(cr => (
                  <CheckResultRow key={cr.check_name} check={cr} />
                ))}
              </div>
            </details>

            <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 20 }}>
              <Link to={`/report/${result.id}`} style={{ color: PRIMARY, textDecoration: 'none', fontSize: 13 }}>Full Report</Link>
              <button onClick={reset} style={{ background: 'none', border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, padding: '4px 12px', color: TEXT_MUTED, cursor: 'pointer', fontSize: 13 }}>New Check</button>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
