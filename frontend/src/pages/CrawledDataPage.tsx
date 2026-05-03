import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { Primitives } from '../components/Primitives';

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
      <div className="max-w-4xl mx-auto py-8">
        <Primitives.Card>
          <p className="text-center text-slate-400">Organizer access required</p>
        </Primitives.Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-6">Indexed Hackathons & Projects</h1>

      {error && (
        <Primitives.Alert variant="error" className="mb-4">
          {error}
        </Primitives.Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Hackathons List */}
        <div className="lg:col-span-1">
          <Primitives.Card className="h-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">
                Hackathons ({hackathons.length})
              </h2>
              <button
                onClick={loadHackathons}
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                Refresh
              </button>
            </div>

            <input
              type="text"
              placeholder="Search hackathons..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-3 py-2 mb-4 bg-slate-800 border border-slate-700 rounded-lg text-sm"
            />

            {loading ? (
              <p className="text-slate-400 text-center py-8">Loading...</p>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-y-auto">
                {filteredHackathons.map((h) => (
                  <button
                    key={h.id}
                    onClick={() => setSelectedHackathon(h.id)}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      selectedHackathon === h.id
                        ? 'bg-blue-600/20 border border-blue-500'
                        : 'bg-slate-800/50 hover:bg-slate-800 border border-transparent'
                    }`}
                  >
                    <p className="font-medium text-sm truncate">{h.name}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {h.project_count} projects
                    </p>
                    {h.end_date && (
                      <p className="text-xs text-slate-500">
                        Ended: {new Date(h.end_date).toLocaleDateString()}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            )}
          </Primitives.Card>
        </div>

        {/* Projects List */}
        <div className="lg:col-span-2">
          <Primitives.Card className="h-full">
            {selectedHackathonData ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-semibold">
                      {selectedHackathonData.name}
                    </h2>
                    <p className="text-sm text-slate-400">
                      {projectTotal} projects indexed
                    </p>
                  </div>
                  <a
                    href={selectedHackathonData.devpost_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-400 hover:text-blue-300"
                  >
                    View on Devpost →
                  </a>
                </div>

                <input
                  type="text"
                  placeholder="Search projects..."
                  value={projectSearch}
                  onChange={(e) => setProjectSearch(e.target.value)}
                  className="w-full px-3 py-2 mb-4 bg-slate-800 border border-slate-700 rounded-lg text-sm"
                />

                {projectsLoading ? (
                  <p className="text-slate-400 text-center py-8">Loading projects...</p>
                ) : filteredProjects.length === 0 ? (
                  <p className="text-slate-400 text-center py-8">
                    {projectSearch ? 'No projects match your search' : 'No projects indexed yet'}
                  </p>
                ) : (
                  <div className="space-y-3 max-h-[600px] overflow-y-auto">
                    {filteredProjects.map((p) => (
                      <div
                        key={p.id}
                        className="p-4 bg-slate-800/50 rounded-lg border border-slate-700"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-sm truncate">
                              <a
                                href={p.devpost_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-400 hover:text-blue-300"
                              >
                                {p.title}
                              </a>
                            </h3>
                            {p.github_url && (
                              <p className="text-xs text-slate-400 mt-1 truncate">
                                <a
                                  href={p.github_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="hover:text-slate-300"
                                >
                                  {p.github_url}
                                </a>
                              </p>
                            )}
                            {p.team_members && p.team_members.length > 0 && (
                              <p className="text-xs text-slate-500 mt-1">
                                Team: {p.team_members.join(', ')}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-full min-h-[300px]">
                <p className="text-slate-400">
                  Select a hackathon to view its projects
                </p>
              </div>
            )}
          </Primitives.Card>
        </div>
      </div>
    </div>
  );
}
