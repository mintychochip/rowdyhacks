import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { PRIMARY, ERROR_TEXT, ERROR_BG20, ERROR, SUCCESS, TEXT_MUTED, TEXT_PRIMARY, TEXT_WHITE, INPUT_BG, INPUT_BORDER } from '../theme';
import { getOAuthAuthorizeUrl, forgotPassword, resetPassword } from '../services/api';
import BrandIcon from '../components/BrandIcon';

export default function AuthPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [searchParams] = useSearchParams();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSent, setForgotSent] = useState(false);
  const [resetToken] = useState(new URLSearchParams(window.location.search).get('reset_token') || '');
  const [newPassword, setNewPassword] = useState('');
  const [resetDone, setResetDone] = useState(false);

  const urlError = searchParams.get('error');

  useEffect(() => {
    if (urlError) {
      setError(decodeURIComponent(urlError));
    }
  }, [urlError]);

  // Redirect already-logged-in users away from the auth page
  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

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
          {(['google', 'github', 'discord'] as const).map(provider => (
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
              <BrandIcon provider={provider} size={20} />
              Sign in with {provider.charAt(0).toUpperCase() + provider.slice(1)}
            </a>
          ))}
        </div>
      </div>

      {isLogin && (
        <p style={{ textAlign: 'center', marginTop: 12, fontSize: 13 }}>
          <button onClick={() => setShowForgot(!showForgot)}
            style={{ background: 'none', border: 'none', color: TEXT_MUTED, cursor: 'pointer', fontSize: 13, textDecoration: 'underline' }}>
            Forgot password?
          </button>
        </p>
      )}

      {showForgot && !forgotSent && (
        <div style={{ marginTop: 16, padding: 16, background: INPUT_BG, borderRadius: 8, border: `1px solid ${INPUT_BORDER}` }}>
          <p style={{ fontSize: 13, color: TEXT_MUTED, marginBottom: 8 }}>Enter your email to receive a reset link.</p>
          <div style={{ display: 'flex', gap: 8 }}>
            <input type="email" value={forgotEmail} onChange={e => setForgotEmail(e.target.value)}
              placeholder="your@email.com" style={{ flex: 1, padding: '8px 12px', background: '#0f172a', border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14 }} />
            <button onClick={async () => { await forgotPassword(forgotEmail); setForgotSent(true); }}
              style={{ padding: '8px 16px', background: PRIMARY, border: 'none', borderRadius: 6, color: '#fff', cursor: 'pointer', fontWeight: 500 }}>Send</button>
          </div>
        </div>
      )}

      {forgotSent && (
        <div style={{ marginTop: 16, padding: 12, background: `${SUCCESS}15`, border: `1px solid ${SUCCESS}`, borderRadius: 8, color: SUCCESS, fontSize: 13 }}>
          If that email exists, a reset link has been sent. Check your inbox.
        </div>
      )}

      {resetToken && !resetDone && (
        <div style={{ marginTop: 16, padding: 16, background: INPUT_BG, borderRadius: 8, border: `1px solid ${INPUT_BORDER}` }}>
          <p style={{ fontSize: 14, color: TEXT_PRIMARY, marginBottom: 8, fontWeight: 600 }}>Reset Your Password</p>
          <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)}
            placeholder="New password (min 8 chars)" minLength={8}
            style={{ width: '100%', padding: '8px 12px', background: '#0f172a', border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, color: '#fff', fontSize: 14, marginBottom: 8, boxSizing: 'border-box' }} />
          <button onClick={async () => { try { await resetPassword(resetToken, newPassword); setResetDone(true); } catch (err: any) { setError(err.message); } }}
            style={{ padding: '8px 16px', background: PRIMARY, border: 'none', borderRadius: 6, color: '#fff', cursor: 'pointer', fontWeight: 500 }}>Reset Password</button>
        </div>
      )}

      {resetDone && (
        <div style={{ marginTop: 16, padding: 12, background: `${SUCCESS}15`, border: `1px solid ${SUCCESS}`, borderRadius: 8, color: SUCCESS, fontSize: 13 }}>
          Password reset successful! You can now sign in with your new password.
        </div>
      )}

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
