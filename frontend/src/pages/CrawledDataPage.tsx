import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { Card } from '../components/Primitives';
import {
  PAGE_BG, TEXT_PRIMARY, TEXT_MUTED, CARD_BG, BORDER, PRIMARY, PRIMARY_BG20,
  RADIUS, TYPO, SPACE, ERROR, ERROR_BG10, ERROR_BORDER30, INPUT_BG,
  SUCCESS, SUCCESS_BG10, TEXT_WHITE, BORDER_LIGHT,
} from '../theme';

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
  const [activeTab, setActiveTab] = useState<'projects' | 'documents' | 'storage'>('projects');
  const [documents, setDocuments] = useState<Array<{ id: string; filename: string; chunk_count: number; s3_url?: string; created_at?: string }>>([]);
  const [docLoading, setDocLoading] = useState(false);
  const [docUploading, setDocUploading] = useState(false);
  const [docError, setDocError] = useState('');
  const [docSuccess, setDocSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [storageObjects, setStorageObjects] = useState<Array<{ key: string; size: number; last_modified: string; url: string }>>([]);
  const [storagePrefix, setStoragePrefix] = useState('');
  const [storageLoading, setStorageLoading] = useState(false);

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
      setError(null);
      const data = await api.request('/crawler/hackathons');
      setHackathons(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load hackathons';
      if (msg === 'signal is aborted without reason') {
        setError('Request timed out. Please try again.');
      } else {
        setError(msg);
      }
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

  const loadDocuments = async (hackathonId: string) => {
    setDocLoading(true);
    try {
      const res = await api.getAssistantDocuments(hackathonId);
      setDocuments(res.documents || []);
    } catch {
      // ignore
    } finally {
      setDocLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!selectedHackathon) return;
    setDocUploading(true);
    setDocError('');
    setDocSuccess('');
    try {
      const res = await api.uploadAssistantDocument(selectedHackathon, file);
      setDocSuccess(`Uploaded "${res.filename}" — ${res.chunk_count} chunks indexed.`);
      await loadDocuments(selectedHackathon);
    } catch (e: any) {
      setDocError(e.message || 'Upload failed');
    } finally {
      setDocUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!selectedHackathon) return;
    setDocError('');
    setDocSuccess('');
    try {
      await api.deleteAssistantDocument(selectedHackathon, docId);
      setDocSuccess('Document deleted.');
      await loadDocuments(selectedHackathon);
    } catch (e: any) {
      setDocError(e.message || 'Delete failed');
    }
  };

  const loadStorage = async (prefix: string = '') => {
    setStorageLoading(true);
    try {
      const res = await api.listStorageObjects(prefix);
      setStorageObjects(res.objects || []);
      setStoragePrefix(res.prefix || '');
    } catch (e: any) {
      console.error('Failed to load storage objects:', e);
      setStorageObjects([]);
    } finally {
      setStorageLoading(false);
    }
  };

  useEffect(() => {
    if (selectedHackathon) {
      loadDocuments(selectedHackathon);
    }
  }, [selectedHackathon]);

  useEffect(() => {
    if (activeTab === 'storage') {
      loadStorage();
    }
  }, [activeTab]);

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
      <h1 style={{ ...TYPO.h1, marginBottom: SPACE.xl }}>
        Indexed Hackathons & Projects
      </h1>

      {error && (
        <div style={{
          padding: `${SPACE.sm}px ${SPACE.md}px`,
          background: ERROR_BG10,
          border: `1px solid ${ERROR_BORDER30}`,
          borderRadius: RADIUS.md,
          color: ERROR,
          marginBottom: SPACE.md,
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
                padding: `${SPACE.sm}px ${SPACE.md}px`,
                marginBottom: SPACE.md,
                background: INPUT_BG,
                border: `1px solid ${BORDER}`,
                borderRadius: RADIUS.md,
                color: TEXT_PRIMARY,
                fontSize: 13,
                outline: 'none',
                boxSizing: 'border-box',
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
                      padding: `${SPACE.sm}px ${SPACE.md}px`,
                      marginBottom: SPACE.sm,
                      borderRadius: RADIUS.md,
                      background: selectedHackathon === h.id ? PRIMARY_BG20 : CARD_BG,
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

                {/* Tabs */}
                <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: `1px solid ${BORDER}` }}>
                  <button
                    onClick={() => setActiveTab('projects')}
                    style={{
                      padding: '8px 16px',
                      background: 'none',
                      border: 'none',
                      borderBottom: `2px solid ${activeTab === 'projects' ? PRIMARY : 'transparent'}`,
                      color: activeTab === 'projects' ? PRIMARY : TEXT_MUTED,
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Projects
                  </button>
                  <button
                    onClick={() => setActiveTab('documents')}
                    style={{
                      padding: '8px 16px',
                      background: 'none',
                      border: 'none',
                      borderBottom: `2px solid ${activeTab === 'documents' ? PRIMARY : 'transparent'}`,
                      color: activeTab === 'documents' ? PRIMARY : TEXT_MUTED,
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Documents
                  </button>
                  <button
                    onClick={() => setActiveTab('storage')}
                    style={{
                      padding: '8px 16px',
                      background: 'none',
                      border: 'none',
                      borderBottom: `2px solid ${activeTab === 'storage' ? PRIMARY : 'transparent'}`,
                      color: activeTab === 'storage' ? PRIMARY : TEXT_MUTED,
                      fontSize: 13,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Storage
                  </button>
                </div>

                {activeTab === 'projects' && (
                  <>
                    <input
                      type="text"
                      placeholder="Search projects..."
                      value={projectSearch}
                      onChange={(e) => setProjectSearch(e.target.value)}
                      style={{
                        width: '100%',
                        padding: `${SPACE.sm}px ${SPACE.md}px`,
                        marginBottom: SPACE.md,
                        background: INPUT_BG,
                        border: `1px solid ${BORDER}`,
                        borderRadius: RADIUS.md,
                        color: TEXT_PRIMARY,
                        fontSize: 13,
                        outline: 'none',
                        boxSizing: 'border-box',
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
                              padding: `${SPACE.sm}px ${SPACE.md}px`,
                              marginBottom: SPACE.sm,
                              background: CARD_BG,
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
                )}

                {activeTab === 'documents' && (
                  <>
                    {docError && (
                      <div style={{
                        background: ERROR_BG10, border: `1px solid ${ERROR}`, borderRadius: RADIUS.md,
                        padding: '10px 16px', marginBottom: SPACE.md, color: ERROR, fontSize: 14,
                      }}>
                        {docError}
                      </div>
                    )}
                    {docSuccess && (
                      <div style={{
                        background: SUCCESS_BG10, border: `1px solid ${SUCCESS}`, borderRadius: RADIUS.md,
                        padding: '10px 16px', marginBottom: SPACE.md, color: SUCCESS, fontSize: 14,
                      }}>
                        {docSuccess}
                      </div>
                    )}
                    <div style={{ marginBottom: SPACE.md }}>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".txt,.md,.pdf,.markdown"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileUpload(file);
                        }}
                        style={{ display: 'none' }}
                      />
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={docUploading}
                        style={{
                          padding: '10px 24px', background: PRIMARY, border: 'none',
                          borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 14,
                          fontWeight: 600, cursor: docUploading ? 'not-allowed' : 'pointer',
                          opacity: docUploading ? 0.6 : 1,
                        }}
                      >
                        {docUploading ? 'Uploading & indexing...' : 'Upload Document'}
                      </button>
                    </div>
                    {docLoading ? (
                      <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: '40px 0' }}>Loading documents...</p>
                    ) : documents.length === 0 ? (
                      <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: '40px 0' }}>
                        No documents uploaded yet.
                      </p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
                        {documents.map((doc) => (
                          <div key={doc.id} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: SPACE.md, background: INPUT_BG, borderRadius: RADIUS.md,
                            border: `1px solid ${BORDER_LIGHT}`,
                          }}>
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div style={{ fontSize: 14, color: TEXT_PRIMARY, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {doc.filename}
                              </div>
                              <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>
                                {doc.chunk_count} chunks indexed
                                {doc.s3_url && (
                                  <a href={doc.s3_url} target="_blank" rel="noopener noreferrer" style={{ color: PRIMARY, marginLeft: 8, textDecoration: 'none' }}>
                                    View file
                                  </a>
                                )}
                              </div>
                            </div>
                            <button
                              onClick={() => handleDeleteDocument(doc.id)}
                              style={{
                                background: 'none', border: 'none', color: ERROR,
                                cursor: 'pointer', fontSize: 13, fontWeight: 600,
                                marginLeft: SPACE.md,
                              }}
                            >
                              Delete
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}

                {activeTab === 'storage' && (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: SPACE.md }}>
                      <span style={{ fontSize: 12, color: TEXT_MUTED }}>Prefix:</span>
                      <input
                        type="text"
                        placeholder="e.g. assistant-documents/"
                        value={storagePrefix}
                        onChange={(e) => setStoragePrefix(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') loadStorage(storagePrefix); }}
                        style={{
                          flex: 1,
                          padding: `${SPACE.sm}px ${SPACE.md}px`,
                          background: INPUT_BG,
                          border: `1px solid ${BORDER}`,
                          borderRadius: RADIUS.md,
                          color: TEXT_PRIMARY,
                          fontSize: 13,
                          outline: 'none',
                        }}
                      />
                      <button
                        onClick={() => loadStorage(storagePrefix)}
                        style={{
                          padding: '8px 16px', background: PRIMARY, border: 'none',
                          borderRadius: RADIUS.md, color: TEXT_WHITE, fontSize: 13,
                          fontWeight: 600, cursor: 'pointer',
                        }}
                      >
                        List
                      </button>
                    </div>
                    {storageLoading ? (
                      <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: '40px 0' }}>Loading storage objects...</p>
                    ) : storageObjects.length === 0 ? (
                      <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: '40px 0' }}>
                        {storagePrefix ? `No objects found for prefix "${storagePrefix}"` : 'No objects in storage yet.'}
                      </p>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
                        {storageObjects.map((obj) => (
                          <div key={obj.key} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: SPACE.md, background: INPUT_BG, borderRadius: RADIUS.md,
                            border: `1px solid ${BORDER_LIGHT}`,
                          }}>
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div style={{ fontSize: 14, color: TEXT_PRIMARY, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {obj.key}
                              </div>
                              <div style={{ fontSize: 12, color: TEXT_MUTED, marginTop: 2 }}>
                                {(obj.size / 1024).toFixed(1)} KB · {new Date(obj.last_modified).toLocaleString()}
                              </div>
                            </div>
                            <a
                              href={obj.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: PRIMARY, fontSize: 13, fontWeight: 600, textDecoration: 'none', marginLeft: SPACE.md }}
                            >
                              View
                            </a>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
                <p style={{ color: TEXT_MUTED, textAlign: 'center', whiteSpace: 'pre-line' }}>
                  {hackathons.length === 0
                    ? "No crawled hackathons yet.\nImport a hackathon from Devpost to see projects here."
                    : "Select a hackathon to view its projects"}
                </p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
