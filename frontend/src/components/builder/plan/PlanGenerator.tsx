// ============================================================
// Plan Generator - Loading/Generating state for AI plan creation
// ============================================================

import { useEffect, useState } from 'react';
import {
  CARD_BG,
  PRIMARY,
  CYAN,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  SPACE,
  RADIUS,
} from '../../../theme';

interface PlanGeneratorProps {
  projectName: string;
  projectDescription: string;
  hackathonId?: string;
  onPlanGenerated: (plan: GeneratedPlan) => void;
  onError: (error: string) => void;
}

export interface GeneratedPlan {
  name: string;
  description: string;
  targetTrack: string;
  estimatedHours: number;
  techStack: string[];
  tasks: PlanTask[];
  stretchGoals: string[];
}

export interface PlanTask {
  id: string;
  description: string;
  estimatedMinutes: number;
  dependencies: string[];
}

const loadingMessages = [
  'Analyzing hackathon tracks...',
  'Evaluating project scope...',
  'Designing technical architecture...',
  'Breaking down into tasks...',
  'Estimating time requirements...',
  'Finalizing your roadmap...',
];

export default function PlanGenerator({
  projectName,
  projectDescription,
  hackathonId,
  onPlanGenerated,
  onError,
}: PlanGeneratorProps) {
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  // Cycle through loading messages
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentMessageIndex((prev) => (prev + 1) % loadingMessages.length);
      setProgress((prev) => Math.min(prev + 15, 90));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Generate plan on mount
  useEffect(() => {
    generatePlan();
  }, []);

  const generatePlan = async () => {
    try {
      const token = localStorage.getItem('auth_token') || '';
      const baseUrl = import.meta.env.VITE_API_URL || '/api';

      const response = await fetch(`${baseUrl}/assistant/generate-plan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          project_name: projectName,
          project_description: projectDescription,
          hackathon_id: hackathonId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to generate plan');
      }

      const plan: GeneratedPlan = await response.json();
      setProgress(100);

      // Small delay to show completion
      setTimeout(() => {
        onPlanGenerated(plan);
      }, 500);
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Failed to generate plan');
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        padding: SPACE.lg,
        background: CARD_BG,
      }}
    >
      {/* Animated spinner */}
      <div
        style={{
          position: 'relative',
          width: 80,
          height: 80,
          marginBottom: SPACE.lg,
        }}
      >
        {/* Outer ring */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: `3px solid ${PRIMARY}30`,
            borderTopColor: PRIMARY,
            animation: 'spin 1.5s linear infinite',
          }}
        />
        {/* Inner ring */}
        <div
          style={{
            position: 'absolute',
            inset: 12,
            borderRadius: '50%',
            border: `3px solid ${CYAN}30`,
            borderBottomColor: CYAN,
            animation: 'spin 1s linear infinite reverse',
          }}
        />
        {/* Center icon */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 28,
          }}
        >
          🤖
        </div>
      </div>

      {/* Title */}
      <h2
        style={{
          margin: 0,
          marginBottom: SPACE.sm,
          color: TEXT_PRIMARY,
          fontSize: 20,
          fontWeight: 600,
        }}
      >
        Building Your Project Plan
      </h2>

      {/* Project name */}
      <p
        style={{
          margin: 0,
          marginBottom: SPACE.lg,
          color: TEXT_SECONDARY,
          fontSize: 14,
          maxWidth: 400,
          textAlign: 'center',
        }}
      >
        {projectName}
      </p>

      {/* Progress bar */}
      <div
        style={{
          width: '100%',
          maxWidth: 300,
          height: 4,
          background: `${PRIMARY}20`,
          borderRadius: RADIUS.full,
          overflow: 'hidden',
          marginBottom: SPACE.md,
        }}
      >
        <div
          style={{
            width: `${progress}%`,
            height: '100%',
            background: `linear-gradient(90deg, ${PRIMARY}, ${CYAN})`,
            borderRadius: RADIUS.full,
            transition: 'width 0.3s ease',
          }}
        />
      </div>

      {/* Loading message */}
      <p
        style={{
          margin: 0,
          color: TEXT_SECONDARY,
          fontSize: 14,
          textAlign: 'center',
          minHeight: 20,
        }}
      >
        {loadingMessages[currentMessageIndex]}
      </p>

      {/* CSS for spin animation */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
