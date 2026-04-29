import React, { useState } from 'react';
import { PRIMARY, SUCCESS, WARNING, WARNING_BG10, WARNING_BORDER30, ERROR, ERROR_TEXT, ERROR_BG10, ERROR_BORDER30, ORANGE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, INPUT_BG, BORDER, EXPANDED_BG, CARD_BG } from '../theme';

function isAlignmentCheck(check: CheckResult): boolean {
  return check.check_name === 'claimed-vs-actual-tech' && check.details?.verified;
}

function isContributorAudit(check: CheckResult): boolean {
  return check.check_name === 'contributor-audit' && check.details?.repo_authors;
}

const COLORS = [PRIMARY, SUCCESS, WARNING, '#00bcd4', '#e040fb', '#ff6d00', '#2196f3', '#4caf50'];

function ContributorAuditDetails({ details }: { details: Record<string, any> }) {
  const pcts: Record<string, number> = details.commit_percentages || {};
  const authors = details.repo_authors || [];
  const teamNames = details.team_names || [];
  const teamGithubs = details.team_githubs || [];
  const ghosts = details.ghost_contributors || [];
  const mia = details.mia_members || [];

  // Assign each team member a commit count (best effort matching)
  const memberContribution = (name: string) => {
    const parts = name.split(' ');
    for (const author of authors) {
      const aParts = author.split(' ');
      if (parts.some(p => aParts.includes(p)) || aParts.some(p => parts.includes(p))) {
        return pcts[author] || 0;
      }
    }
    for (const gh of teamGithubs) {
      for (const author of authors) {
        if (author.includes(gh) || gh.includes(author)) {
          return pcts[author] || 0;
        }
      }
    }
    return 0;
  };

  // Unmatched repo authors (ghosts)
  const unmatchedAuthors = authors.filter(a => {
    return !teamNames.some(name => {
      const parts = name.split(' ');
      const aParts = a.split(' ');
      return parts.some(p => aParts.includes(p)) || aParts.some(p => parts.includes(p));
    }) && !teamGithubs.some(gh => a.includes(gh));
  });

  // Build pie segments
  const segments: { label: string; pct: number; color: string }[] = [];
  let colorIdx = 0;
  for (const name of teamNames) {
    const pct = memberContribution(name);
    if (pct > 0) {
      segments.push({ label: name, pct, color: COLORS[colorIdx % COLORS.length] });
      colorIdx++;
    }
  }
  for (const author of unmatchedAuthors) {
    const pct = pcts[author] || 0;
    if (pct > 0) {
      segments.push({ label: `${author} (ghost)`, pct, color: ERROR });
    }
  }
  // Sort by pct descending
  segments.sort((a, b) => b.pct - a.pct);

  // SVG donut
  const size = 160;
  const cx = size / 2, cy = size / 2;
  const radius = 60;
  const strokeWidth = 18;
  const circ = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div>
      {/* Donut chart */}
      <div style={{ textAlign: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 8, fontWeight: 600 }}>
          Commits ({details.total_commits} total, {details.repos_analyzed || 1} repo{details.repos_analyzed > 1 ? 's' : ''})
        </div>
        <div style={{ display: 'inline-block', position: 'relative' }}>
          <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
            {segments.map((seg, i) => {
              const len = (seg.pct / 100) * circ;
              const dashArray = `${len} ${circ - len}`;
              const segEl = (
                <circle key={i} cx={cx} cy={cy} r={radius} fill="none" stroke={seg.color}
                  strokeWidth={strokeWidth} strokeDasharray={dashArray} strokeDashoffset={-offset}
                  transform={`rotate(-90 ${cx} ${cy})`}
                  style={{ transition: 'stroke-dashoffset 0.8s ease' }} />
              );
              offset += len;
              return segEl;
            })}
            {/* Center text */}
            <text x={cx} y={cy - 8} textAnchor="middle" fill="#fff" fontSize={24} fontWeight={700}>
              {segments.length > 0 ? `${segments[0].pct}%` : '—'}
            </text>
            <text x={cx} y={cy + 12} textAnchor="middle" fill={TEXT_MUTED} fontSize={11}>
              top contributor
            </text>
          </svg>
        </div>
      </div>

      {/* Legend */}
      <div style={{ marginBottom: 16 }}>
        {segments.map((seg, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: seg.color, flexShrink: 0 }} />
            <span style={{ color: TEXT_PRIMARY, flex: 1 }}>{seg.label}</span>
            <span style={{ color: TEXT_MUTED, fontWeight: 600 }}>{seg.pct}%</span>
          </div>
        ))}
      </div>

      {/* Zero-commit members */}
      {mia.length > 0 && (
        <div style={{ marginBottom: 12, fontSize: 11, color: ERROR_TEXT }}>
          No commits: {mia.join(', ')}
        </div>
      )}

      {/* GitHub links */}
      {teamGithubs.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 6, fontWeight: 600 }}>Linked GitHub Profiles</div>
          {teamGithubs.map((gh: string) => (
            <a key={gh} href={`https://github.com/${gh}`} target="_blank" rel="noopener noreferrer"
              style={{ display: 'inline-block', color: PRIMARY, marginRight: 12, fontSize: 12, textDecoration: 'none' }}>
              @{gh} →
            </a>
          ))}
        </div>
      )}

      {/* Alerts */}
      {details.sole_contributor && (
        <div style={{ background: ERROR_BG10, border: `1px solid ${ERROR_BORDER30}`, borderRadius: 6, padding: 10, fontSize: 12, color: ERROR_TEXT, marginBottom: 8 }}>
          Only {Object.keys(pcts)[0]} committed — but Devpost lists {teamNames.length} team members
        </div>
      )}
      {mia.length > 0 && (
        <div style={{ background: WARNING_BG10, border: `1px solid ${WARNING_BORDER30}`, borderRadius: 6, padding: 10, fontSize: 12, color: WARNING }}>
          {mia.length} team member{mia.length > 1 ? 's' : ''} with no matching commits: {mia.join(', ')}
        </div>
      )}
    </div>
  );
}

