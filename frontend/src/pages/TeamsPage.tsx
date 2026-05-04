import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { PAGE_BG, CARD_BG, INPUT_BG, INPUT_BORDER, PRIMARY, TEXT_PRIMARY, TEXT_MUTED, BORDER, RADIUS, SPACE, CYAN } from '../theme';

interface TeamPost {
  id: string;
  user_name: string | null;
  title: string;
  description: string | null;
  looking_for: string[];
  offering: string[];
  max_members: number;
  is_open: boolean;
  created_at: string;
}

export default function TeamsPage() {
  const { hackathonId } = useParams<{ hackathonId: string }>();
  const { user } = useAuth();
  const [posts, setPosts] = useState<TeamPost[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [lookingFor, setLookingFor] = useState('');
  const [offering, setOffering] = useState('');
  const [loading, setLoading] = useState(true);
  const [joinMessage, setJoinMessage] = useState('');
  const [joiningId, setJoiningId] = useState<string | null>(null);

  const load = () => {
    if (!hackathonId) return;
    api.getTeamPosts(hackathonId).then((d: { posts: TeamPost[] }) => {
      setPosts(d.posts);
      setLoading(false);
    }).catch(() => setLoading(false));
  };
  useEffect(load, [hackathonId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hackathonId) return;
    await api.createTeamPost(hackathonId, {
      title,
      description: description || undefined,
      looking_for: lookingFor ? lookingFor.split(',').map(s => s.trim()) : undefined,
      offering: offering ? offering.split(',').map(s => s.trim()) : undefined,
    });
    setTitle(''); setDescription(''); setLookingFor(''); setOffering('');
    setShowForm(false);
    load();
  };

  const handleJoin = async (postId: string) => {
    if (!hackathonId) return;
    try {
      await api.requestToJoinTeam(hackathonId, postId, joinMessage || undefined);
      setJoiningId(null);
      setJoinMessage('');
      alert('Request sent!');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send request';
      alert(msg);
    }
  };

  const inputStyle = {
    width: '100%', padding: '10px 14px', background: INPUT_BG,
    border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md,
    color: TEXT_PRIMARY, fontSize: 14, boxSizing: 'border-box' as const, outline: 'none',
  };

  return (
    <div style={{ padding: SPACE.lg, maxWidth: 900, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACE.lg }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: TEXT_PRIMARY, margin: 0 }}>
          <span className="material-symbols-outlined" style={{ verticalAlign: 'middle', marginRight: 8, color: PRIMARY }}>group_add</span>
          Find a Team
        </h1>
        {user && (
          <button onClick={() => setShowForm(!showForm)} style={{
            padding: '10px 20px', background: `linear-gradient(135deg, ${PRIMARY}, ${CYAN})`,
            border: 'none', borderRadius: RADIUS.md, color: '#fff', fontWeight: 600, cursor: 'pointer',
          }}>
            {showForm ? 'Cancel' : '+ Post'}
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleCreate} style={{
          background: CARD_BG, borderRadius: RADIUS.lg, padding: SPACE.lg,
          border: `1px solid ${BORDER}`, marginBottom: SPACE.lg,
        }}>
          <div style={{ marginBottom: SPACE.md }}>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Title</label>
            <input value={title} onChange={e => setTitle(e.target.value)} required placeholder="Looking for frontend devs" style={inputStyle} />
          </div>
          <div style={{ marginBottom: SPACE.md }}>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Tell people about your project idea..." style={{ ...inputStyle, minHeight: 80, resize: 'vertical' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: SPACE.md, marginBottom: SPACE.md }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Looking For (comma-separated)</label>
              <input value={lookingFor} onChange={e => setLookingFor(e.target.value)} placeholder="React, Python, ML" style={inputStyle} />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Offering (comma-separated)</label>
              <input value={offering} onChange={e => setOffering(e.target.value)} placeholder="Backend, DevOps, Design" style={inputStyle} />
            </div>
          </div>
          <button type="submit" style={{
            padding: '10px 24px', background: PRIMARY, border: 'none',
            borderRadius: RADIUS.md, color: '#fff', fontWeight: 600, cursor: 'pointer',
          }}>Create Post</button>
        </form>
      )}

      {loading ? (
        <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: 40 }}>Loading...</p>
      ) : posts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, display: 'block', marginBottom: 12 }}>group_off</span>
          No team posts yet. Be the first to look for teammates!
        </div>
      ) : (
        <div style={{ display: 'grid', gap: SPACE.md }}>
          {posts.map(p => (
            <div key={p.id} style={{
              background: CARD_BG, borderRadius: RADIUS.lg, padding: SPACE.lg,
              border: `1px solid ${BORDER}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: TEXT_PRIMARY }}>{p.title}</h3>
                  <p style={{ fontSize: 13, color: TEXT_MUTED, margin: '4px 0' }}>Posted by {p.user_name || 'Anonymous'}</p>
                </div>
                <span style={{
                  fontSize: 11, padding: '4px 10px', borderRadius: 99, fontWeight: 600,
                  background: '#10b98120', color: '#10b981',
                }}>Open</span>
              </div>
              {p.description && <p style={{ color: TEXT_PRIMARY, marginTop: SPACE.sm, fontSize: 14 }}>{p.description}</p>}
              <div style={{ display: 'flex', gap: SPACE.md, marginTop: SPACE.sm, flexWrap: 'wrap' }}>
                {p.looking_for.length > 0 && (
                  <div>
                    <span style={{ fontSize: 11, color: TEXT_MUTED }}>Looking for:</span>
                    <div style={{ display: 'flex', gap: 4, marginTop: 2, flexWrap: 'wrap' }}>
                      {p.looking_for.map(s => (
                        <span key={s} style={{
                          fontSize: 11, padding: '2px 8px', borderRadius: 99,
                          background: `${PRIMARY}20`, color: PRIMARY,
                        }}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}
                {p.offering.length > 0 && (
                  <div>
                    <span style={{ fontSize: 11, color: TEXT_MUTED }}>Offering:</span>
                    <div style={{ display: 'flex', gap: 4, marginTop: 2, flexWrap: 'wrap' }}>
                      {p.offering.map(s => (
                        <span key={s} style={{
                          fontSize: 11, padding: '2px 8px', borderRadius: 99,
                          background: `${CYAN}20`, color: CYAN,
                        }}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              {user && joiningId === p.id ? (
                <div style={{ marginTop: SPACE.md, display: 'flex', gap: 8 }}>
                  <input value={joinMessage} onChange={e => setJoinMessage(e.target.value)} placeholder="Introduce yourself..." style={{ ...inputStyle, flex: 1 }} />
                  <button onClick={() => handleJoin(p.id)} style={{
                    padding: '8px 16px', background: PRIMARY, border: 'none',
                    borderRadius: RADIUS.md, color: '#fff', cursor: 'pointer', whiteSpace: 'nowrap',
                  }}>Send</button>
                  <button onClick={() => setJoiningId(null)} style={{
                    padding: '8px 16px', background: 'transparent', border: `1px solid ${BORDER}`,
                    borderRadius: RADIUS.md, color: TEXT_MUTED, cursor: 'pointer',
                  }}>Cancel</button>
                </div>
              ) : user ? (
                <button onClick={() => setJoiningId(p.id)} style={{
                  marginTop: SPACE.md, padding: '8px 16px', background: 'transparent',
                  border: `1px solid ${PRIMARY}`, borderRadius: RADIUS.md,
                  color: PRIMARY, cursor: 'pointer', fontWeight: 500,
                }}>Request to Join</button>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
