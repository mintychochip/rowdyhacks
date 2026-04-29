import ScoreCircle from './ScoreCircle';
import { SUCCESS, WARNING, ERROR, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, CARD_BG, BORDER, INPUT_BG } from '../theme';

interface CheckSummary {
  check_name: string;
  check_category: string;
  score: number;
  status: string;
  details: Record<string, any>;
  evidence: string[];
}

interface Props {
  projectTitle?: string;
  riskScore: number;
  verdict: string;
  categories: Array<{ category: string; score: number }>;
  checks?: CheckSummary[];
}

function verdictLabel(v: string) {
  if (v === 'clean') return 'Clean';
  if (v === 'flagged') return 'Flagged';
  return 'Needs Review';
}

function verdictColor(v: string) {
  if (v === 'clean') return SUCCESS;
  if (v === 'flagged') return ERROR;
  return WARNING;
}

function generateNarrative(checks: CheckSummary[], riskScore: number, verdict: string): string {
  if (!checks || checks.length === 0) return '';
  const fails = checks.filter(c => c.status === 'fail');
  const warns = checks.filter(c => c.status === 'warn');
  const passes = checks.filter(c => c.status === 'pass' || c.status === 'pass_');

  if (fails.length === 0 && warns.length === 0) {
    return `All ${checks.length} integrity checks passed. This submission shows no signs of cheating — the code matches the Devpost claims, commits are within expected timeframes, and no suspicious patterns were detected.`;
  }

  const parts: string[] = [];
  if (fails.length > 0) {
    const names = fails.map(c => c.check_name.replace(/-/g, ' ')).join(', ');
    parts.push(`${fails.length} critical issue${fails.length > 1 ? 's' : ''} found: ${names}.`);
  }
  if (warns.length > 0) {
    const names = warns.map(c => c.check_name.replace(/-/g, ' ')).join(', ');
    parts.push(`${warns.length} warning${warns.length > 1 ? 's' : ''} to review: ${names}.`);
  }
  parts.push(`${passes.length} checks passed cleanly.`);
  return parts.join(' ');
}

function severityBadge(score: number) {
  if (score >= 60) return { label: 'High', color: ERROR, bg: '#ff444418' };
  if (score >= 30) return { label: 'Medium', color: WARNING, bg: '#ffc10718' };
  return { label: 'Low', color: SUCCESS, bg: '#00c85318' };
}

export default function ReportCard({ projectTitle, riskScore, verdict, categories, checks }: Props) {
  const narrative = generateNarrative(checks || [], riskScore, verdict);
  const vColor = verdictColor(verdict);

  // Group key findings: show fails first, then warns
  const keyFindings = (checks || [])
    .filter(c => c.status === 'fail' || c.status === 'warn')
    .sort((a, b) => b.score - a.score);

  return (
    <div>
      {/* Hero */}
      <div style={{ textAlign: 'center', padding: '40px 20px 32px' }}>
        <ScoreCircle score={riskScore} verdict={verdict} size={180} />
        {projectTitle && (
          <h2 style={{ fontSize: 26, fontWeight: 700, marginTop: 20, marginBottom: 4 }}>
            {projectTitle}
          </h2>
        )}
        <div style={{
          display: 'inline-block', padding: '4px 16px', borderRadius: 20, fontSize: 14, fontWeight: 600,
          background: vColor + '18', color: vColor, marginTop: 8,
        }}>
          {verdictLabel(verdict)}
        </div>

        {/* Narrative */}
        {narrative && (
          <p style={{ maxWidth: 600, margin: '20px auto 0', fontSize: 14, color: TEXT_SECONDARY, lineHeight: 1.6 }}>
            {narrative}
          </p>
        )}
      </div>

      {/* Key Findings */}
      {keyFindings.length > 0 && (
        <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24, marginBottom: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, textTransform: 'uppercase', letterSpacing: 1, color: TEXT_MUTED }}>
            Key Findings
          </div>
          {keyFindings.map((check, i) => {
            const sev = severityBadge(check.score);
            const detail = check.details;
            // Extract a human-readable summary from the details
            const summary = detail?.overall_assessment
              || detail?.reason
              || (check.evidence && check.evidence[0])
              || 'No details available';

            return (
              <div key={check.check_name} style={{
                display: 'flex', gap: 16, alignItems: 'flex-start',
                padding: '14px 0', borderBottom: i < keyFindings.length - 1 ? `1px solid ${BORDER}` : 'none',
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                  background: sev.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 18, fontWeight: 700, color: sev.color,
                }}>
                  {check.score}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, textTransform: 'capitalize' }}>
                      {check.check_name.replace(/-/g, ' ')}
                    </span>
                    <span style={{
                      fontSize: 10, padding: '2px 8px', borderRadius: 10, fontWeight: 600,
                      background: sev.bg, color: sev.color,
                    }}>
                      {sev.label}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: TEXT_MUTED, lineHeight: 1.5 }}>
                    {typeof summary === 'string' ? summary.slice(0, 200) : JSON.stringify(summary).slice(0, 200)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Category Breakdown */}
      <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 24 }}>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, textTransform: 'uppercase', letterSpacing: 1, color: TEXT_MUTED }}>
          Category Breakdown
        </div>
        {categories.map(cat => (
          <div key={cat.category} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
            <span style={{ fontSize: 13, color: TEXT_SECONDARY, width: 150, textTransform: 'capitalize' }}>
              {cat.category.replace(/_/g, ' ')}
            </span>
            <div style={{ flex: 1, height: 6, background: INPUT_BG, borderRadius: 3, overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${Math.max(cat.score, 4)}%`,
                background: cat.score <= 30 ? SUCCESS : cat.score <= 60 ? WARNING : ERROR,
                borderRadius: 3, transition: 'width 0.8s ease',
              }} />
            </div>
            <span style={{ fontSize: 12, color: TEXT_SECONDARY, minWidth: 24, textAlign: 'right', fontWeight: 600 }}>
              {cat.score}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
