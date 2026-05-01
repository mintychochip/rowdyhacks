import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import {
  PRIMARY, PRIMARY_BG20, CYAN, CYAN_BG20, GOLD, GOLD_BG20,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, BORDER, BORDER_LIGHT,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface Track {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  prize: string;
  criteria: string[];
  resources?: { name: string; url: string }[];
}

interface HackathonTracks {
  hackathon_id: string;
  hackathon_name: string;
  tracks: Track[];
}

const DEFAULT_TRACKS: Track[] = [
  {
    id: '1',
    name: 'Deep Space Exploration',
    description: 'Push the boundaries of space tech. Build tools for satellite data analysis, mission planning, or astronaut support systems.',
    icon: '🚀',
    color: '#8b5cf6',
    prize: '$1,000 + SpaceX Tour',
    criteria: ['Innovation', 'Technical Complexity', 'Space Applicability'],
    resources: [
      { name: 'NASA Open APIs', url: 'https://api.nasa.gov/' },
      { name: 'Space-Track.org', url: 'https://www.space-track.org/' },
    ],
  },
  {
    id: '2',
    name: 'Orbital Commerce',
    description: 'Create the future of space economy. Develop marketplace platforms, logistics tools, or financial systems for the space age.',
    icon: '💎',
    color: '#06b6d4',
    prize: '$800 + Starlink Kit',
    criteria: ['Business Viability', 'UX Design', 'Market Potential'],
    resources: [
      { name: 'Space Economy Report', url: '#' },
      { name: 'Satellite Pricing APIs', url: '#' },
    ],
  },
  {
    id: '3',
    name: 'Cosmic Commons',
    description: 'Democratize access to space. Build educational tools, citizen science platforms, or community-driven space initiatives.',
    icon: '🌌',
    color: '#fbbf24',
    prize: '$600 + Celestron Telescope',
    criteria: ['Social Impact', 'Accessibility', 'Community Engagement'],
    resources: [
      { name: 'Zooniverse APIs', url: 'https://www.zooniverse.org/' },
      { name: 'Astronomy Data', url: '#' },
    ],
  },
  {
    id: '4',
    name: 'Nebula Arts',
    description: 'Where space meets creativity. Develop immersive visualizations, space-themed games, or generative art using astronomical data.',
    icon: '✨',
    color: '#ec4899',
    prize: '$500 + Wacom Tablet',
    criteria: ['Aesthetic Quality', 'Technical Execution', 'Concept Originality'],
    resources: [
      { name: 'ESA Sky', url: 'https://sky.esa.int/' },
      { name: 'Three.js Docs', url: 'https://threejs.org/' },
    ],
  },
];

export default function TracksPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { isMobile } = useMediaQuery();
  const [tracks, setTracks] = useState<Track[]>(DEFAULT_TRACKS);
  const [hackathonName, setHackathonName] = useState('CSUB Hacks');
  const [loading, setLoading] = useState(true);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null);
  const [hoveredTrack, setHoveredTrack] = useState<string | null>(null);

  useEffect(() => {
    loadTracks();
  }, [id]);

  const loadTracks = async () => {
    setLoading(true);
    try {
      let hackathonId = id;
      // If no ID in URL, find the latest hackathon
      if (!hackathonId) {
        const hackathons = await api.getHackathons();
        if (hackathons.length > 0) {
          hackathonId = hackathons[0].id;
        }
      }
      if (hackathonId) {
        const hackathon = await api.getHackathon(hackathonId);
        setHackathonName(hackathon.name);
      }
    } catch (e) {
      console.error('Failed to load hackathon:', e);
    }
    setLoading(false);
  };

  const trackCardStyle = (track: Track, isHovered: boolean): React.CSSProperties => ({
    background: CARD_BG,
    border: `1px solid ${isHovered ? track.color : BORDER}`,
    borderRadius: RADIUS.lg,
    padding: isMobile ? SPACE.md : SPACE.lg,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    transform: isHovered ? 'translateY(-4px)' : 'translateY(0)',
    boxShadow: isHovered ? `0 8px 32px ${track.color}20` : 'none',
    position: 'relative',
    overflow: 'hidden',
  });

  const glowEffect = (color: string): React.CSSProperties => ({
    position: 'absolute',
    top: -50,
    right: -50,
    width: 150,
    height: 150,
    borderRadius: '50%',
    background: `radial-gradient(circle, ${color}30 0%, transparent 70%)`,
    pointerEvents: 'none',
  });

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl }}>
        <div style={{ fontSize: 48, marginBottom: SPACE.md, animation: 'pulse 2s infinite' }}>🌙</div>
        <p style={{ color: TEXT_MUTED }}>Loading tracks from orbit...</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: SPACE.xl }}>
        <div style={{ fontSize: 64, marginBottom: SPACE.md }}>🌌</div>
        <h1 style={{ ...TYPO.h1, marginBottom: SPACE.sm }}>
          {hackathonName} Tracks
        </h1>
        <p style={{ color: TEXT_SECONDARY, fontSize: 16, maxWidth: 600, margin: '0 auto' }}>
          Choose your mission. Each track offers unique challenges, prizes, and resources to help you build something stellar.
        </p>
      </div>

      {/* Tracks Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, 1fr)',
        gap: SPACE.lg,
        marginBottom: SPACE.xl,
      }}>
        {tracks.map((track) => {
          const isHovered = hoveredTrack === track.id;
          return (
            <div
              key={track.id}
              style={trackCardStyle(track, isHovered)}
              onMouseEnter={() => setHoveredTrack(track.id)}
              onMouseLeave={() => setHoveredTrack(null)}
              onClick={() => setSelectedTrack(track)}
            >
              <div style={glowEffect(track.color)} />
              
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: SPACE.md, position: 'relative', zIndex: 1 }}>
                <div style={{
                  width: 56,
                  height: 56,
                  borderRadius: RADIUS.md,
                  background: `${track.color}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 28,
                  flexShrink: 0,
                }}>
                  {track.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <h3 style={{ ...TYPO.h3, marginBottom: SPACE.xs, color: track.color }}>
                    {track.name}
                  </h3>
                  <p style={{ color: TEXT_SECONDARY, fontSize: 14, marginBottom: SPACE.sm, lineHeight: 1.5 }}>
                    {track.description}
                  </p>
                  <div style={{
                    display: 'inline-block',
                    padding: '4px 12px',
                    borderRadius: RADIUS.full,
                    background: `${track.color}20`,
                    color: track.color,
                    fontSize: 13,
                    fontWeight: 600,
                  }}>
                    🏆 {track.prize}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Track Detail Modal */}
      {selectedTrack && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(10,10,18,0.9)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: SPACE.md,
          }}
          onClick={() => setSelectedTrack(null)}
        >
          <div
            style={{
              background: CARD_BG,
              border: `1px solid ${selectedTrack.color}`,
              borderRadius: RADIUS.lg,
              padding: isMobile ? SPACE.lg : SPACE.xl,
              maxWidth: 600,
              width: '100%',
              maxHeight: '90vh',
              overflow: 'auto',
              position: 'relative',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={glowEffect(selectedTrack.color)} />
            
            <button
              onClick={() => setSelectedTrack(null)}
              style={{
                position: 'absolute',
                top: SPACE.md,
                right: SPACE.md,
                background: 'none',
                border: 'none',
                color: TEXT_MUTED,
                fontSize: 24,
                cursor: 'pointer',
                padding: 0,
                width: 32,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              ×
            </button>

            <div style={{ textAlign: 'center', marginBottom: SPACE.lg, position: 'relative', zIndex: 1 }}>
              <div style={{ fontSize: 56, marginBottom: SPACE.sm }}>{selectedTrack.icon}</div>
              <h2 style={{ ...TYPO.h2, color: selectedTrack.color, marginBottom: SPACE.xs }}>
                {selectedTrack.name}
              </h2>
              <p style={{ color: TEXT_SECONDARY }}>{selectedTrack.description}</p>
            </div>

            <div style={{ marginBottom: SPACE.lg, position: 'relative', zIndex: 1 }}>
              <h4 style={{ ...TYPO['label-caps'], color: selectedTrack.color, marginBottom: SPACE.sm }}>
                Judging Criteria
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACE.sm }}>
                {selectedTrack.criteria.map((criterion, idx) => (
                  <span
                    key={idx}
                    style={{
                      padding: '6px 12px',
                      borderRadius: RADIUS.md,
                      background: INPUT_BG,
                      color: TEXT_PRIMARY,
                      fontSize: 13,
                    }}
                  >
                    {criterion}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: SPACE.lg, position: 'relative', zIndex: 1 }}>
              <h4 style={{ ...TYPO['label-caps'], color: selectedTrack.color, marginBottom: SPACE.sm }}>
                Prize
              </h4>
              <div style={{
                padding: SPACE.md,
                borderRadius: RADIUS.md,
                background: `${selectedTrack.color}10`,
                border: `1px solid ${selectedTrack.color}30`,
                color: selectedTrack.color,
                fontSize: 18,
                fontWeight: 700,
                textAlign: 'center',
              }}>
                {selectedTrack.prize}
              </div>
            </div>

            {selectedTrack.resources && (
              <div style={{ position: 'relative', zIndex: 1 }}>
                <h4 style={{ ...TYPO['label-caps'], color: selectedTrack.color, marginBottom: SPACE.sm }}>
                  Resources
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
                  {selectedTrack.resources.map((resource, idx) => (
                    <a
                      key={idx}
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: SPACE.sm,
                        padding: '10px 14px',
                        borderRadius: RADIUS.md,
                        background: INPUT_BG,
                        color: CYAN,
                        textDecoration: 'none',
                        fontSize: 14,
                      }}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: 18 }}>link</span>
                      {resource.name}
                    </a>
                  ))}
                </div>
              </div>
            )}

            <div style={{ marginTop: SPACE.lg, textAlign: 'center', position: 'relative', zIndex: 1 }}>
              <Link
                to={id ? `/hackathons/${id}/register` : '/register'}
                style={{
                  display: 'inline-block',
                  padding: '12px 32px',
                  background: selectedTrack.color,
                  borderRadius: RADIUS.md,
                  color: TEXT_WHITE,
                  textDecoration: 'none',
                  fontSize: 16,
                  fontWeight: 700,
                }}
              >
                Register for This Track →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* CTA Section */}
      <div style={{
        background: `linear-gradient(135deg, ${PRIMARY_BG20} 0%, ${CYAN_BG20} 100%)`,
        border: `1px solid ${BORDER}`,
        borderRadius: RADIUS.lg,
        padding: isMobile ? SPACE.lg : SPACE.xl,
        textAlign: 'center',
      }}>
        <h3 style={{ ...TYPO.h3, marginBottom: SPACE.sm }}>
          Not sure which track to choose?
        </h3>
        <p style={{ color: TEXT_SECONDARY, marginBottom: SPACE.md, maxWidth: 500, margin: '0 auto ' + SPACE.md + 'px' }}>
          You can explore multiple tracks and decide later. The best projects often combine elements from different categories.
        </p>
        {user ? (
          <Link
            to={id ? `/hackathons/${id}/hacker-dashboard` : '/dashboard'}
            style={{
              display: 'inline-block',
              padding: '12px 28px',
              background: PRIMARY,
              borderRadius: RADIUS.md,
              color: TEXT_WHITE,
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
            Go to Dashboard
          </Link>
        ) : (
          <Link
            to="/auth"
            style={{
              display: 'inline-block',
              padding: '12px 28px',
              background: PRIMARY,
              borderRadius: RADIUS.md,
              color: TEXT_WHITE,
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
            Sign In to Register
          </Link>
        )}
      </div>
    </div>
  );
}
