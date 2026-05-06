import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';

interface TrackResource {
  name: string;
  url: string;
}

interface Track {
  id: string;
  name: string;
  description: string;
  challenge: string;
  icon: string;
  color: string;
  prize: string;
  track_type?: string | null;
  criteria: string[];
  resources: TrackResource[];
}

interface TrackCardProps {
  track: Track;
  hackathonId: string | undefined;
  isMobile: boolean;
  expandedTrack: string | null;
  toggleTrack: (id: string) => void;
}

// Icons
const ChevronDownIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m6 9 6 6 6-6"/>
  </svg>
);

const ExternalLinkIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
    <polyline points="15 3 21 3 21 9"/>
    <line x1="10" x2="21" y1="14" y2="3"/>
  </svg>
);

const TrophyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>
    <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>
    <path d="M4 22h16"/>
    <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>
    <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>
    <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
  </svg>
);

const GavelIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m14 13-7 7"/>
    <path d="M19.5 2.5 21 4l-6.5 6.5"/>
    <path d="m14 6-7 7"/>
    <path d="m7.5 12.5 2 2"/>
    <path d="m6.5 13.5 2 2"/>
    <path d="m5.5 14.5 2 2"/>
    <path d="M4 20l2 2"/>
  </svg>
);

const BookmarkIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>
  </svg>
);

const ArrowRightIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14"/>
    <path d="m12 5 7 7-7 7"/>
  </svg>
);

// Track icon mapping
const TRACK_ICONS: Record<string, string> = {
  'Deep Space Exploration': '🚀',
  'Orbital Commerce': '💎',
  'Cosmic Commons': '🌌',
  'Nebula Arts': '✨',
  'Mission Control AI': '🤖',
  'Lunar Settlements': '🌕',
};

function TrackCard({ track, hackathonId, isMobile, expandedTrack, toggleTrack }: TrackCardProps) {
  const isExpanded = expandedTrack === track.id;
  const accentColor = track.color || 'var(--accent-primary)';

  return (
    <div
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid',
        borderColor: isExpanded ? 'var(--border-strong)' : 'var(--border-default)',
        borderRadius: 12,
        overflow: 'hidden',
        transition: 'all 200ms ease',
      }}
    >
      {/* Card Header */}
      <button
        onClick={() => toggleTrack(track.id)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: isMobile ? '16px' : '20px',
          background: isExpanded ? 'var(--bg-tertiary)' : 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
          transition: 'background 150ms ease',
        }}
      >
        {/* Icon */}
        <div style={{
          width: 48,
          height: 48,
          borderRadius: 12,
          background: isExpanded ? `${accentColor}20` : 'var(--bg-tertiary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 24,
          flexShrink: 0,
          transition: 'all 150ms ease',
          border: '1px solid',
          borderColor: isExpanded ? `${accentColor}40` : 'var(--border-default)',
        }}>
          {TRACK_ICONS[track.name] || track.icon || '🎯'}
        </div>

        {/* Title & Description */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={{
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 4,
            letterSpacing: '-0.01em',
          }}>
            {track.name}
          </h3>
          <p style={{
            color: 'var(--text-secondary)',
            fontSize: 13,
            margin: 0,
            lineHeight: 1.5,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}>
            {track.description}
          </p>
        </div>

        {/* Prize Badge */}
        {track.prize && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: 'var(--accent-subtle)',
            borderRadius: 100,
            fontSize: 12,
            fontWeight: 600,
            color: 'var(--accent-primary)',
            flexShrink: 0,
          }}>
            <TrophyIcon />
            {track.prize.split(' ')[0]}
          </div>
        )}

        {/* Expand Chevron */}
        <div style={{
          color: 'var(--text-muted)',
          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
          transition: 'transform 200ms ease',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <ChevronDownIcon />
        </div>
      </button>

      {/* Expanded Content */}
      <div style={{
        maxHeight: isExpanded ? '2000px' : '0px',
        overflow: 'hidden',
        transition: 'max-height 400ms cubic-bezier(0.4, 0, 0.2, 1)',
      }}>
        <div style={{
          padding: isMobile ? '0 16px 16px' : '0 20px 20px',
          borderTop: '1px solid var(--border-subtle)',
        }}>
          <TrackDetails track={track} hackathonId={hackathonId} isMobile={isMobile} />
        </div>
      </div>
    </div>
  );
}

interface TrackDetailsProps {
  track: Track;
  hackathonId: string | undefined;
  isMobile: boolean;
}

