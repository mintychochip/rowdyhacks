import React, { ReactNode } from 'react';
import {
  PRIMARY, SUCCESS, WARNING, WARNING_BG10, WARNING_BORDER30,
  ERROR, ERROR_TEXT, ERROR_BG10, ERROR_BORDER30, ORANGE,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, INPUT_BG,
  BORDER, CARD_BG, INFO, INFO_BG20, SUCCESS_BG10,
} from '../theme';

// ── shared helpers ──────────────────────────────────────────────

function ErrorReason({ reason }: { reason: string }) {
  return (
    <div style={{ background: ERROR_BG10, border: `1px solid ${ERROR_BORDER30}`, borderRadius: 6, padding: 10, fontSize: 12, color: ERROR_TEXT }}>
      {reason}
    </div>
  );
}

function MiniBar({ pct, color = WARNING }: { pct: number; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 8, background: INPUT_BG, borderRadius: 4, overflow: 'hidden' }}>
        <div style={{ width: `${Math.min(pct, 100)}%`, height: '100%', background: color, borderRadius: 4, transition: 'width 0.4s ease' }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color, minWidth: 32, textAlign: 'right' }}>{pct}%</span>
    </div>
  );
}

function StatRow({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: `1px solid ${BORDER}` }}>
      <span style={{ fontSize: 12, color: TEXT_MUTED }}>{label}</span>
      <span style={{ fontSize: 12, fontWeight: 600, color: color || TEXT_PRIMARY }}>{value}</span>
    </div>
  );
}

function Badge({ children, color, bg }: { children: ReactNode; color: string; bg?: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
      color, background: bg || (color + '20'),
    }}>{children}</span>
  );
}

function Chip({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 500,
      color, background: color + '20', marginRight: 4, marginBottom: 4,
    }}>{label}</span>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 8, fontWeight: 600 }}>{children}</div>;
}

// ── detail components ───────────────────────────────────────────

function RepoAgeDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
        <StatRow label="Created" value={details.repo_created?.slice(0, 10)} />
        <StatRow label="Age" value={`${details.age_days} days`} color={details.age_days < 30 ? ERROR : SUCCESS} />
        <StatRow label="Stars" value={details.stars} />
        <StatRow label="Forks" value={details.forks} />
        <StatRow label="Open Issues" value={details.open_issues} />
        <StatRow label="Default Branch" value={details.default_branch} />
        {details.hackathon_start && (
          <StatRow label="Hackathon Start" value={details.hackathon_start?.slice(0, 10)} />
        )}
      </div>
      {details.is_fork && details.forked_from && (
        <div style={{ marginTop: 10, padding: 8, background: WARNING_BG10, border: `1px solid ${WARNING_BORDER30}`, borderRadius: 6, fontSize: 12, color: WARNING }}>
          Fork of: {details.forked_from}
        </div>
      )}
    </div>
  );
}

function CommitTimelineDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  if (details.no_commits) return <ErrorReason reason="No commits found in this repo." />;
  return (
    <div>
      {details.commits_before_start !== undefined && (
        <StatRow label="Commits before hackathon start" value={details.commits_before_start}
          color={details.commits_before_start > 0 ? WARNING : SUCCESS} />
      )}
      {details.single_commit && (
        <div style={{ background: ERROR_BG10, border: `1px solid ${ERROR_BORDER30}`, borderRadius: 6, padding: 8, fontSize: 12, color: ERROR_TEXT, marginBottom: 6 }}>
          Only 1 commit — likely built before the hackathon
        </div>
      )}
      {details.commit_burst && (
        <div style={{ background: WARNING_BG10, border: `1px solid ${WARNING_BORDER30}`, borderRadius: 6, padding: 8, fontSize: 12, color: WARNING, marginBottom: 6 }}>
          Commit burst detected — many commits in a short window
        </div>
      )}
      {details.suspicious_messages !== undefined && (
        <StatRow label="Suspicious messages" value={details.suspicious_messages}
          color={details.suspicious_messages > 0 ? ERROR : SUCCESS} />
      )}
    </div>
  );
}

function FileTimestampsDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const earlyFiles: any[] = details.early_files || [];
  return (
    <div>
      <StatRow label="Total files" value={details.total_files} />
      <div style={{ padding: '6px 0', borderBottom: `1px solid ${BORDER}` }}>
        <span style={{ fontSize: 12, color: TEXT_MUTED }}>Early files ({details.files_before_hackathon} / {details.total_files})</span>
        <div style={{ marginTop: 6 }}>
          <MiniBar pct={details.pct_early} color={details.pct_early > 50 ? ERROR : details.pct_early > 20 ? WARNING : SUCCESS} />
        </div>
      </div>
      {earlyFiles.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <SectionTitle>Early files (max 10 shown)</SectionTitle>
          <div style={{ maxHeight: 200, overflowY: 'auto', background: INPUT_BG, borderRadius: 6, padding: 8 }}>
            {earlyFiles.slice(0, 10).map((f: any, i: number) => (
              <div key={i} style={{ fontSize: 11, color: TEXT_SECONDARY, padding: '3px 0', display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ wordBreak: 'break-all' }}>{f.file}</span>
                <span style={{ color: TEXT_MUTED, marginLeft: 12, flexShrink: 0 }}>{f.date?.slice(0, 10)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CommitQualityDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const worst: string[] = details.worst_messages || [];
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
        <StatRow label="Total commits" value={details.total_commits} />
        <StatRow label="Suspicious %" value={`${details.pct_suspicious}%`}
          color={details.pct_suspicious > 50 ? ERROR : details.pct_suspicious > 20 ? WARNING : SUCCESS} />
        <StatRow label="Single-word msgs" value={details.single_word_count}
          color={details.single_word_count > 5 ? ERROR : undefined} />
        <StatRow label="Avg message len" value={details.avg_message_len} />
        <StatRow label="Conventional commits" value={details.conventional_commits}
          color={details.conventional_commits > 0 ? SUCCESS : undefined} />
      </div>
      {worst.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <SectionTitle>Worst commit messages</SectionTitle>
          <div style={{ maxHeight: 160, overflowY: 'auto', background: INPUT_BG, borderRadius: 6, padding: 8 }}>
            {worst.map((msg, i) => (
              <div key={i} style={{ fontSize: 11, color: TEXT_SECONDARY, padding: '3px 0', borderBottom: i < worst.length - 1 ? `1px solid ${BORDER}` : 'none' }}>
                {msg}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DeadDepsDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const missing: string[] = details.missing || [];
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
        <StatRow label="Declared" value={details.total_declared} />
        <StatRow label="Imported" value={details.imported} />
      </div>
      <div style={{ padding: '6px 0', borderBottom: `1px solid ${BORDER}` }}>
        <span style={{ fontSize: 12, color: TEXT_MUTED }}>Dead dependencies</span>
        <div style={{ marginTop: 6 }}>
          <MiniBar pct={details.pct_dead} color={details.pct_dead > 30 ? ERROR : WARNING} />
        </div>
      </div>
      {missing.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <SectionTitle>Missing ({missing.length})</SectionTitle>
          <div>
            {missing.map((dep: string) => (
              <Chip key={dep} label={dep} color={ERROR} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RepoIntegrityDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const forks: any[] = details.forks || [];
  const secretTypes: string[] = details.secret_types || [];
  const boilerplate = details.boilerplate_detected;
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
        <StatRow label="Total files" value={details.total_files} />
        <StatRow label="Secrets found" value={details.secrets_found}
          color={details.secrets_found > 0 ? ERROR : SUCCESS} />
      </div>
      {forks.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <SectionTitle>Forks ({forks.length})</SectionTitle>
          {forks.map((f: any, i: number) => (
            <div key={i} style={{ fontSize: 11, color: TEXT_SECONDARY, marginBottom: 4, padding: '4px 8px', background: INPUT_BG, borderRadius: 4 }}>
              <div style={{ wordBreak: 'break-all' }}>{f.upstream_url}</div>
              <div style={{ color: TEXT_MUTED, marginTop: 2 }}>{f.detection}</div>
            </div>
          ))}
        </div>
      )}
      {secretTypes.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <SectionTitle>Secret types</SectionTitle>
          <div>
            {secretTypes.map((t: string) => (
              <Chip key={t} label={t} color={ERROR} />
            ))}
          </div>
        </div>
      )}
      {boilerplate && Object.keys(boilerplate).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <SectionTitle>Boilerplate detected</SectionTitle>
          {Object.entries(boilerplate).map(([name, count]) => (
            <div key={name} style={{ fontSize: 11, color: TEXT_MUTED, marginBottom: 2 }}>
              {name}: {count as number} files
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AssetIntegrityDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const brokenLinks: any[] = details.broken_links || [];
  const missingAssets: string[] = details.missing_assets || [];
  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 10 }}>
        <Badge color={details.ai_disclosure ? SUCCESS : WARNING}
          bg={details.ai_disclosure ? SUCCESS_BG10 : WARNING_BG10}>
          AI disclosure: {details.ai_disclosure ? 'Found' : 'Not found'}
        </Badge>
        <span style={{ fontSize: 11, color: TEXT_MUTED, alignSelf: 'center' }}>
          YT check: {details.youtube_timestamp_check || 'n/a'}
        </span>
      </div>
      {missingAssets.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <SectionTitle>Missing assets</SectionTitle>
          <div>
            {missingAssets.map((a: string) => (
              <Chip key={a} label={a} color={WARNING} />
            ))}
          </div>
        </div>
      )}
      {brokenLinks.length > 0 && (
        <div>
          <SectionTitle>Broken links ({brokenLinks.length})</SectionTitle>
          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            {brokenLinks.map((l: any, i: number) => (
              <div key={i} style={{ fontSize: 11, padding: '6px 8px', borderBottom: `1px solid ${BORDER}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>
                  <Badge color={ERROR}>{l.name}</Badge>
                  <span style={{ color: TEXT_SECONDARY, marginLeft: 8, wordBreak: 'break-all' }}>{l.url}</span>
                </span>
                <span style={{ color: TEXT_MUTED, marginLeft: 12, flexShrink: 0 }}>{l.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BuildVerifyDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const results: any[] = details.results || [];
  return (
    <div>
      {results.map((r: any, i: number) => (
        <div key={i} style={{ marginBottom: i < results.length - 1 ? 10 : 0, padding: 10, background: INPUT_BG, borderRadius: 6, border: `1px solid ${BORDER}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: TEXT_PRIMARY }}>{r.repo}</span>
            {r.name && (
              <Badge color={INFO}>{r.name}</Badge>
            )}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
            <StatRow label="Install" value={
              r.install_success === null ? <span style={{ color: TEXT_MUTED }}>skipped</span> :
                r.install_success ? <span style={{ color: SUCCESS }}>pass ({r.install_time?.toFixed(1)}s)</span> :
                  <span style={{ color: ERROR }}>fail ({r.install_time?.toFixed(1)}s)</span>
            } />
            <StatRow label="Build" value={
              r.build_success === null ? <span style={{ color: TEXT_MUTED }}>skipped</span> :
                r.build_success ? <span style={{ color: SUCCESS }}>pass ({r.build_time?.toFixed(1)}s)</span> :
                  <span style style={{ color: ERROR }}>fail ({r.build_time?.toFixed(1)}s)</span>
            } />
          </div>
          {r.install_output && !r.install_success && (
            <details style={{ marginTop: 8 }}>
              <summary style={{ fontSize: 11, color: TEXT_MUTED, cursor: 'pointer' }}>Install output</summary>
              <pre style={{ fontSize: 10, color: TEXT_SECONDARY, whiteSpace: 'pre-wrap', maxHeight: 100, overflowY: 'auto', marginTop: 4, background: CARD_BG, padding: 6, borderRadius: 4 }}>
                {r.install_output}
              </pre>
            </details>
          )}
          {r.build_output && r.build_failed && (
            <details style={{ marginTop: 4 }}>
              <summary style={{ fontSize: 11, color: TEXT_MUTED, cursor: 'pointer' }}>Build output</summary>
              <pre style={{ fontSize: 10, color: TEXT_SECONDARY, whiteSpace: 'pre-wrap', maxHeight: 100, overflowY: 'auto', marginTop: 4, background: CARD_BG, padding: 6, borderRadius: 4 }}>
                {r.build_output}
              </pre>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}

function AIDetectionDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px' }}>
      <StatRow label="AI phrases found" value={details.ai_phrases_found}
        color={details.ai_phrases_found > 0 ? WARNING : SUCCESS} />
      <StatRow label="High comment ratio" value={
        details.high_comment_ratio
          ? <Badge color={WARNING}>Yes</Badge>
          : <Badge color={SUCCESS}>No</Badge>
      } />
      <StatRow label="Style shifts" value={details.style_shifts}
        color={details.style_shifts > 0 ? WARNING : SUCCESS} />
    </div>
  );
}

function CrossHackathonDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const matches: any[] = details.matches || [];
  if (matches.length === 0) return <div style={{ fontSize: 12, color: TEXT_MUTED }}>No matches found</div>;
  return (
    <div>
      {matches.map((m: any, i: number) => (
        <div key={i} style={{ marginBottom: 10, padding: 10, background: INPUT_BG, borderRadius: 6, border: `1px solid ${BORDER}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <Badge color={m.type === 'exact_github_url' ? ERROR : m.type === 'same_commit_hash' ? ORANGE : WARNING}>
              {m.type.replace(/_/g, ' ')}
            </Badge>
            {m.hackathon_id && (
              <span style={{ fontSize: 11, color: TEXT_MUTED }}>{m.hackathon_id}</span>
            )}
          </div>
          {m.devpost_url && (
            <div style={{ fontSize: 11, wordBreak: 'break-all', marginBottom: 4 }}>
              <a href={m.devpost_url} target="_blank" rel="noopener noreferrer" style={{ color: PRIMARY, textDecoration: 'none' }}>
                {m.devpost_url}
              </a>
            </div>
          )}
          {m.commit_hash && <div style={{ fontSize: 11, color: TEXT_MUTED }}>Commit: {m.commit_hash}</div>}
          {m.repo_name && <div style={{ fontSize: 11, color: TEXT_MUTED }}>Repo: {m.repo_name}</div>}
          {m.title && <div style={{ fontSize: 11, color: TEXT_SECONDARY, marginTop: 2 }}>{m.title}</div>}
        </div>
      ))}
    </div>
  );
}

function RepeatOffenderDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const priorFlags: any[] = details.prior_flags || [];
  const suspiciousPatterns: any[] = details.suspicious_patterns || [];
  return (
    <div>
      {priorFlags.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <SectionTitle>Prior flags ({priorFlags.length})</SectionTitle>
          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  <th style={{ textAlign: 'left', padding: '4px 8px', color: TEXT_MUTED }}>Username</th>
                  <th style={{ textAlign: 'left', padding: '4px 8px', color: TEXT_MUTED }}>Devpost</th>
                  <th style={{ textAlign: 'left', padding: '4px 8px', color: TEXT_MUTED }}>Title</th>
                </tr>
              </thead>
              <tbody>
                {priorFlags.map((f: any, i: number) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${BORDER}` }}>
                    <td style={{ padding: '4px 8px', color: TEXT_PRIMARY }}>{f.github_username}</td>
                    <td style={{ padding: '4px 8px' }}>
                      {f.devpost_url ? (
                        <a href={f.devpost_url} target="_blank" rel="noopener noreferrer" style={{ color: PRIMARY, textDecoration: 'none' }}>
                          link
                        </a>
                      ) : '—'}
                    </td>
                    <td style={{ padding: '4px 8px', color: TEXT_SECONDARY }}>{f.title || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {suspiciousPatterns.length > 0 && (
        <div>
          <SectionTitle>Suspicious patterns</SectionTitle>
          {suspiciousPatterns.map((p: any, i: number) => (
            <div key={i} style={{ fontSize: 11, color: TEXT_SECONDARY, marginBottom: 4, padding: '4px 8px', background: INPUT_BG, borderRadius: 4 }}>
              <span style={{ color: TEXT_PRIMARY }}>{p.devpost_profile}</span>
              <span style={{ color: TEXT_MUTED, marginLeft: 8 }}>
                GitHub: {p.github_accounts?.join(', ')}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SubmissionHistoryDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  return (
    <div>
      {details.wrong_readme && (
        <div style={{ background: ERROR_BG10, border: `1px solid ${ERROR_BORDER30}`, borderRadius: 6, padding: 8, fontSize: 12, color: ERROR_TEXT, marginBottom: 8 }}>
          README mentions a different hackathon
        </div>
      )}
      {details.no_team_data && (
        <div style={{ background: WARNING_BG10, border: `1px solid ${WARNING_BORDER30}`, borderRadius: 6, padding: 8, fontSize: 12, color: WARNING, marginBottom: 8 }}>
          No team member data from Devpost
        </div>
      )}
      {details.prior_flags !== undefined && details.prior_flags.length === 0 && (
        <div style={{ fontSize: 12, color: TEXT_MUTED }}>No prior flags</div>
      )}
    </div>
  );
}

function DevpostAlignmentSimpleDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  const missingTech: string[] = details.missing_tech || [];
  const foundTech: string[] = details.found_tech || [];
  return (
    <div>
      <div style={{ padding: '6px 0', borderBottom: `1px solid ${BORDER}`, marginBottom: 8 }}>
        <span style={{ fontSize: 12, color: TEXT_MUTED }}>Dead files</span>
        <div style={{ marginTop: 6 }}>
          <MiniBar pct={details.dead_files_pct} color={details.dead_files_pct > 30 ? ERROR : WARNING} />
        </div>
      </div>
      {foundTech.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <SectionTitle>Found tech</SectionTitle>
          <div>
            {foundTech.map((t: string) => (
              <Chip key={t} label={t} color={SUCCESS} />
            ))}
          </div>
        </div>
      )}
      {missingTech.length > 0 && (
        <div>
          <SectionTitle>Missing tech</SectionTitle>
          <div>
            {missingTech.map((t: string) => (
              <Chip key={t} label={t} color={ERROR} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── moved from CheckResultRow.tsx ───────────────────────────────

const COLORS = [PRIMARY, SUCCESS, WARNING, '#00bcd4', '#e040fb', '#ff6d00', '#2196f3', '#4caf50'];

function ContributorAuditDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;

  const pcts: Record<string, number> = details.commit_percentages || {};
  const authors = details.repo_authors || [];
  const teamNames = details.team_names || [];
  const teamGithubs = details.team_githubs || [];
  const ghosts = details.ghost_contributors || [];
  const mia = details.mia_members || [];

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

  const unmatchedAuthors = authors.filter(a => {
    return !teamNames.some(name => {
      const parts = name.split(' ');
      const aParts = a.split(' ');
      return parts.some(p => aParts.includes(p)) || aParts.some(p => parts.includes(p));
    }) && !teamGithubs.some(gh => a.includes(gh));
  });

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
  segments.sort((a, b) => b.pct - a.pct);

  const size = 160;
  const cx = size / 2, cy = size / 2;
  const radius = 60;
  const strokeWidth = 18;
  const circ = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <div>
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
            <text x={cx} y={cy - 8} textAnchor="middle" fill="#fff" fontSize={24} fontWeight={700}>
              {segments.length > 0 ? `${segments[0].pct}%` : '—'}
            </text>
            <text x={cx} y={cy + 12} textAnchor="middle" fill={TEXT_MUTED} fontSize={11}>
              top contributor
            </text>
          </svg>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        {segments.map((seg, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: seg.color, flexShrink: 0 }} />
            <span style={{ color: TEXT_PRIMARY, flex: 1 }}>{seg.label}</span>
            <span style={{ color: TEXT_MUTED, fontWeight: 600 }}>{seg.pct}%</span>
          </div>
        ))}
      </div>

      {mia.length > 0 && (
        <div style={{ marginBottom: 12, fontSize: 11, color: ERROR_TEXT }}>
          No commits: {mia.join(', ')}
        </div>
      )}

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

// ── trace flow visualization ────────────────────────────────────

const LAYER_COLORS: Record<string, string> = {
  entry_point: PRIMARY,
  core_logic: SUCCESS,
  data_layer: WARNING,
  output: INFO,
};

const LAYER_LABELS: Record<string, string> = {
  entry_point: 'Entry Point',
  core_logic: 'Core Logic',
  data_layer: 'Data Layer',
  output: 'Output',
};

function TraceStepRow({ step, isLast }: { step: Record<string, any>; isLast: boolean }) {
  const dotColor = LAYER_COLORS[step.layer] || SUCCESS;

  return (
    <div style={{ display: 'flex', gap: 12 }}>
      {/* connector column */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 20, flexShrink: 0 }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%', background: dotColor, flexShrink: 0,
          boxShadow: `0 0 6px ${dotColor}40`,
        }} />
        {!isLast && <div style={{ width: 2, flex: 1, background: SUCCESS, opacity: 0.3, minHeight: 8 }} />}
      </div>
      {/* step card */}
      <div style={{ flex: 1, paddingBottom: isLast ? 0 : 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: 10, fontWeight: 700, color: dotColor, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Step {step.step}
          </span>
          <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 600,
            color: dotColor, background: (dotColor + '20'),
          }}>
            {LAYER_LABELS[step.layer] || step.layer}
          </span>
        </div>
        {step.description && (
          <div style={{ fontSize: 12, color: TEXT_SECONDARY, marginBottom: 6 }}>{step.description}</div>
        )}
        {step.snippet && (
          <div style={{
            background: INPUT_BG, border: `1px solid ${BORDER}`, borderRadius: 4,
            padding: '6px 8px', marginBottom: 4, fontFamily: 'monospace', fontSize: 11,
            color: TEXT_PRIMARY, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
            maxHeight: 80, overflowY: 'auto',
          }}>
            {step.snippet}
          </div>
        )}
        {step.url && (
          <a href={step.url} target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, color: PRIMARY, textDecoration: 'none', wordBreak: 'break-all' }}>
            {step.url}
          </a>
        )}
      </div>
    </div>
  );
}

function AlignmentDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;

  function extractUrl(text: string): string {
    const m = text.match(/^(https:\/\/github\.com\/[^\s]+)/);
    return m ? m[1] : '#';
  }

  function renderVerifiedFlat(v: any, i: number) {
    return (
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
    );
  }

  function renderVerifiedTrace(v: any, i: number) {
    const traceSteps: any[] = v.trace || [];
    return (
      <div key={i} style={{ marginBottom: 16 }}>
        {/* claim header card */}
        <div style={{
          background: SUCCESS_BG10, border: `1px solid ${SUCCESS}30`, borderRadius: 6,
          padding: 10, marginBottom: 12,
        }}>
          <div style={{ fontSize: 13, color: TEXT_PRIMARY, fontWeight: 600 }}>{v.claim}</div>
          <div style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 2 }}>{v.explanation}</div>
        </div>
        {/* trace flow */}
        <div style={{ paddingLeft: 4 }}>
          {traceSteps.map((step: any, si: number) => (
            <TraceStepRow key={si} step={step} isLast={si === traceSteps.length - 1} />
          ))}
        </div>
      </div>
    );
  }

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
          {details.verified.map((v: any, i: number) =>
            v.trace && v.trace.length > 0
              ? renderVerifiedTrace(v, i)
              : renderVerifiedFlat(v, i)
          )}
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

function DuplicateGithubUrlDetails({ details }: { details: Record<string, any> }) {
  if (details.reason) return <ErrorReason reason={details.reason} />;
  return (
    <div style={{ background: WARNING_BG10, border: `1px solid ${WARNING_BORDER30}`, borderRadius: 6, padding: 10 }}>
      <div style={{ fontSize: 12, wordBreak: 'break-all', marginBottom: 4 }}>
        <span style={{ color: TEXT_MUTED }}>Duplicate URL: </span>
        <a href={details.duplicate_url} target="_blank" rel="noopener noreferrer" style={{ color: PRIMARY, textDecoration: 'none' }}>
          {details.duplicate_url}
        </a>
      </div>
      {details.other_submission && (
        <div style={{ fontSize: 11, color: TEXT_MUTED }}>
          Other submission: {details.other_submission}
        </div>
      )}
    </div>
  );
}

// ── fallback ─────────────────────────────────────────────────────

function RawDetails({ details }: { details: Record<string, any> }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Details</div>
      <pre style={{ fontSize: 12, color: TEXT_SECONDARY, whiteSpace: 'pre-wrap', background: CARD_BG, padding: 12, borderRadius: 6 }}>
        {JSON.stringify(details, null, 2)}
      </pre>
    </div>
  );
}

// ── dispatcher ──────────────────────────────────────────────────

const DETAIL_MAP: Record<string, React.FC<{ details: Record<string, any> }>> = {
  'repo-age': RepoAgeDetails,
  'commit-timestamps': CommitTimelineDetails,
  'file-timestamps': FileTimestampsDetails,
  'commit-quality': CommitQualityDetails,
  'dead-dependencies': DeadDepsDetails,
  'repo-integrity': RepoIntegrityDetails,
  'asset-integrity': AssetIntegrityDetails,
  'build-verify': BuildVerifyDetails,
  'ai-detection': AIDetectionDetails,
  'cross-hackathon-duplicate': CrossHackathonDetails,
  'repeat-offender': RepeatOffenderDetails,
  'submission-history': SubmissionHistoryDetails,
  'contributor-audit': ContributorAuditDetails,
  'duplicate-github-url': DuplicateGithubUrlDetails,
};

export function renderCheckDetails(checkName: string, details: Record<string, any>): ReactNode {
  if (!details || Object.keys(details).length === 0) return null;

  // claimed-vs-actual-tech has two variants: AI (has 'verified') and simple (has 'missing_tech')
  if (checkName === 'claimed-vs-actual-tech') {
    if (details.verified !== undefined) {
      return <AlignmentDetails details={details} />;
    }
    return <DevpostAlignmentSimpleDetails details={details} />;
  }

  const Component = DETAIL_MAP[checkName];
  if (Component) {
    return <Component details={details} />;
  }

  return <RawDetails details={details} />;
}
