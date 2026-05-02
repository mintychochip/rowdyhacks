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

  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return (
    <div style={{ ...TYPO['body-sm'], color: TEXT_DIM, marginTop: SPACE.md }}>
      Elapsed: {mins}:{secs.toString().padStart(2, '0')}
    </div>
  );
}

function AnalysisProgress({ stage, checkProgress, labels, hasGithub }: {
  stage: string;
  checkProgress: { completed: string[]; pending: string[]; current: string | null } | null;
  labels: Record<string, string>;
  hasGithub: boolean;
}) {
  const stageLabel: Record<string, string> = {
    scraping: 'Scraping Devpost page',
    cloning: hasGithub ? 'Downloading source code' : 'Preparing analysis',
    checking: 'Running integrity checks',
    scoring: 'Computing final report',
  };

  const stageDesc: Record<string, string> = {
    scraping: 'Extracting project info, tech stack, and team members',
    cloning: hasGithub ? 'Cloning repository for analysis' : 'No GitHub repo found — skipping',
    checking: '',
    scoring: 'Aggregating all results into your report',
  };

  const totalChecks = checkProgress ? checkProgress.completed.length + checkProgress.pending.length : 13;
  const doneChecks = checkProgress ? checkProgress.completed.length : 0;

  // Progress bar: 0-8% scraping, 8-15% cloning, 15-95% per-check, 95-100% scoring
  const pct = (() => {
    if (stage === 'scraping') return doneChecks > 0 ? 8 : 3;
    if (stage === 'cloning') return hasGithub ? 12 : 15;
    if (stage === 'scoring') return 97;
    if (stage === 'checking') {
      const base = hasGithub ? 15 : 18;
      const range = 80; // 15% to 95%
      return base + (doneChecks / Math.max(totalChecks, 1)) * range;
    }
    return 0;
  })();

  return (
    <div style={{ maxWidth: 500, margin: '0 auto' }}>
      {/* Main progress bar */}
      <div style={{
        height: 6, background: INPUT_BG, borderRadius: 3, overflow: 'hidden', marginBottom: SPACE.md,
      }}>
        <div style={{
          height: '100%',
          width: `${Math.round(pct)}%`,
          background: `linear-gradient(90deg, ${PRIMARY}, #a78bfa)`,
          borderRadius: 3,
          transition: 'width 0.6s ease',
        }} />
      </div>

      {/* Current stage */}
      <div style={{ textAlign: 'center', marginBottom: SPACE.xs }}>
        <span style={{
          ...TYPO['body-lg'], fontWeight: 600, color: TEXT_WHITE,
        }}>
          {stageLabel[stage] || 'Analyzing...'}
        </span>
      </div>
      {stageDesc[stage] && (
        <div style={{ ...TYPO['body-sm'], color: TEXT_MUTED, textAlign: 'center', marginBottom: SPACE.md }}>
          {stageDesc[stage]}
        </div>
      )}

      {/* Check progress — show whenever we have check data */}
      {checkProgress && (
        <div style={{ marginTop: SPACE.lg }}>
          <div style={{ ...TYPO['body-sm'], color: TEXT_MUTED, marginBottom: SPACE.sm, textAlign: 'center' }}>
            {doneChecks}/{totalChecks} checks complete
          </div>

          {/* Completed checks scrolling in */}
          <div style={{
            maxHeight: 200, overflow: 'hidden',
            maskImage: 'linear-gradient(to bottom, black 60%, transparent 100%)',
          }}>
            {checkProgress.completed.map((name: string) => (
              <div key={name} style={{
                display: 'flex', alignItems: 'center', gap: SPACE.sm,
                padding: '4px 0', fontSize: 12,
                animation: 'slideDown 0.3s ease',
              }}>
                <span style={{
                  width: 16, height: 16, borderRadius: '50%', flexShrink: 0,
                  background: SUCCESS, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 9, color: TEXT_WHITE,
                }}>{'\u2713'}</span>
                <span style={{ color: SUCCESS }}>{labels[name] || name.replace(/_/g, ' ')}</span>
              </div>
            ))}
          </div>

          {/* Current check */}
          {checkProgress.current && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: SPACE.sm,
              padding: '8px 0', fontSize: 13, fontWeight: 500,
            }}>
              <div style={{
                width: 16, height: 16, borderRadius: '50%', flexShrink: 0,
                background: PRIMARY, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 9, color: TEXT_WHITE,
                animation: 'pulse 1.5s infinite',
              }}>{'\u25CF'}</div>
              <span style={{ color: TEXT_WHITE }}>
                {labels[checkProgress.current] || checkProgress.current.replace(/_/g, ' ')}
              </span>
              <span style={{ color: PRIMARY, fontSize: 10 }}>running...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AnalyzePage() {
  const { submit, reset, result, status, stage, checkProgress, CHECK_LABELS, error, hasGithub } = useAnalysis();
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
          <AnalysisProgress
            stage={stage}
            checkProgress={checkProgress}
            labels={CHECK_LABELS}
            hasGithub={hasGithub}
          />
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
