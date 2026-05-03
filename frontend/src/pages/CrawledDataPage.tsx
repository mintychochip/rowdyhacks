import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { Card } from '../components/Primitives';
import { PAGE_BG, TEXT_PRIMARY, TEXT_MUTED, CARD_BG, BORDER, PRIMARY, RADIUS, TYPO } from '../theme';

interface CrawledHackathon {
  id: string;
  name: string;
  devpost_url: string;
  start_date: string | null;
  end_date: string | null;
  last_crawled_at: string | null;
  project_count: number;
}

interface CrawledProject {
  id: string;
  title: string;
  devpost_url: string;
  github_url: string | null;
  team_members: string[];
  created_at: string;
}

export default function CrawledDataPage() {
  const { user } = useAuth();
  const [hackathons, setHackathons] = useState<CrawledHackathon[]>([]);
  const [selectedHackathon, setSelectedHackathon] = useState<string | null>(null);
  const [projects, setProjects] = useState<CrawledProject[]>([]);
  const [projectTotal, setProjectTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [projectSearch, setProjectSearch] = useState('');

  useEffect(() => {
    loadHackathons();
  }, []);

  useEffect(() => {
    if (selectedHackathon) {
      loadProjects(selectedHackathon);
    }
  }, [selectedHackathon]);

  const loadHackathons = async () => {
    try {
      setLoading(true);
      const data = await api.request('/crawler/hackathons');
      setHackathons(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load hackathons');
    } finally {
      setLoading(false);
    }
  };

  const loadProjects = async (hackathonId: string) => {
    try {
      setProjectsLoading(true);
      const data = await api.request(`/crawler/hackathons/${hackathonId}/projects?limit=100`);
      setProjects(data.projects);
      setProjectTotal(data.total);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setProjectsLoading(false);
    }
  };

  const filteredHackathons = hackathons.filter(h =>
    h.name.toLowerCase().includes(search.toLowerCase())
  );

  const filteredProjects = projects.filter(p =>
    p.title.toLowerCase().includes(projectSearch.toLowerCase())
  );

  const selectedHackathonData = hackathons.find(h => h.id === selectedHackathon);

  if (user?.role !== 'organizer') {
    return (
      <div style={{ maxWidth: 900, margin: '0 auto', padding: 32 }}>
        <Card>
          <p style={{ textAlign: 'center', color: TEXT_MUTED }}>Organizer access required</p>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 16px' }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 24, color: TEXT_PRIMARY }}>
        Indexed Hackathons & Projects
      </h1>

      {error && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(239,68,68,0.1)',
          border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: RADIUS.md,
          color: '#ef4444',
          marginBottom: 16,
        }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24 }}>
        {/* Hackathons List */}
        <div>
          <Card style={{ height: '100%', minHeight: 500 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <h2 style={{ fontSize: 18, fontWeight: 600, color: TEXT_PRIMARY }}>
                Hackathons ({hackathons.length})
              </h2>
              <button
                onClick={loadHackathons}
                style={{
                  fontSize: 12,
                  color: PRIMARY,
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                Refresh
              </button>
            </div>

            <input
              type="text"
              placeholder="Search hackathons..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                marginBottom: 12,
                background: PAGE_BG,
                border: `1px solid ${BORDER}`,
                borderRadius: RADIUS.md,
                color: TEXT_PRIMARY,
                fontSize: 13,
              }}
            />

            {loading ? (
              <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: '40px 0' }}>Loading...</p>
            ) : (
              <div style={{ maxHeight: 600, overflowY: 'auto' }}>
                {filteredHackathons.map((h) => (
                  <button
                    key={h.id}
                    onClick={() => setSelectedHackathon(h.id)}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: 12,
                      marginBottom: 8,
                      borderRadius: RADIUS.md,
                      background: selectedHackathon === h.id ? 'rgba(26,92,231,0.12)' : CARD_BG,
                      border: `1px solid ${selectedHackathon === h.id ? PRIMARY : 'transparent'}`,
                      color: TEXT_PRIMARY,
                      cursor: 'pointer',
                    }}
                  >
                    <p style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {h.name}
                    </p>
                    <p style={{ fontSize: 11, color: TEXT_MUTED }}>
                      {h.project_count} projects
                    </p>
                    {h.end_date && (
                      <p style={{ fontSize: 10, color: TEXT_MUTED, marginTop: 2 }}>
                        Ended: {new Date(h.end_date).toLocaleDateString()}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Projects List */}
        <div>
          <Card style={{ height: '100%', minHeight: 500 }}>
            {selectedHackathonData ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 600, color: TEXT_PRIMARY }}>
                      {selectedHackathonData.name}
                    </h2>
                    <p style={{ fontSize: 13, color: TEXT_MUTED, marginTop: 4 }}>
                      {projectTotal} projects indexed
                    </p>
                  </div>
                  <a
                    href={selectedHackathonData.devpost_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: 12,
                      color: PRIMARY,
                      textDecoration: 'none',
                    }}
                  >
                    View on Devpost →
                  </a>
                </div>

                <input
                  type="text"
                  placeholder="Search projects..."
                  value={projectSearch}
                  onChange={(e) => setProjectSearch(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    marginBottom: 12,
                    background: PAGE_BG,
                    border: `1px solid ${BORDER}`,
                    borderRadius: RADIUS.md,
                    color: TEXT_PRIMARY,
                    fontSize: 13,
                  }}
                />

                {projectsLoading ? (
                  <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: '40px 0' }}>Loading projects...</p>
                ) : filteredProjects.length === 0 ? (
                  <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: '40px 0' }}>
                    {projectSearch ? 'No projects match your search' : 'No projects indexed yet'}
                  </p>
                ) : (
                  <div style={{ maxHeight: 600, overflowY: 'auto' }}>
                    {filteredProjects.map((p) => (
                      <div
                        key={p.id}
                        style={{
                          padding: 12,
                          marginBottom: 8,
                          background: PAGE_BG,
                          borderRadius: RADIUS.md,
                          border: `1px solid ${BORDER}`,
                        }}
                      >
                        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                          <a
                            href={p.devpost_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: PRIMARY, textDecoration: 'none' }}
                          >
                            {p.title}
                          </a>
                        </h3>
                        {p.github_url && (
                          <p style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 4 }}>
                            <a
                              href={p.github_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: TEXT_MUTED, textDecoration: 'none' }}
                            >
                              {p.github_url}
                            </a>
                          </p>
                        )}
                        {p.team_members && p.team_members.length > 0 && (
                          <p style={{ fontSize: 11, color: TEXT_MUTED, marginTop: 4 }}>
                            Team: {p.team_members.join(', ')}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
                <p style={{ color: TEXT_MUTED }}>Select a hackathon to view its projects</p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
