import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import * as api from '../services/api';
import {
  PRIMARY, SUCCESS, WARNING, ERROR, ERROR_TEXT,
  TEXT_MUTED, TEXT_SECONDARY,
  TYPO, SPACE,
} from '../theme';
import { Card, Button, Table, TableHeader, TableHeadCell, TableRow, TableCell, Badge } from '../components/Primitives';

interface Project {
  id: string;
  project_title: string;
  devpost_url: string;
  github_url: string | null;
  team_members: any;
  risk_score: number;
  verdict: string | null;
}

export default function ProjectGallery() {
  const { id } = useParams<{ id: string }>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.getHackathonSubmissions(id)
      .then(setProjects)
      .catch((e: any) => setError(e.message || 'Failed to load projects'))
      .finally(() => setLoading(false));
  }, [id]);

  const riskColor = (score: number) =>
    score < 30 ? SUCCESS : score < 60 ? WARNING : ERROR;

  const verdictBadge = (verdict: string | null) => {
    if (!verdict) return null;
    const map: Record<string, { color: string; label: string }> = {
      clean: { color: SUCCESS, label: 'Clean' },
      review: { color: WARNING, label: 'Review' },
      flagged: { color: ERROR, label: 'Flagged' },
    };
    const v = map[verdict];
    return v ? <Badge color={v.color}>{v.label}</Badge> : null;
  };

  const teamNames = (tm: any) => {
    if (!tm) return '-';
    if (Array.isArray(tm)) return tm.join(', ');
    if (typeof tm === 'object') return (tm as any).names?.join(', ') || '-';
    return '-';
  };

  // Deduplicate projects by extracting project slug from Devpost URL
  const dedupedProjects = projects.filter((p, index, self) => {
    // Extract project slug from URL like https://devpost.com/software/signlingo?...
    const match = p.devpost_url?.match(/\/software\/([^/?]+)/);
    const slug = match ? match[1] : p.id;
    // Keep only the first occurrence of each slug
    return self.findIndex((other) => {
      const otherMatch = other.devpost_url?.match(/\/software\/([^/?]+)/);
      const otherSlug = otherMatch ? otherMatch[1] : other.id;
      return otherSlug === slug;
    }) === index;
  });

  if (loading) {
    return <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: SPACE.xl }}>Loading projects...</p>;
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACE.lg }}>
        <div>
          <Link to={`/hackathons/${id}`} style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none' }}>
            &larr; Back to Hackathon
          </Link>
          <h1 style={{ ...TYPO.h1, marginTop: SPACE.sm, marginBottom: 0 }}>Project Gallery</h1>
        </div>
      </div>

      {error ? (
        <Card style={{ padding: SPACE.lg, textAlign: 'center' }}>
          <p style={{ color: ERROR_TEXT, marginBottom: SPACE.sm + 4 }}>{error}</p>
          <Button onClick={() => window.location.reload()}>Try Again</Button>
        </Card>
      ) : dedupedProjects.length === 0 ? (
        <Card style={{ padding: SPACE.xl, textAlign: 'center' }}>
          <p style={{ color: TEXT_MUTED }}>No completed projects yet.</p>
          <p style={{ color: TEXT_SECONDARY, fontSize: 13, marginTop: SPACE.sm }}>
            Projects appear here once they've been submitted and analyzed.
          </p>
        </Card>
      ) : (
        <Card style={{ overflow: 'hidden' }}>
          <Table>
            <TableHeader>
              <TableHeadCell>Project</TableHeadCell>
              <TableHeadCell>Team</TableHeadCell>
              <TableHeadCell align="right">Risk Score</TableHeadCell>
              <TableHeadCell>Verdict</TableHeadCell>
              <TableHeadCell align="right">Report</TableHeadCell>
            </TableHeader>
            <tbody>
              {dedupedProjects.map(p => (
                <TableRow key={p.id}>
                  <TableCell>
                    <div style={{ fontWeight: 600 }}>{p.project_title || 'Untitled'}</div>
                    <div style={{ fontSize: 12, color: TEXT_MUTED }}>
                      <a href={p.devpost_url} target="_blank" rel="noopener noreferrer" style={{ color: TEXT_MUTED }}>
                        Devpost
                      </a>
                      {p.github_url && (
                        <>
                          {' | '}
                          <a href={p.github_url} target="_blank" rel="noopener noreferrer" style={{ color: TEXT_MUTED }}>
                            GitHub
                          </a>
                        </>
                      )}
                    </div>
                  </TableCell>
                  <TableCell style={{ color: TEXT_SECONDARY }}>{teamNames(p.team_members)}</TableCell>
                  <TableCell align="right" style={{ fontFamily: TYPO['mono-data'].fontFamily, fontWeight: 600, color: riskColor(p.risk_score) }}>
                    {p.risk_score}
                  </TableCell>
                  <TableCell>{verdictBadge(p.verdict)}</TableCell>
                  <TableCell align="right">
                    <Link to={`/report/${p.id}`} style={{ color: PRIMARY, textDecoration: 'none', fontWeight: 600, fontSize: 13 }}>
                      View Report
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </tbody>
          </Table>
        </Card>
      )}
    </div>
  );
}
