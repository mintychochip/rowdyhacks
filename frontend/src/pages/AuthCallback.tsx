import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TEXT_MUTED, PAGE_BG, TEXT_PRIMARY } from '../theme';

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const hash = location.hash;
    const queryIndex = hash.indexOf('?');
    if (queryIndex === -1) {
      navigate('/auth?error=no_oauth_data');
      return;
    }
    const query = hash.slice(queryIndex + 1);
    const params = new URLSearchParams(query);
    const token = params.get('token');
    const error = params.get('error');

    if (error) {
      const messages: Record<string, string> = {
        invalid_state: 'Login session expired. Please try again.',
        oauth_denied: 'Login was cancelled.',
        provider_error: 'Could not connect to login provider. Please try again.',
        no_email: 'Your account did not return an email address.',
      };
      const message = messages[error] || 'Login failed. Please try again.';
      navigate(`/auth?error=${encodeURIComponent(message)}`);
      return;
    }

    if (token) {
      localStorage.setItem('auth_token', token);
      window.location.href = '/';
      return;
    }

    navigate('/auth?error=no_oauth_data');
  }, [navigate]);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '60vh', background: PAGE_BG,
    }}>
      <div style={{ textAlign: 'center' }}>
        <div className="material-symbols-outlined" style={{
          fontSize: 48, color: TEXT_PRIMARY, marginBottom: 16,
          animation: 'spin 1s linear infinite',
        }}>
          progress_activity
        </div>
        <p style={{ color: TEXT_MUTED }}>Completing sign in...</p>
      </div>
    </div>
  );
}
