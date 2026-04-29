import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { PRIMARY, PRIMARY_HOVER, GOLD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE, NAV_BG, BORDER, INPUT_BORDER, STATUS_ACCEPTED } from '../theme';

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div style={{ minHeight: '100vh', background: '#080c1a', color: TEXT_PRIMARY }}>
      <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 24px', borderBottom: `1px solid ${BORDER}`, background: NAV_BG }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <Link to="/" style={{ fontSize: 20, fontWeight: 700, color: GOLD, textDecoration: 'none' }}>HackVerify</Link>
          <Link to="/" style={{ color: TEXT_MUTED, textDecoration: 'none', fontSize: 14 }}>Analyze</Link>
          <Link to="/hackathons" style={{ color: TEXT_MUTED, textDecoration: 'none', fontSize: 14 }}>Hackathons</Link>
          {user && (
            <Link to="/registrations" style={{ color: STATUS_ACCEPTED, textDecoration: 'none', fontSize: 14, fontWeight: 600 }}>
              My QR Codes
            </Link>
          )}
          {user && <Link to="/dashboard" style={{ color: TEXT_MUTED, textDecoration: 'none', fontSize: 14 }}>Dashboard</Link>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {user ? (
            <>
              <span style={{ fontSize: 14, color: TEXT_MUTED }}>{user.name}</span>
              <button onClick={logout} style={{ background: 'none', border: `1px solid ${INPUT_BORDER}`, borderRadius: 6, padding: '6px 12px', color: TEXT_MUTED, cursor: 'pointer', fontSize: 13 }}>Logout</button>
            </>
          ) : (
            <Link to="/auth" style={{ background: PRIMARY, border: 'none', borderRadius: 6, padding: '6px 16px', color: TEXT_WHITE, textDecoration: 'none', fontSize: 14 }}>Sign In</Link>
          )}
        </div>
      </nav>
      <main style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
        <Outlet />
      </main>
    </div>
  );
}
