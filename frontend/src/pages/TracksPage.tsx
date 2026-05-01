import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useAuth } from '../contexts/AuthContext';
import * as api from '../services/api';
import {
  PRIMARY, PRIMARY_BG20, CYAN, CYAN_BG20,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, BORDER,
  TYPO, SPACE, RADIUS,
} from '../theme';

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
  criteria: string[];
  resources: TrackResource[];
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

  useEffect(() => {
    loadTracks();
  }, [id]);

  const loadTracks = async () => {
    setLoading(true);
    try {
      let hId = id;
      if (!hId) {
        const hackathons = await api.getHackathons();
        if (hackathons.length > 0) hId = hackathons[0].id;
      }
      if (hId) {
        setHackathonId(hId);
        const hackathon = await api.getHackathon(hId);
        setHackathonName(hackathon.name);
        try {
          const data = await api.getHackathonTracks(hId);
          if (data.tracks && data.tracks.length > 0) {
            setTracks(data.tracks);
          }
        } catch {
          // Use fallback tracks if API fails
        }
      }
    } catch (e) {
      console.error('Failed to load tracks:', e);
    }
    setLoading(false);
  };

  const toggleTrack = (trackId: string) => {
    setExpandedTrack(expandedTrack === trackId ? null : trackId);
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: SPACE.xl }}>
        <div style={{ fontSize: 48, marginBottom: SPACE.md }}>🌙</div>
        <p style={{ color: TEXT_MUTED }}>Loading tracks from orbit...</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: SPACE.xl }}>
        <div style={{ fontSize: 56, marginBottom: SPACE.md }}>🛰️</div>
        <h1 style={{ ...TYPO.h1, marginBottom: SPACE.sm }}>
          {hackathonName ? `${hackathonName} Tracks` : 'Challenge Tracks'}
        </h1>
        <p style={{ color: TEXT_SECONDARY, fontSize: 16, maxWidth: 600, margin: '0 auto' }}>
          Six mission tracks. Each with its own challenge prompt, judging criteria, prizes, and curated resources. Choose your orbit.
        </p>
      </div>

      {/* Tracks Accordion */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.md, marginBottom: SPACE.xl }}>
        {tracks.map((track) => {
          const isExpanded = expandedTrack === track.id;
          return (
            <div
              key={track.id}
              style={{
                background: CARD_BG,
                border: `1px solid ${isExpanded ? track.color : BORDER}`,
                borderLeft: `4px solid ${track.color}`,
                borderRadius: RADIUS.lg,
                overflow: 'hidden',
                transition: 'all 0.25s ease',
                boxShadow: isExpanded ? `0 4px 24px ${track.color}20` : 'none',
              }}
            >
              {/* Header — always visible */}
              <button
                onClick={() => toggleTrack(track.id)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.md,
                  padding: isMobile ? SPACE.md : SPACE.lg,
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                  color: TEXT_PRIMARY,
                }}
              >
                <div style={{
                  width: 56, height: 56, borderRadius: RADIUS.md,
                  background: `${track.color}20`, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  fontSize: 28, flexShrink: 0,
                }}>
                  {track.icon || '🛸'}
                </div>
                <div style={{ flex: 1 }}>
                  <h3 style={{ ...TYPO.h3, marginBottom: 4, color: isExpanded ? track.color : TEXT_PRIMARY }}>
                    {track.name}
                  </h3>
                  <p style={{ color: TEXT_SECONDARY, fontSize: 14, margin: 0 }}>
                    {track.description}
                  </p>
                </div>
                <div style={{
                  fontSize: 20, color: TEXT_MUTED,
                  transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.25s ease', flexShrink: 0,
                }}>
                  ▾
                </div>
              </button>

              {/* Expanded content */}
              <div style={{
                maxHeight: isExpanded ? '2000px' : '0px',
                overflow: 'hidden',
                transition: 'max-height 0.35s ease',
                padding: isExpanded ? (isMobile ? `0 ${SPACE.md}px ${SPACE.md}px` : `0 ${SPACE.lg}px ${SPACE.lg}px`) : `0 ${isMobile ? SPACE.md : SPACE.lg}px`,
                opacity: isExpanded ? 1 : 0,
                transitionProperty: 'max-height, opacity, padding',
                transitionDuration: '0.35s, 0.25s, 0.35s',
                transitionTimingFunction: 'ease',
              }}>
                <div>
                  {/* Challenge prompt */}
                  <div style={{
                    background: `${track.color}10`,
                    border: `1px solid ${track.color}30`,
                    borderRadius: RADIUS.md,
                    padding: SPACE.md,
                    marginBottom: SPACE.lg,
                    whiteSpace: 'pre-line',
                    fontSize: 15,
                    color: TEXT_PRIMARY,
                    lineHeight: 1.7,
                  }}>
                    {track.challenge || track.description}
                  </div>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
                    gap: SPACE.lg,
                  }}>
                    {/* Left column */}
                    <div>
                      <h4 style={{
                        ...TYPO['label-caps'], color: track.color,
                        marginBottom: SPACE.sm, display: 'flex', alignItems: 'center', gap: 6,
                      }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>gavel</span>
                        Judging Criteria
                      </h4>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACE.xs, marginBottom: SPACE.lg }}>
                        {(track.criteria || []).map((criterion, idx) => (
                          <span key={idx} style={{
                            padding: '6px 12px', borderRadius: RADIUS.full,
                            background: `${track.color}15`, color: track.color,
                            fontSize: 13, fontWeight: 500,
                          }}>
                            {criterion}
                          </span>
                        ))}
                      </div>

                      <h4 style={{
                        ...TYPO['label-caps'], color: track.color,
                        marginBottom: SPACE.sm, display: 'flex', alignItems: 'center', gap: 6,
                      }}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>trophy</span>
                        Prize
                      </h4>
                      <div style={{
                        padding: SPACE.md, borderRadius: RADIUS.md,
                        background: `${track.color}10`, border: `1px solid ${track.color}30`,
                        color: track.color, fontSize: 18, fontWeight: 700, textAlign: 'center',
                      }}>
                        {track.prize || 'Prize TBA'}
                      </div>
                    </div>

                    {/* Right column */}
                    <div>
                      {(track.resources && track.resources.length > 0) && (
                        <>
                          <h4 style={{
                            ...TYPO['label-caps'], color: track.color,
                            marginBottom: SPACE.sm, display: 'flex', alignItems: 'center', gap: 6,
                          }}>
                            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>bookmark</span>
                            Starter Resources
                          </h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm, marginBottom: SPACE.lg }}>
                            {track.resources.map((resource, idx) => (
                              <a
                                key={idx}
                                href={resource.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                  display: 'flex', alignItems: 'center', gap: SPACE.sm,
                                  padding: '10px 14px', borderRadius: RADIUS.md,
                                  background: INPUT_BG, color: CYAN,
                                  textDecoration: 'none', fontSize: 14, fontWeight: 500,
                                  border: `1px solid ${BORDER}`,
                                }}
                              >
                                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>link</span>
                                {resource.name}
                              </a>
                            ))}
                          </div>
                        </>
                      )}

                      {/* Register CTA */}
                      <Link
                        to={hackathonId ? `/hackathons/${hackathonId}/register` : '/register'}
                        style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                          width: '100%', padding: '12px 24px',
                          background: track.color, borderRadius: RADIUS.md,
                          color: TEXT_WHITE, textDecoration: 'none',
                          fontSize: 15, fontWeight: 700, boxSizing: 'border-box',
                          marginTop: track.resources && track.resources.length > 0 ? 0 : SPACE.md,
                        }}
                      >
                        Register for {track.name} →
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom CTA */}
      <div style={{
        background: `linear-gradient(135deg, ${PRIMARY_BG20} 0%, ${CYAN_BG20} 100%)`,
        border: `1px solid ${BORDER}`, borderRadius: RADIUS.lg,
        padding: isMobile ? SPACE.lg : SPACE.xl, textAlign: 'center',
      }}>
        <h3 style={{ ...TYPO.h3, marginBottom: SPACE.sm }}>Not sure which track to choose?</h3>
        <p style={{ color: TEXT_SECONDARY, marginBottom: SPACE.lg, maxWidth: 500, margin: `0 auto ${SPACE.lg}px` }}>
          You can explore all tracks and decide later. The best projects often bridge multiple domains.
        </p>
        {user ? (
          <Link
            to={hackathonId ? `/hackathons/${hackathonId}/hacker-dashboard` : '/dashboard'}
            style={{
              display: 'inline-block', padding: '12px 28px',
              background: PRIMARY, borderRadius: RADIUS.md,
              color: TEXT_WHITE, textDecoration: 'none', fontWeight: 600,
            }}
          >
            Go to Dashboard
          </Link>
        ) : (
          <Link
            to="/auth"
            style={{
              display: 'inline-block', padding: '12px 28px',
              background: PRIMARY, borderRadius: RADIUS.md,
              color: TEXT_WHITE, textDecoration: 'none', fontWeight: 600,
            }}
          >
            Sign In to Register
          </Link>
        )}
      </div>
    </div>
  );
}
