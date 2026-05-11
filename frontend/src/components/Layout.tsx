import { useState, useEffect, createContext, useContext } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import CommandPalette, { useCommandPalette } from './CommandPalette';

const ROLE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  organizer: { label: 'Organizer', color: '#3b82f6', bg: 'rgba(37, 99, 235, 0.12)' },
  judge: { label: 'Judge', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.12)' },
  participant: { label: 'Participant', color: '#22c55e', bg: 'rgba(34, 197, 94, 0.12)' },
};

type NavItem = {
  to: string | null;
  label: string;
  roles?: string[];
  getTo?: (hkId: string) => string;
  requiresHackathon?: boolean;
  children?: { to: string; label: string }[];
};

export const HackathonContext = createContext<string | null>(null);
export const useHackathonId = () => useContext(HackathonContext);

// Icons
const HomeIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const SparklesIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
    <path d="M5 3v4"/>
    <path d="M19 17v4"/>
    <path d="M3 5h4"/>
    <path d="M17 19h4"/>
  </svg>
);

const ChartIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" x2="18" y1="20" y2="10"/>
    <line x1="12" x2="12" y1="20" y2="4"/>
    <line x1="6" x2="6" y1="20" y2="14"/>
  </svg>
);

const UsersIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const GavelIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m14 13-7 7"/>
    <path d="M19.5 2.5 21 4l-6.5 6.5"/>
    <path d="m14 6-7 7"/>
    <path d="m7.5 12.5 2 2"/>
    <path d="m6.5 13.5 2 2"/>
    <path d="m5.5 14.5 2 2"/>
    <path d="M4 20l2 2"/>
  </svg>
);

const TrophyIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>
    <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>
    <path d="M4 22h16"/>
    <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>
    <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>
    <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
  </svg>
);

const FolderIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>
  </svg>
);

const RouteIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="6" cy="19" r="3"/>
    <path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/>
    <circle cx="18" cy="5" r="3"/>
  </svg>
);

const BookmarkIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>
  </svg>
);

const CheckCircleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="m9 12 2 2 4-4"/>
  </svg>
);

const CommandIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 6v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3"/>
  </svg>
);

const MenuIcon = ({ open }: { open: boolean }) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {open ? (
      <>
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </>
    ) : (
      <>
        <line x1="4" y1="6" x2="20" y2="6" />
        <line x1="4" y1="12" x2="20" y2="12" />
        <line x1="4" y1="18" x2="20" y2="18" />
      </>
    )}
  </svg>
);

const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/>
    <path d="m21 21-4.3-4.3"/>
  </svg>
);

