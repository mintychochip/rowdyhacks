import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { PRIMARY, ERROR_TEXT, ERROR_BG20, ERROR, TEXT_MUTED, TEXT_PRIMARY, TEXT_WHITE, INPUT_BG, INPUT_BORDER } from '../theme';
import { getOAuthAuthorizeUrl } from '../services/api';

export default function AuthPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [searchParams] = useSearchParams();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const urlError = searchParams.get('error');

  useEffect(() => {
    if (urlError) {
      setError(decodeURIComponent(urlError));
    }
  }, [urlError]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, name, password);
      }
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: isMobile ? '30px auto' : '60px auto', padding: isMobile ? 14 : 24 }}>
      <h1 style={{ textAlign: 'center', marginBottom: 24 }}>
        {isLogin ? 'Sign In' : 'Create Account'}
      </h1>

      {error && (
        <div style={{ background: ERROR_BG20, border: `1px solid ${ERROR}`, borderRadius: 8, padding: 12, marginBottom: 16, color: ERROR_TEXT }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {!isLogin && (
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 14, color: TEXT_MUTED }}>Name</label>
            <input type="text" value={name} onChange={e => setName(e.target.value)} required
              style={{ width: '100%', padding: '10px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14, boxSizing: 'border-box' }} />
          </div>
        )}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4, fontSize: 14, color: TEXT_MUTED }}>Email</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
            style={{ width: '100%', padding: '10px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14, boxSizing: 'border-box' }} />
        </div>
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: 'block', marginBottom: 4, fontSize: 14, color: TEXT_MUTED }}>Password</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8}
            style={{ width: '100%', padding: '10px 12px', background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14, boxSizing: 'border-box' }} />
        </div>
        <button type="submit" disabled={loading}
          style={{ width: '100%', padding: '12px', background: PRIMARY, border: 'none', borderRadius: 8, color: TEXT_WHITE, fontSize: 16, fontWeight: 600, cursor: 'pointer' }}>
          {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Create Account'}
        </button>
      </form>

      <div style={{ marginTop: 20, marginBottom: 20 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
        }}>
          <div style={{ flex: 1, height: 1, background: INPUT_BORDER }} />
          <span style={{ color: TEXT_MUTED, fontSize: 13 }}>or continue with</span>
          <div style={{ flex: 1, height: 1, background: INPUT_BORDER }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(['google', 'github', 'discord', 'apple'] as const).map(provider => (
            <a
              key={provider}
              href={getOAuthAuthorizeUrl(provider)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                width: '100%', padding: '10px 12px',
                background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
                borderRadius: 6, color: TEXT_PRIMARY, fontSize: 14, fontWeight: 500,
                textDecoration: 'none', cursor: 'pointer', boxSizing: 'border-box',
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
                {provider === 'google' ? 'login' : provider === 'github' ? 'code' : provider === 'discord' ? 'chat' : 'fingerprint'}
              </span>
              Sign in with {provider.charAt(0).toUpperCase() + provider.slice(1)}
            </a>
          ))}
        </div>
      </div>

      <p style={{ textAlign: 'center', marginTop: 20, fontSize: 14, color: TEXT_MUTED }}>
        {isLogin ? "Don't have an account? " : 'Already have an account? '}
        <button onClick={() => { setIsLogin(!isLogin); setError(''); }}
          style={{ background: 'none', border: 'none', color: PRIMARY, cursor: 'pointer', fontSize: 14, textDecoration: 'underline' }}>
          {isLogin ? 'Sign Up' : 'Sign In'}
        </button>
      </p>
    </div>
  );
}