function TrackDetails({ track, hackathonId, isMobile }: TrackDetailsProps) {
  const accentColor = track.color || 'var(--accent-primary)';

  return (
    <div style={{ paddingTop: 20 }}>
      {/* Challenge Section */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-default)',
        borderRadius: 10,
        padding: 16,
        marginBottom: 20,
      }}>
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: 14,
          lineHeight: 1.7,
          margin: 0,
          whiteSpace: 'pre-line',
        }}>
          {track.challenge || track.description}
        </p>
      </div>

      {/* Two Column Layout */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
        gap: 20,
      }}>
        {/* Left Column - Criteria & Prize */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Judging Criteria */}
          <div>
            <h4 style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-muted)',
              marginBottom: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <GavelIcon />
              Judging Criteria
            </h4>
            <div style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 8,
            }}>
              {(track.criteria || []).map((criterion, idx) => (
                <span key={idx} style={{
                  padding: '6px 12px',
                  borderRadius: 6,
                  background: 'var(--bg-tertiary)',
                  color: 'var(--text-secondary)',
                  fontSize: 12,
                  fontWeight: 500,
                  border: '1px solid var(--border-default)',
                }}>
                  {criterion}
                </span>
              ))}
            </div>
          </div>

          {/* Prize */}
          <div>
            <h4 style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-muted)',
              marginBottom: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <TrophyIcon />
              Prize
            </h4>
            <div style={{
              padding: 14,
              borderRadius: 10,
              background: 'var(--accent-subtle)',
              border: '1px solid rgba(139, 92, 246, 0.2)',
              color: 'var(--accent-primary)',
              fontSize: 16,
              fontWeight: 600,
              textAlign: 'center',
            }}>
              {track.prize || 'Prize TBA'}
            </div>
          </div>
        </div>

        {/* Right Column - Resources & CTA */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Resources */}
          {(track.resources && track.resources.length > 0) && (
            <div>
              <h4 style={{
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: 'var(--text-muted)',
                marginBottom: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <BookmarkIcon />
                Starter Resources
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {track.resources.map((resource, idx) => (
                  <a
                    key={idx}
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: 12,
                      padding: '10px 14px',
                      borderRadius: 8,
                      background: 'var(--bg-tertiary)',
                      color: 'var(--text-secondary)',
                      textDecoration: 'none',
                      fontSize: 13,
                      fontWeight: 500,
                      border: '1px solid var(--border-default)',
                      transition: 'all 150ms ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--bg-secondary)';
                      e.currentTarget.style.color = 'var(--text-primary)';
                      e.currentTarget.style.borderColor = 'var(--border-strong)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'var(--bg-tertiary)';
                      e.currentTarget.style.color = 'var(--text-secondary)';
                      e.currentTarget.style.borderColor = 'var(--border-default)';
                    }}
                  >
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {resource.name}
                    </span>
                    <ExternalLinkIcon />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* CTA Button */}
          <Link
            to={hackathonId ? `/hackathons/${hackathonId}/register` : '/register'}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              width: '100%',
              padding: '12px 20px',
              background: 'var(--accent-primary)',
              borderRadius: 10,
              color: 'white',
              textDecoration: 'none',
              fontSize: 14,
              fontWeight: 500,
              marginTop: 'auto',
              transition: 'all 150ms ease',
              boxShadow: '0 4px 14px rgba(139, 92, 246, 0.3)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--accent-primary-hover)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--accent-primary)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            Register for {track.name}
            <ArrowRightIcon />
          </Link>
        </div>
      </div>
    </div>
  );
}

const FALLBACK_TRACKS: Track[] = [
  {
    id: '1', name: 'Deep Space Exploration', description: 'Push the boundaries of space tech. Build tools for satellite data analysis, mission planning, or astronaut support systems.',
    challenge: 'Your mission: create a working prototype that solves a real problem in space exploration. This could be a satellite trajectory planner, a telemetry dashboard, a radiation exposure calculator for astronauts, or an AI system that classifies celestial objects from telescope imagery.\n\nLooking for projects that demonstrate technical depth — bonus points for using real NASA/ESA datasets or simulating realistic physics.',
    icon: '🚀', color: '#8b5cf6', prize: '$1,000 + SpaceX Tour',
    criteria: ['Innovation', 'Technical Complexity', 'Space Applicability', 'Use of Real Data'],
    resources: [{ name: 'NASA Open APIs', url: 'https://api.nasa.gov/' }, { name: 'Space-Track.org', url: 'https://www.space-track.org/' }],
  },
  {
    id: '2', name: 'Orbital Commerce', description: 'Create the future of space economy. Develop marketplace platforms, logistics tools, or financial systems for the space age.',
    challenge: 'The commercialization of low Earth orbit is accelerating. Build a tool, platform, or system that enables commerce in space — a marketplace for satellite services, a launch logistics scheduler, or a DeFi protocol for satellite time-sharing.',
    icon: '💎', color: '#06b6d4', prize: '$800 + Starlink Kit',
    criteria: ['Business Viability', 'UX Design', 'Market Potential', 'Technical Execution'],
    resources: [{ name: 'Space Economy Report', url: 'https://spacefoundation.org/research/' }, { name: 'AWS Ground Station', url: 'https://aws.amazon.com/ground-station/' }],
  },
  {
    id: '3', name: 'Cosmic Commons', description: 'Democratize access to space. Build educational tools, citizen science platforms, or community-driven space initiatives.',
    challenge: 'Space shouldn\'t just be for billionaires and government agencies. Create something that makes space more accessible — a VR planetarium for schools, a mobile app for citizen astronomy, or a platform connecting amateur astronomers with researchers.',
    icon: '🌌', color: '#fbbf24', prize: '$600 + Celestron Telescope',
    criteria: ['Social Impact', 'Accessibility', 'Community Engagement', 'Innovation'],
    resources: [{ name: 'Zooniverse Projects', url: 'https://www.zooniverse.org/' }, { name: 'NASA Citizen Science', url: 'https://science.nasa.gov/citizen-science/' }],
  },
  {
    id: '4', name: 'Nebula Arts', description: 'Where space meets creativity. Develop immersive visualizations, space-themed games, or generative art from astronomical data.',
    challenge: 'Art and science are two sides of the same coin. Create something beautiful grounded in real space data — a WebGL nebula renderer, a procedural planet generator, a sonification of solar wind data, or a mixed reality stargazing app.',
    icon: '✨', color: '#ec4899', prize: '$500 + Wacom Tablet',
    criteria: ['Aesthetic Quality', 'Technical Execution', 'Concept Originality', 'Emotional Impact'],
    resources: [{ name: 'Three.js Docs', url: 'https://threejs.org/' }, { name: 'ESA Image Archive', url: 'https://www.esa.int/ESA_Multimedia/Images' }],
  },
  {
    id: '5', name: 'Mission Control AI', description: 'Apply artificial intelligence to space operations. Build ML models for anomaly detection, predictive maintenance, or autonomous navigation.',
    challenge: 'AI is transforming how we operate in space. Train a model to detect anomalies in telemetry data, build a reinforcement learning agent for autonomous docking, create an LLM-powered mission planning assistant, or develop computer vision for satellite inspection.',
    icon: '🤖', color: '#10b981', prize: '$1,200 + NVIDIA Jetson Kit',
    criteria: ['AI Innovation', 'Model Performance', 'Problem Relevance', 'Presentation Clarity'],
    resources: [{ name: 'NASA Telemetry Data', url: 'https://data.nasa.gov/' }, { name: 'PyTorch Docs', url: 'https://pytorch.org/docs/' }],
  },
  {
    id: '6', name: 'Lunar Settlements', description: 'Design for life beyond Earth. Create habitat concepts, life support simulations, and resource utilization tools for off-world colonies.',
    challenge: 'If we\'re going to stay on the Moon, we need to figure out how to live there. Design a system for sustaining human life off-world — a hydroponics controller for microgravity, a 3D habitat layout tool using in-situ resources, or a crew psychology dashboard.',
    icon: '🌕', color: '#f97316', prize: '$900 + 3D Printer',
    criteria: ['Systems Thinking', 'Feasibility', 'Innovation', 'Sustainability'],
    resources: [{ name: 'NASA Artemis Program', url: 'https://www.nasa.gov/artemis/' }, { name: 'Lunar ISRU Papers', url: 'https://www.lpi.usra.edu/' }],
  },
];

export default function TracksPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { isMobile } = useMediaQuery();
  const [tracks, setTracks] = useState<Track[]>(FALLBACK_TRACKS);
  const [hackathonName, setHackathonName] = useState('');
  const [hackathonId, setHackathonId] = useState<string | undefined>(id);
  const [loading, setLoading] = useState(true);
  const [expandedTrack, setExpandedTrack] = useState<string | null>(null);

  const loadTracks = useCallback(async () => {
    try {
      let hId = id;
      if (!hId) {
        const hackathons = await api.getHackathons();
        if (hackathons.length > 0) hId = hackathons[0].id;
      }
      if (hId) {
        setHackathonId(hId);
        const [hackathon, tracksData] = await Promise.all([
          api.getHackathon(hId).catch(() => null),
          api.getHackathonTracks(hId).catch(() => ({ tracks: [] })),
        ]);
        if (hackathon) setHackathonName(hackathon.name);
        if (tracksData.tracks && tracksData.tracks.length > 0) {
          setTracks(tracksData.tracks);
        }
      }
    } catch (e) {
      console.error('Failed to load tracks:', e);
    }
    setLoading(false);
  }, [id]);

  useEffect(() => {
    loadTracks();
  }, [loadTracks]);

  const toggleTrack = (trackId: string) => {
    setExpandedTrack(expandedTrack === trackId ? null : trackId);
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      {/* Loading indicator */}
      {loading && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 12,
          padding: '12px 20px',
          marginBottom: 24,
          borderRadius: 10,
          background: 'var(--accent-subtle)',
          color: 'var(--accent-primary)',
          fontSize: 13,
          fontWeight: 500,
        }}>
          <div style={{
            width: 16,
            height: 16,
            border: '2px solid var(--border-default)',
            borderTop: '2px solid var(--accent-primary)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          Loading tracks...
        </div>
      )}

      {/* Header */}
      <div style={{
        textAlign: 'center',
        marginBottom: 40,
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 64,
          height: 64,
          borderRadius: 16,
          background: 'var(--accent-subtle)',
          border: '1px solid rgba(139, 92, 246, 0.2)',
          fontSize: 28,
          marginBottom: 20,
        }}>
          🏆
        </div>
        <h1 style={{
          fontSize: isMobile ? 28 : 32,
          fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
          marginBottom: 12,
        }}>
          {hackathonName ? `${hackathonName} Tracks` : 'Challenge Tracks'}
        </h1>
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: 16,
          lineHeight: 1.6,
          maxWidth: 500,
          margin: '0 auto',
        }}>
          Six mission tracks. Each with its own challenge prompt, judging criteria, prizes, and curated resources.
        </p>
      </div>

      {/* Track Count */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        marginBottom: 24,
        padding: '12px 16px',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-default)',
        borderRadius: 10,
      }}>
        <span style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: 'var(--success)',
        }} />
        <span style={{
          fontSize: 13,
          color: 'var(--text-secondary)',
          fontWeight: 500,
        }}>
          {tracks.length} tracks available
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>
          Click to expand
        </span>
      </div>

      {/* Tracks List */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        marginBottom: 40,
      }}>
        {tracks.map(track => (
          <TrackCard
            key={track.id}
            track={track}
            hackathonId={hackathonId}
            isMobile={isMobile}
            expandedTrack={expandedTrack}
            toggleTrack={toggleTrack}
          />
        ))}
      </div>

      {/* Bottom CTA */}
      <div style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-default)',
        borderRadius: 12,
        padding: isMobile ? '24px' : '32px',
        textAlign: 'center',
      }}>
        <h3 style={{
          fontSize: 18,
          fontWeight: 600,
          color: 'var(--text-primary)',
          marginBottom: 8,
        }}>
          Not sure which track to choose?
        </h3>
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: 14,
          marginBottom: 24,
          maxWidth: 420,
          margin: '0 auto 24px',
        }}>
          You can explore all tracks and decide later. The best projects often bridge multiple domains.
        </p>
        {user ? (
          <Link
            to={hackathonId ? `/hackathons/${hackathonId}/hacker-dashboard` : '/dashboard'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '12px 24px',
              background: 'var(--accent-primary)',
              borderRadius: 10,
              color: 'white',
              textDecoration: 'none',
              fontSize: 14,
              fontWeight: 500,
              transition: 'all 150ms ease',
              boxShadow: '0 4px 14px rgba(139, 92, 246, 0.3)',
            }}
          >
            Go to Dashboard
            <ArrowRightIcon />
          </Link>
        ) : (
          <Link
            to="/auth"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '12px 24px',
              background: 'var(--accent-primary)',
              borderRadius: 10,
              color: 'white',
              textDecoration: 'none',
              fontSize: 14,
              fontWeight: 500,
              transition: 'all 150ms ease',
              boxShadow: '0 4px 14px rgba(139, 92, 246, 0.3)',
            }}
          >
            Sign In to Register
            <ArrowRightIcon />
          </Link>
        )}
      </div>
    </div>
  );
}
