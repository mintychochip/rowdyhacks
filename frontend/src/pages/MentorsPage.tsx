import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import { CARD_BG, INPUT_BG, INPUT_BORDER, PRIMARY, TEXT_PRIMARY, TEXT_MUTED, BORDER, RADIUS, SPACE, CYAN, GOLD } from '../theme';

interface Mentor {
  id: string;
  name: string;
  expertise: string[];
  bio: string | null;
  max_sessions: number;
  is_available: boolean;
  created_at: string;
}

export default function MentorsPage() {
  const { hackathonId } = useParams<{ hackathonId: string }>();
  const { user } = useAuth();
  const [mentors, setMentors] = useState<Mentor[]>([]);
  const [showRegister, setShowRegister] = useState(false);
  const [name, setName] = useState('');
  const [expertise, setExpertise] = useState('');
  const [bio, setBio] = useState('');
  const [loading, setLoading] = useState(true);
  const [requestingId, setRequestingId] = useState<string | null>(null);
  const [topic, setTopic] = useState('');
  const [reqDesc, setReqDesc] = useState('');

  const load = () => {
    if (!hackathonId) return;
    api.getMentors(hackathonId).then((d: { mentors: Mentor[] }) => {
      setMentors(d.mentors);
      setLoading(false);
    }).catch(() => setLoading(false));
  };
  useEffect(load, [hackathonId]);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hackathonId) return;
    await api.registerMentor(hackathonId, {
      name,
      expertise: expertise ? expertise.split(',').map(s => s.trim()) : undefined,
      bio: bio || undefined,
    });
    setName(''); setExpertise(''); setBio('');
    setShowRegister(false);
    load();
  };

  const handleRequest = async (mentorId: string) => {
    if (!hackathonId) return;
    try {
      await api.requestMentor(hackathonId, mentorId, { topic, description: reqDesc || undefined });
      setRequestingId(null);
      setTopic(''); setReqDesc('');
      alert('Mentor request sent!');
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
          <span className="material-symbols-outlined" style={{ verticalAlign: 'middle', marginRight: 8, color: GOLD }}>school</span>
          Mentors
        </h1>
        {user && (
          <button onClick={() => setShowRegister(!showRegister)} style={{
            padding: '10px 20px', background: `linear-gradient(135deg, ${GOLD}, ${CYAN})`,
            border: 'none', borderRadius: RADIUS.md, color: '#fff', fontWeight: 600, cursor: 'pointer',
          }}>
            {showRegister ? 'Cancel' : 'Become a Mentor'}
          </button>
        )}
      </div>

      {showRegister && (
        <form onSubmit={handleRegister} style={{
          background: CARD_BG, borderRadius: RADIUS.lg, padding: SPACE.lg,
          border: `1px solid ${BORDER}`, marginBottom: SPACE.lg,
        }}>
          <div style={{ marginBottom: SPACE.md }}>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Display Name</label>
            <input value={name} onChange={e => setName(e.target.value)} required style={inputStyle} />
          </div>
          <div style={{ marginBottom: SPACE.md }}>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Expertise (comma-separated)</label>
            <input value={expertise} onChange={e => setExpertise(e.target.value)} placeholder="React, Python, ML, UI/UX" style={inputStyle} />
          </div>
          <div style={{ marginBottom: SPACE.md }}>
            <label style={{ display: 'block', fontSize: 12, color: TEXT_MUTED, marginBottom: 4 }}>Bio</label>
            <textarea value={bio} onChange={e => setBio(e.target.value)} placeholder="Brief intro about your experience..." style={{ ...inputStyle, minHeight: 80, resize: 'vertical' }} />
          </div>
          <button type="submit" style={{
            padding: '10px 24px', background: GOLD, border: 'none',
            borderRadius: RADIUS.md, color: '#000', fontWeight: 600, cursor: 'pointer',
          }}>Register as Mentor</button>
        </form>
      )}

      {loading ? (
        <p style={{ color: TEXT_MUTED, textAlign: 'center', padding: 40 }}>Loading...</p>
      ) : mentors.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: TEXT_MUTED }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, display: 'block', marginBottom: 12 }}>person_search</span>
          No mentors available yet. Be the first to sign up!
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: SPACE.md }}>
          {mentors.map(m => (
            <div key={m.id} style={{
              background: CARD_BG, borderRadius: RADIUS.lg, padding: SPACE.lg,
              border: `1px solid ${BORDER}`,
            }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: TEXT_PRIMARY }}>{m.name}</h3>
              {m.bio && <p style={{ color: TEXT_MUTED, fontSize: 13, marginTop: 4 }}>{m.bio}</p>}
              {m.expertise.length > 0 && (
                <div style={{ display: 'flex', gap: 4, marginTop: SPACE.sm, flexWrap: 'wrap' }}>
                  {m.expertise.map(e => (
                    <span key={e} style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 99,
                      background: `${GOLD}20`, color: GOLD,
                    }}>{e}</span>
                  ))}
                </div>
              )}
              {user && requestingId === m.id ? (
                <div style={{ marginTop: SPACE.md }}>
                  <input value={topic} onChange={e => setTopic(e.target.value)} placeholder="Topic (required)" required style={{ ...inputStyle, marginBottom: 8 }} />
                  <textarea value={reqDesc} onChange={e => setReqDesc(e.target.value)} placeholder="Describe your question..." style={{ ...inputStyle, minHeight: 60, resize: 'vertical', marginBottom: 8 }} />
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={() => handleRequest(m.id)} style={{
                      padding: '8px 16px', background: PRIMARY, border: 'none',
                      borderRadius: RADIUS.md, color: '#fff', cursor: 'pointer',
                    }}>Send</button>
                    <button onClick={() => setRequestingId(null)} style={{
                      padding: '8px 16px', background: 'transparent', border: `1px solid ${BORDER}`,
                      borderRadius: RADIUS.md, color: TEXT_MUTED, cursor: 'pointer',
                    }}>Cancel</button>
                  </div>
                </div>
              ) : user ? (
                <button onClick={() => setRequestingId(m.id)} style={{
                  marginTop: SPACE.md, padding: '8px 16px', background: 'transparent',
                  border: `1px solid ${GOLD}`, borderRadius: RADIUS.md,
                  color: GOLD, cursor: 'pointer', fontWeight: 500, width: '100%',
                }}>Request Help</button>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