const NAV_ICONS: Record<string, React.ReactNode> = {
  'Home': <HomeIcon />,
  'AI Assistant': <SparklesIcon />,
  'Analyze': <ChartIcon />,
  'Registrations': <UsersIcon />,
  'Judging': <GavelIcon />,
  'Leaderboard': <TrophyIcon />,
  'Projects': <FolderIcon />,
  'Tracks': <RouteIcon />,
  'Resources': <BookmarkIcon />,
  'Check-In': <CheckCircleIcon />,
  'Submissions': <FolderIcon />,
  'Indexed Data': <SearchIcon />,
  'Your Application': <CheckCircleIcon />,
  'Judge Portal': <GavelIcon />,
};

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const { isOpen, open, close } = useCommandPalette();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hackathonId, setHackathonId] = useState<string | null>(null);
  const [expandedNav, setExpandedNav] = useState<Set<string>>(new Set(['Resources']));
  const role = user?.role;
  const roleBadge = role && ROLE_LABELS[role];

  const toggleNavSection = (label: string) => {
    setExpandedNav(prev => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  useEffect(() => {
    api.getHackathons().then(hks => {
      if (hks.length > 0) setHackathonId(hks[0].id);
    }).catch(() => {});
  }, [user]);

  const closeSidebar = () => setSidebarOpen(false);
  const toggleSidebar = () => setSidebarOpen(prev => !prev);

  const isActive = (to: string | null) => {
    if (!to) return false;
    if (to === '/') return location.pathname === '/' || location.pathname.startsWith('/report');
    if (hackathonId && to.includes(hackathonId)) {
      return location.pathname === to || location.pathname.startsWith(to);
    }
    return location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
  };

  const hk = (path: string) => hackathonId ? `/hackathons/${hackathonId}${path}` : null;

  const rawNav: NavItem[] = [
    { to: '/', label: 'Home' },
    { to: '/assistant', label: 'AI Assistant', roles: ['organizer', 'participant', 'judge'] },
    { to: '/analyze', label: 'Analyze', roles: ['organizer'] },
    { to: hk('/registrations'), label: 'Registrations', roles: ['organizer'] },
    { to: hk('/judging/setup'), label: 'Judging', roles: ['organizer'] },
    { to: hk('/leaderboard'), label: 'Leaderboard' },
    { to: hk('/projects'), label: 'Projects', roles: ['organizer'] },
    { to: '/tracks', label: 'Tracks' },
    {
      to: '/resources',
      label: 'Resources',
      children: [
        { to: '/resources/getting-started', label: 'Getting Started' },
        { to: '/resources/apis', label: 'APIs' },
        { to: '/resources/hardware', label: 'Hardware' },
      ]
    },
    { to: '/check-in', label: 'Check-In', roles: ['organizer'] },
    { to: '/dashboard', label: 'Submissions', roles: ['organizer'] },
    { to: '/crawled-data', label: 'Indexed Data', roles: ['organizer'] },
    { to: '/registrations', label: 'Your Application', roles: ['participant'] },
    { to: '/judge', label: 'Judge Portal', roles: ['judge'] },
  ];

  const NAV_ITEMS = rawNav.filter((item): item is { to: string; label: string; roles?: string[] } => item.to !== null);
  const visibleNav = NAV_ITEMS.filter(item => !item.roles || (role && item.roles.includes(role)));

  const handleLogout = () => {
    closeSidebar();
    logout();
  };

  return (
    <HackathonContext.Provider value={hackathonId}>
      <div style={{ minHeight: '100vh', height: '100vh', display: 'flex', background: 'var(--bg-base)', color: 'var(--text-primary)' }}>
        <CommandPalette isOpen={isOpen} onClose={close} />

        {/* Mobile backdrop */}
        {isMobile && sidebarOpen && (
          <div
            onClick={closeSidebar}
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.6)',
              backdropFilter: 'blur(4px)',
              zIndex: 45,
              animation: 'fadeIn 200ms ease',
            }}
          />
        )}

        {/* Sidebar */}
        <aside
          style={{
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            width: 260,
            background: 'var(--bg-secondary)',
            borderRight: '1px solid var(--border-subtle)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 50,
            overflowY: 'auto',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
            ...(isMobile ? {
              transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
              transition: 'transform 300ms cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: sidebarOpen ? '4px 0 24px rgba(0,0,0,0.4)' : 'none',
            } : {}),
          }}
        >
          {/* Logo */}
          <div style={{ padding: '20px 20px 16px' }}>
            <Link to="/" onClick={closeSidebar} style={{ textDecoration: 'none' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
              }}>
                <div style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#f97316',
                  filter: 'drop-shadow(0 0 6px rgba(249, 115, 22, 0.4))',
                }}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
                    <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
                    <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
                    <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
                  </svg>
                </div>
                <div>
                  <div style={{
                    fontSize: 15,
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    letterSpacing: '-0.01em',
                  }}>
                    Hackathon
                  </div>
                  <div style={{
                    fontSize: 11,
                    color: 'var(--text-muted)',
                    fontWeight: 500,
                  }}>
                    2026
                  </div>
                </div>
              </div>
            </Link>
          </div>

          {/* Command Palette Trigger */}
          <div style={{ padding: '0 16px 12px' }}>
            <button
              onClick={open}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                width: '100%',
                padding: '10px 14px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                borderRadius: 8,
                color: 'var(--text-tertiary)',
                fontSize: 13,
                cursor: 'pointer',
                transition: 'all 150ms ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--bg-elevated)';
                e.currentTarget.style.borderColor = 'var(--border-strong)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--bg-tertiary)';
                e.currentTarget.style.borderColor = 'var(--border-default)';
              }}
            >
              <SearchIcon />
              <span style={{ flex: 1, textAlign: 'left' }}>Search...</span>
              <kbd style={{
                padding: '3px 6px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-default)',
                borderRadius: 4,
                fontSize: 10,
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                color: 'var(--text-muted)',
              }}>
                ⌘K
              </kbd>
            </button>
          </div>

          {/* Nav */}
          <nav style={{
            flex: 1,
            padding: '8px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}>
            {visibleNav.map(item => {
              const active = isActive(item.to);
              const icon = NAV_ICONS[item.label];
              const hasChildren = item.children && item.children.length > 0;
              const isExpanded = expandedNav.has(item.label);

              // Check if any child is active
              const childActive = hasChildren && item.children?.some(child =>
                location.pathname === child.to
              );

              if (hasChildren) {
                return (
                  <div key={item.to + item.label}>
                    {/* Parent nav item with expand button */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        borderRadius: 8,
                        color: active || childActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                        background: active || childActive ? 'var(--bg-tertiary)' : 'transparent',
                        border: '1px solid',
                        borderColor: active || childActive ? 'var(--border-default)' : 'transparent',
                        transition: 'all 150ms ease',
                      }}
                    >
                      <Link
                        to={item.to}
                        onClick={closeSidebar}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 12,
                          flex: 1,
                          padding: '9px 12px',
                          color: 'inherit',
                          background: 'transparent',
                          textDecoration: 'none',
                          fontSize: 14,
                          fontWeight: active || childActive ? 500 : 400,
                          borderRadius: 8,
                        }}
                        onMouseEnter={(e) => {
                          if (!active && !childActive) {
                            e.currentTarget.parentElement!.style.background = 'var(--bg-tertiary)';
                            e.currentTarget.parentElement!.style.color = 'var(--text-primary)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!active && !childActive) {
                            e.currentTarget.parentElement!.style.background = 'transparent';
                            e.currentTarget.parentElement!.style.color = 'var(--text-secondary)';
                          }
                        }}
                      >
                        <span style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: 22,
                          height: 22,
                          color: active || childActive ? 'var(--text-primary)' : 'var(--text-tertiary)',
                          transition: 'color 150ms ease',
                        }}>
                          {icon}
                        </span>
                        {item.label}
                      </Link>
                      {/* Expand/collapse chevron button */}
                      <button
                        onClick={() => toggleNavSection(item.label)}
                        style={{
                          padding: '9px 12px',
                          background: 'transparent',
                          border: 'none',
                          borderRadius: 8,
                          cursor: 'pointer',
                          color: 'var(--text-muted)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'transform 200ms ease',
                        }}
                        aria-label={isExpanded ? 'Collapse section' : 'Expand section'}
                      >
                        <span style={{
                          fontSize: 12,
                          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                          transition: 'transform 200ms ease',
                        }}>
                          ▼
                        </span>
                      </button>
                    </div>

                    {/* Child items */}
                    {isExpanded && (
                      <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        marginLeft: 34,
                        marginTop: 2,
                        marginBottom: 4,
                        paddingLeft: 12,
                        borderLeft: '1px solid var(--border-subtle)',
                      }}>
                        {item.children?.map(child => {
                          const childIsActive = location.pathname === child.to;
                          return (
                            <div
                              key={child.to}
                              onClick={() => { navigate(child.to); closeSidebar(); }}
                              onMouseEnter={(e) => {
                                if (!childIsActive) {
                                  e.currentTarget.style.background = 'var(--bg-tertiary)';
                                  e.currentTarget.style.color = 'var(--text-secondary)';
                                }
                              }}
                              onMouseLeave={(e) => {
                                if (!childIsActive) {
                                  e.currentTarget.style.background = 'transparent';
                                  e.currentTarget.style.color = 'var(--text-muted)';
                                }
                              }}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                padding: '8px 12px',
                                borderRadius: 6,
                                cursor: 'pointer',
                                color: childIsActive ? 'var(--text-primary)' : 'var(--text-muted)',
                                background: childIsActive ? 'var(--bg-tertiary)' : 'transparent',
                                textDecoration: 'none',
                                fontSize: 13,
                                fontWeight: childIsActive ? 500 : 400,
                                transition: 'all 150ms ease',
                              }}
                            >
                              {child.label}
                              {childIsActive && (
                                <div style={{
                                  marginLeft: 'auto',
                                  width: 4,
                                  height: 4,
                                  borderRadius: '50%',
                                  background: 'var(--text-primary)',
                                }} />
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              }

              return (
                <Link
                  key={item.to + item.label}
                  to={item.to}
                  onClick={closeSidebar}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '9px 12px',
                    borderRadius: 8,
                    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                    background: active ? 'var(--bg-tertiary)' : 'transparent',
                    textDecoration: 'none',
                    fontSize: 14,
                    fontWeight: active ? 500 : 400,
                    transition: 'all 150ms ease',
                    border: '1px solid',
                    borderColor: active ? 'var(--border-default)' : 'transparent',
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = 'var(--bg-tertiary)';
                      e.currentTarget.style.color = 'var(--text-primary)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text-secondary)';
                    }
                  }}
                >
                  <span style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 22,
                    height: 22,
                    color: active ? 'var(--text-primary)' : 'var(--text-tertiary)',
                    transition: 'color 150ms ease',
                  }}>
                    {icon}
                  </span>
                  {item.label}
                  {active && (
                    <div style={{
                      marginLeft: 'auto',
                      width: 4,
                      height: 4,
                      borderRadius: '50%',
                      background: 'var(--accent-primary)',
                    }} />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* User section */}
          <div style={{
            padding: '16px',
            borderTop: '1px solid var(--border-subtle)',
            background: 'var(--bg-secondary)',
          }}>
            {user ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 36,
                  height: 36,
                  borderRadius: 10,
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-primary)',
                  fontSize: 14,
                  fontWeight: 600,
                }}>
                  {(user.name || user.email || '?')[0].toUpperCase()}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 14,
                    fontWeight: 500,
                    color: 'var(--text-primary)',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {user.name || user.email?.split('@')[0] || 'User'}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
                    {roleBadge && (
                      <span style={{
                        fontSize: 10,
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: 4,
                        background: roleBadge.bg,
                        color: roleBadge.color,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
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
                    padding: 8,
                    background: 'transparent',
                    border: '1px solid var(--border-default)',
                    borderRadius: 8,
                    color: 'var(--text-tertiary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 150ms ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-tertiary)';
                  }}
                >
                  <LogoutIcon />
                </button>
              </div>
            ) : (
              <Link
                to="/auth"
                onClick={closeSidebar}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  padding: '12px 16px',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 10,
                  color: 'var(--text-primary)',
                  textDecoration: 'none',
                  fontSize: 14,
                  fontWeight: 500,
                  transition: 'all 150ms ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--bg-elevated)';
                  e.currentTarget.style.borderColor = 'var(--border-strong)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'var(--bg-tertiary)';
                  e.currentTarget.style.borderColor = 'var(--border-default)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <UserIcon />
                Sign In
              </Link>
            )}
          </div>
        </aside>

        {/* Main content wrapper */}
        <div style={{
          flex: 1,
          marginLeft: isMobile ? 0 : 260,
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
        }}>
          {/* Top bar */}
          <header style={{
            position: 'sticky',
            top: 0,
            height: 64,
            background: 'rgba(10, 15, 30, 0.8)',
            backdropFilter: 'blur(12px)',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: isMobile ? '0 16px' : '0 32px',
            zIndex: 40,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              {isMobile && (
                <button
                  onClick={toggleSidebar}
                  aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--border-default)',
                    borderRadius: 8,
                    padding: 8,
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 150ms ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                >
                  <MenuIcon open={sidebarOpen} />
                </button>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  fontSize: 13,
                  color: 'var(--text-muted)',
                  fontWeight: 500,
                }}>
                  Platform
                </span>
                <span style={{ color: 'var(--border-default)' }}>/</span>
                <span style={{
                  fontSize: 13,
                  color: 'var(--text-primary)',
                  fontWeight: 500,
                }}>
                  2026
                </span>
              </div>
            </div>

            {/* Right side actions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {/* Quick command button */}
              <button
                onClick={open}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 14px',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 8,
                  color: 'var(--text-secondary)',
                  fontSize: 13,
                  cursor: 'pointer',
                  transition: 'all 150ms ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--bg-elevated)';
                  e.currentTarget.style.borderColor = 'var(--border-strong)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'var(--bg-tertiary)';
                  e.currentTarget.style.borderColor = 'var(--border-default)';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }}
              >
                <CommandIcon />
                {!isMobile && (
                  <>
                    <span>Command</span>
                    <kbd style={{
                      padding: '2px 6px',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border-default)',
                      borderRadius: 4,
                      fontSize: 10,
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      color: 'var(--text-muted)',
                    }}>
                      ⌘K
                    </kbd>
                  </>
                )}
              </button>
            </div>
          </header>

          {/* Page content */}
          <main style={{
            flex: 1,
            padding: isMobile ? 16 : 32,
          }}>
            <Outlet />
          </main>
        </div>
      </div>
    </HackathonContext.Provider>
  );
}

// Logout icon component
function LogoutIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
      <polyline points="16 17 21 12 16 7"/>
      <line x1="21" x2="9" y1="12" y2="12"/>
    </svg>
  );
}

// User icon component
function UserIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
      <circle cx="12" cy="7" r="4"/>
    </svg>
  );
}
