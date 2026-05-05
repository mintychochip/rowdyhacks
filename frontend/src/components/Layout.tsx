import { useState, useEffect, createContext, useContext } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import { PRIMARY, GOLD, SUCCESS, STATUS_ACCEPTED, TEXT_PRIMARY, TEXT_MUTED, TEXT_DIM, TEXT_WHITE, PAGE_BG, NAV_BG, CARD_BG, INPUT_BG, BORDER, INPUT_BORDER, SPACE, RADIUS } from '../theme';

const ROLE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  organizer: { label: 'Organizer', color: GOLD, bg: '#FFC72C20' },
  judge: { label: 'Judge', color: GOLD, bg: '#FFC72C20' },
  participant: { label: 'Participant', color: STATUS_ACCEPTED, bg: '#10b98120' },
};

type NavItem = { to: string | null; icon: string; label: string; roles?: string[]; getTo?: (hkId: string) => string; requiresHackathon?: boolean };

// Hackathon context to share the ID across pages
export const HackathonContext = createContext<string | null>(null);
export const useHackathonId = () => useContext(HackathonContext);

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const { isMobile } = useMediaQuery();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hackathonId, setHackathonId] = useState<string | null>(null);
  const role = user?.role;
  const roleBadge = role && ROLE_LABELS[role];

  // Load the single hackathon ID for nav links
  useEffect(() => {
    api.getHackathons().then(hks => {
      if (hks.length > 0) setHackathonId(hks[0].id);
    }).catch(() => {});
  }, [user]);

  // Add CSS animation for float effect and hide scrollbars
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
      }
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }
      /* Hide scrollbar for Chrome, Safari and Opera */
      .hide-scrollbar::-webkit-scrollbar {
        display: none;
      }
      /* Hide scrollbar for IE, Edge and Firefox */
      .hide-scrollbar {
        -ms-overflow-style: none;
        scrollbar-width: none;
      }
    `;
    document.head.appendChild(style);
    return () => { document.head.removeChild(style); };
  }, []);

  const closeSidebar = () => setSidebarOpen(false);
  const toggleSidebar = () => setSidebarOpen(prev => !prev);

  const isActive = (to: string | null) => {
    if (!to) return false;
    if (to === '/') return location.pathname === '/' || location.pathname.startsWith('/report');
    // For hackathon-scoped links, match the pattern
    if (hackathonId && to.includes(hackathonId)) {
      return location.pathname === to || location.pathname.startsWith(to);
    }
    return location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
  };

  // Generate hackathon-scoped paths; return null if no hackathon exists (item will be hidden)
  const hk = (path: string) => hackathonId ? `/hackathons/${hackathonId}${path}` : null;

  const rawNav: NavItem[] = [
    { to: '/', icon: 'home', label: 'Home' },
    { to: '/assistant', icon: 'smart_toy', label: 'AI Assistant', roles: ['organizer', 'participant', 'judge'] },
    { to: '/analyze', icon: 'science', label: 'Analyze', roles: ['organizer'] },
    { to: hk('/registrations'), icon: 'group', label: 'Registrations', roles: ['organizer'] },
    { to: hk('/judging/setup'), icon: 'gavel', label: 'Judging', roles: ['organizer'] },
    { to: hk('/leaderboard'), icon: 'leaderboard', label: 'Leaderboard' },
    { to: hk('/projects'), icon: 'inventory_2', label: 'Projects', roles: ['organizer'] },
    { to: '/tracks', icon: 'route', label: 'Tracks' },
    { to: '/resources', icon: 'menu_book', label: 'Resources' },
    { to: '/check-in', icon: 'qr_code_scanner', label: 'Check-In', roles: ['organizer'] },
    { to: '/dashboard', icon: 'monitoring', label: 'Submissions', roles: ['organizer'] },
    { to: '/crawled-data', icon: 'database', label: 'Indexed Data', roles: ['organizer'] },
    { to: '/registrations', icon: 'badge', label: 'Your Application', roles: ['participant'] },
    { to: '/judge', icon: 'gavel', label: 'Judge Portal', roles: ['judge'] },
  ];

  // Filter out nav items that require a hackathon but have no valid link (no hackathon exists)
  // This prevents showing disabled links when there's no hackathon in the database
  const NAV_ITEMS = rawNav
    .filter((item): item is { to: string; icon: string; label: string; roles?: string[] } => item.to !== null);

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
      <aside className="hide-scrollbar" style={{
        position: 'fixed', left: 0, top: 0, bottom: 0, width: 240,
        background: NAV_BG, borderRight: `1px solid ${BORDER}`,
        display: 'flex', flexDirection: 'column', zIndex: 50,
        overflowY: 'auto',
        scrollbarWidth: 'none',
        msOverflowStyle: 'none',
        ...(isMobile ? {
          transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.2s ease',
          boxShadow: sidebarOpen ? '4px 0 24px rgba(0,0,0,0.5)' : 'none',
          zIndex: 60,
        } : {}),
      }}>
        {/* Logo */}
        <div style={{ padding: '16px 16px 12px' }}>
          <Link to="/" onClick={closeSidebar} style={{ textDecoration: 'none', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
            <img src="/rowdy-mascot.png" alt="Hack the Valley" style={{ width: 120, height: 'auto', borderRadius: 8 }} />
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: TEXT_WHITE, letterSpacing: -0.5, fontFamily: 'Inter, sans-serif' }}>
                Hack the Valley
              </div>
              <div style={{ fontSize: 10, color: PRIMARY, letterSpacing: 1.5, textTransform: 'uppercase', fontWeight: 600, marginTop: 2 }}>
                Canada's largest student-run hackathon
              </div>
            </div>
          </Link>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {visibleNav.map(item => {
            const active = isActive(item.to);
            return (
              <Link
                key={item.to + item.label}
                to={item.to}
                onClick={closeSidebar}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '10px 12px', borderRadius: RADIUS.md,
                  color: active ? PRIMARY : TEXT_MUTED,
                  background: active ? 'rgba(0,212,255,0.08)' : 'transparent',
                  borderLeft: active ? `3px solid ${PRIMARY}` : '3px solid transparent',
                  textDecoration: 'none',
                  fontSize: 14,
                  fontWeight: active ? 600 : 400,
                  fontFamily: 'Inter, sans-serif',
                  transition: 'all 0.15s',
                  cursor: 'pointer',
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 20, color: active ? PRIMARY : 'inherit' }}>{item.icon}</span>
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
                color: '#0B1120', fontSize: 13, fontWeight: 700,
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
              padding: '8px 16px', color: '#0B1120',
              textDecoration: 'none', fontSize: 14, fontWeight: 600,
              fontFamily: 'Inter, sans-serif',
            }}>
              Sign In
            </Link>
          )}
        </div>
      </aside>

      {/* Top bar */}
      <header style={{
        position: 'fixed', top: 0, right: 0, left: isMobile ? 0 : 240, height: 56,
        background: 'rgba(11,17,32,0.85)', backdropFilter: 'blur(12px)',
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
          <span style={{ fontSize: 14, color: TEXT_PRIMARY, fontWeight: 600, fontFamily: 'Inter, sans-serif' }}>
            Hack the Valley 2026
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
