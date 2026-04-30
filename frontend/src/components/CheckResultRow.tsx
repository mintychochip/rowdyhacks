import { useState } from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { PRIMARY, SUCCESS, WARNING, ERROR, ORANGE, TEXT_SECONDARY, TEXT_MUTED, BORDER, EXPANDED_BG, CARD_BG, TYPO, SPACE, RADIUS } from '../theme';
import { Badge } from './Primitives';
import { renderCheckDetails } from './CheckDetails';

function renderEvidence(text: string) {
  const urlMatch = text.match(/^(https:\/\/github\.com\/[^\s]+)/);
  if (urlMatch) {
    const url = urlMatch[1];
    return <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: PRIMARY, textDecoration: 'none', wordBreak: 'break-all' }}>{url}</a>;
  }
  return <span style={{ color: TEXT_SECONDARY }}>{text}</span>;
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
  const { isMobile } = useMediaQuery();
  const [expanded, setExpanded] = useState(false);
  const sColor = statusColor(check.status);

  return (
    <div style={{ border: `1px solid ${BORDER}`, borderRadius: RADIUS.md, marginBottom: SPACE.sm, overflow: 'hidden' }}>
      <div onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: isMobile ? '14px 12px' : `${SPACE.sm + 4}px ${SPACE.md}px`, cursor: 'pointer', background: CARD_BG,
        }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm + 4 }}>
          <span style={{ color: sColor, fontSize: 18 }}>{statusIcon(check.status)}</span>
          <div>
            <div style={{ ...TYPO['body-lg'], fontWeight: 600 }}>{check.check_name}</div>
            <div style={{ ...TYPO['body-sm'], color: TEXT_MUTED, textTransform: 'capitalize' }}>
              {check.check_category.replace(/_/g, ' ')}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm + 4 }}>
          <Badge color={sColor}>
            {check.status === 'pass_' ? 'pass' : check.status}
          </Badge>
          <span style={{
            fontSize: 18, fontWeight: 700, color: sColor,
            minWidth: 36, textAlign: 'right',
          }}>
            {check.score}
          </span>
        </div>
      </div>
      {expanded && (
        <div style={{ padding: SPACE.md, background: EXPANDED_BG, borderTop: `1px solid ${BORDER}` }}>
          {renderCheckDetails(check.check_name, check.details)}
          {check.evidence && check.evidence.length > 0 && (
            <div>
              <div style={{ ...TYPO['body-sm'], color: TEXT_MUTED, marginBottom: SPACE.xs }}>Evidence</div>
              {check.evidence.map((e, i) => (
                <div key={i} style={{ ...TYPO['body-sm'], marginBottom: SPACE.xs }}>
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
