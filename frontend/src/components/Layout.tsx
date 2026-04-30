import { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { PRIMARY, GOLD, SUCCESS, STATUS_ACCEPTED, TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, TEXT_WHITE, PAGE_BG, NAV_BG, CARD_BG, INPUT_BG, BORDER, INPUT_BORDER, TYPO, SPACE, RADIUS } from '../theme';

const ROLE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  organizer: { label: 'Organizer', color: GOLD, bg: '#FFC72C20' },
  judge: { label: 'Judge', color: GOLD, bg: '#FFC72C20' },
  participant: { label: 'Participant', color: STATUS_ACCEPTED, bg: '#10b98120' },
};

type NavItem = { to: string; icon: string; label: string; roles?: string[] };

const NAV_ITEMS: NavItem[] = [
  { to: '/', icon: 'search', label: 'Analyze' },
  { to: '/hackathons', icon: 'trophy', label: 'Hackathons' },
  { to: '/dashboard', icon: 'dashboard', label: 'Dashboard', roles: ['organizer'] },
  { to: '/hackathons', icon: 'gavel', label: 'Judge Portal', roles: ['judge'] },
  { to: '/registrations', icon: 'badge', label: 'My Registrations', roles: ['participant'] },
  { to: '/check-in', icon: 'qr_code_scanner', label: 'Check-In', roles: ['organizer'] },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const { isMobile } = useMediaQuery();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const role = user?.role;
  const roleBadge = role && ROLE_LABELS[role];

  const closeSidebar = () => setSidebarOpen(false);
  const toggleSidebar = () => setSidebarOpen(prev => !prev);

  const isActive = (to: string) => {
    if (to === '/') return location.pathname === '/' || location.pathname.startsWith('/report');
    return location.pathname.startsWith(to);
  };

  const visibleNav = NAV_ITEMS.filter(item => !item.roles || (role && item.roles.includes(role)));

  const handleLogout = () => {
    closeSidebar();
    logout();
  };

  return (
    <div style={{ minHeight: '100vh', background: PAGE_BG, color: TEXT_PRIMARY }}>
      {/* Mobile backdrop */}
      {isMobile && sidebarOpen && (
        <div
          onClick={closeSidebar}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            zIndex: 55, animation: 'slideDown 0.2s ease',
          }}
        />
      )}

      {/* Sidebar */}
      <aside style={{
        position: 'fixed', left: 0, top: 0, bottom: 0, width: 240,
        background: NAV_BG, borderRight: `1px solid ${BORDER}`,
        display: 'flex', flexDirection: 'column', zIndex: 50,
        ...(isMobile ? {
          transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.2s ease',
          boxShadow: sidebarOpen ? '4px 0 24px rgba(0,0,0,0.5)' : 'none',
          zIndex: 60,
        } : {}),
      }}>
        {/* Logo */}
        <div style={{ padding: '20px 20px 16px' }}>
          <Link to="/" onClick={closeSidebar} style={{ textDecoration: 'none' }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: GOLD, letterSpacing: -0.5 }}>
              HackVerify
            </div>
            <div style={{ ...TYPO['label-caps'], color: TEXT_DIM, marginTop: 2, fontSize: 10 }}>
              Integrity Platform
            </div>
          </Link>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {visibleNav.map(item => {
            const active = isActive(item.to);
            return (
              <Link
                key={item.to + (item.roles?.join() || '')}
                to={item.to}
                onClick={closeSidebar}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 12px', borderRadius: RADIUS.md,
                  color: active ? TEXT_PRIMARY : TEXT_MUTED,
                  fontWeight: active ? 600 : 400,
                  background: active ? 'rgba(26,92,231,0.12)' : 'transparent',
                  borderLeft: active ? `3px solid ${PRIMARY}` : '3px solid transparent',
                  textDecoration: 'none',
                  ...TYPO['body-sm'],
                  transition: 'all 0.15s',
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div style={{ padding: '16px', borderTop: `1px solid ${BORDER}` }}>
          {user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 32, height: 32, borderRadius: RADIUS.md,
                background: PRIMARY, display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: TEXT_WHITE, fontSize: 13, fontWeight: 700,
              }}>
                {(user.name || user.email || '?')[0].toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: TEXT_PRIMARY, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.name || 'User'}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 1 }}>
                  {roleBadge && (
                    <span style={{
                      fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: RADIUS.full,
                      background: roleBadge.bg, color: roleBadge.color,
                      textTransform: 'uppercase', letterSpacing: 0.5,
                    }}>
                      {roleBadge.label}
                    </span>
                  )}
                </div>
              </div>
              <Link
                to="/settings"
                title="Account Settings"
                style={{
                  background: 'none', border: 'none', color: TEXT_MUTED, cursor: 'pointer',
                  padding: 4, display: 'flex', alignItems: 'center', textDecoration: 'none',
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>settings</span>
              </Link>
              <button
                onClick={handleLogout}
                title="Logout"
                style={{
                  background: 'none', border: 'none', color: TEXT_MUTED, cursor: 'pointer',
                  padding: 4, display: 'flex', alignItems: 'center',
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>logout</span>
              </button>
            </div>
          ) : (
            <Link to="/auth" onClick={closeSidebar} style={{
              display: 'block', textAlign: 'center',
              background: PRIMARY, border: 'none', borderRadius: RADIUS.md,
              padding: '8px 16px', color: TEXT_WHITE,
              textDecoration: 'none', ...TYPO['body-sm'], fontWeight: 600,
            }}>
              Sign In
            </Link>
          )}
        </div>
      </aside>

      {/* Top bar */}
      <header style={{
        position: 'fixed', top: 0, right: 0, left: isMobile ? 0 : 240, height: 56,
        background: 'rgba(8,12,26,0.85)', backdropFilter: 'blur(12px)',
        borderBottom: `1px solid ${BORDER}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: isMobile ? '0 14px' : '0 24px', zIndex: 40,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {isMobile && (
            <button
              onClick={toggleSidebar}
              aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={sidebarOpen}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                padding: 4, display: 'flex', flexDirection: 'column', gap: 4,
                width: 24, height: 24, justifyContent: 'center',
              }}
            >
              <span style={{
                display: 'block', height: 2, width: 18, background: TEXT_MUTED,
                borderRadius: 1, transition: 'transform 0.2s',
                transform: sidebarOpen ? 'rotate(45deg) translate(4px, 4px)' : 'none',
              }} />
              <span style={{
                display: 'block', height: 2, width: 18, background: TEXT_MUTED,
                borderRadius: 1, transition: 'opacity 0.2s',
                opacity: sidebarOpen ? 0 : 1,
              }} />
              <span style={{
                display: 'block', height: 2, width: 18, background: TEXT_MUTED,
                borderRadius: 1, transition: 'transform 0.2s',
                transform: sidebarOpen ? 'rotate(-45deg) translate(4px, -4px)' : 'none',
              }} />
            </button>
          )}
          <span style={{ ...TYPO['body-sm'], color: TEXT_PRIMARY, fontWeight: 600 }}>
            HackVerify
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <span className="material-symbols-outlined" style={{
              position: 'absolute', left: 10, fontSize: 16, color: TEXT_DIM, pointerEvents: 'none',
            }}>search</span>
            <input
              type="text"
              placeholder="Search submissions..."
              style={{
                width: isMobile ? 140 : 200, padding: '6px 12px 6px 32px',
                background: INPUT_BG, border: `1px solid ${INPUT_BORDER}`,
                borderRadius: RADIUS.sm, color: TEXT_PRIMARY,
                fontSize: 12, outline: 'none',
              }}
            />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main style={{
        marginLeft: isMobile ? 0 : 240, paddingTop: 56 + SPACE.lg,
        paddingLeft: isMobile ? 14 : SPACE.lg,
        paddingRight: isMobile ? 14 : SPACE.lg,
        paddingBottom: SPACE.xl,
        maxWidth: 1440, minHeight: '100vh',
      }}>
        <Outlet />
      </main>
    </div>
  );
}