function renderEvidence(text: string) {
  const urlMatch = text.match(/^(https:\/\/github\.com\/[^\s]+)/);
  if (urlMatch) {
    const url = urlMatch[1];
    return <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: PRIMARY, textDecoration: 'none', wordBreak: 'break-all' }}>{url}</a>;
  }
  return <span style={{ color: TEXT_SECONDARY }}>{text}</span>;
}

function AlignmentDetails({ details }: { details: Record<string, any> }) {
  return (
    <div>
      {details.overall_assessment && (
        <p style={{ fontSize: 13, color: TEXT_SECONDARY, marginBottom: 16, lineHeight: 1.5 }}>{details.overall_assessment}</p>
      )}
      {details.verified && details.verified.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: SUCCESS, marginBottom: 8, fontWeight: 600 }}>
            Verified ({details.verified_count})
          </div>
          {details.verified.map((v: any, i: number) => (
            <div key={i} style={{ marginBottom: 8, paddingLeft: 12, borderLeft: `2px solid ${SUCCESS}` }}>
              <div style={{ fontSize: 13, color: TEXT_PRIMARY, fontWeight: 500 }}>{v.claim}</div>
              <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 2 }}>{v.explanation}</div>
              {(v.evidence || []).map((e: string, j: number) => (
                <div key={j} style={{ fontSize: 11, marginTop: 2 }}>
                  <a href={extractUrl(e)} target="_blank" rel="noopener noreferrer" style={{ color: PRIMARY, textDecoration: 'none', wordBreak: 'break-all' }}>
                    {e}
                  </a>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
      {details.missing && details.missing.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: ERROR, marginBottom: 8, fontWeight: 600 }}>
            Missing ({details.missing_count})
          </div>
          {details.missing.map((m: any, i: number) => (
            <div key={i} style={{ marginBottom: 6, paddingLeft: 12, borderLeft: `2px solid ${ERROR}` }}>
              <div style={{ fontSize: 13, color: TEXT_PRIMARY, fontWeight: 500 }}>{m.claim}</div>
              <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 2 }}>{m.explanation}</div>
            </div>
          ))}
        </div>
      )}
      {details.unclear && details.unclear.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: WARNING, marginBottom: 8, fontWeight: 600 }}>
            Unclear ({details.unclear_count})
          </div>
          {details.unclear.map((u: any, i: number) => (
            <div key={i} style={{ marginBottom: 6, paddingLeft: 12, borderLeft: `2px solid ${WARNING}` }}>
              <div style={{ fontSize: 13, color: TEXT_PRIMARY, fontWeight: 500 }}>{u.claim}</div>
              <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 2 }}>{u.explanation}</div>
            </div>
          ))}
        </div>
      )}
      {details.suspicious_patterns && details.suspicious_patterns.length > 0 && (
        <div style={{ padding: 10, background: ERROR_BG10, border: `1px solid ${ERROR_BORDER30}`, borderRadius: 6 }}>
          <div style={{ fontSize: 12, color: ERROR, fontWeight: 600, marginBottom: 4 }}>Suspicious Patterns</div>
          {details.suspicious_patterns.map((s: string, i: number) => (
            <div key={i} style={{ fontSize: 11, color: ERROR_TEXT }}>{s}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function extractUrl(text: string): string {
  const m = text.match(/^(https:\/\/github\.com\/[^\s]+)/);
  return m ? m[1] : '#';
}

interface CheckResult {
  check_name: string;
  check_category: string;
  score: number;
  status: string;
  details: Record<string, any>;
  evidence: string[];
}

function statusIcon(status: string): string {
  if (status === 'pass' || status === 'pass_') return '\u2713';
  if (status === 'warn') return '\u26A0';
  if (status === 'fail') return '\u2717';
  if (status === 'error') return '\u26A1';
  return '?';
}

function statusColor(status: string): string {
  if (status === 'pass' || status === 'pass_') return SUCCESS;
  if (status === 'warn') return WARNING;
  if (status === 'fail') return ERROR;
  if (status === 'error') return ORANGE;
  return '#888';
}

export default function CheckResultRow({ check }: { check: CheckResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, marginBottom: 8, overflow: 'hidden' }}>
      <div onClick={() => setExpanded(!expanded)}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', cursor: 'pointer', background: CARD_BG }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: statusColor(check.status), fontSize: 18 }}>{statusIcon(check.status)}</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{check.check_name}</div>
            <div style={{ fontSize: 11, color: TEXT_MUTED, textTransform: 'capitalize' }}>{check.check_category.replace('_', ' ')}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            background: statusColor(check.status) + '20', color: statusColor(check.status),
            padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600
          }}>
            {check.status === 'pass_' ? 'pass' : check.status}
          </span>
          <span style={{ fontSize: 18, fontWeight: 700, color: statusColor(check.status), minWidth: 36, textAlign: 'right' }}>{check.score}</span>
        </div>
      </div>
      {expanded && (
        <div style={{ padding: 16, background: EXPANDED_BG, borderTop: `1px solid ${BORDER}` }}>
          {isAlignmentCheck(check) ? (
            <AlignmentDetails details={check.details} />
          ) : isContributorAudit(check) ? (
            <ContributorAuditDetails details={check.details} />
          ) : Object.keys(check.details).length > 0 ? (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Details</div>
              <pre style={{ fontSize: 12, color: TEXT_SECONDARY, whiteSpace: 'pre-wrap', background: CARD_BG, padding: 12, borderRadius: 6 }}>
                {JSON.stringify(check.details, null, 2)}
              </pre>
            </div>
          ) : null}
          {check.evidence && check.evidence.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Evidence</div>
              {check.evidence.map((e, i) => (
                <div key={i} style={{ fontSize: 12, marginBottom: 4 }}>
                  {renderEvidence(e)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
