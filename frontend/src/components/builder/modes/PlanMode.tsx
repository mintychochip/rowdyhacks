// ============================================================
// Plan Mode - Main wrapper for AI-generated project planning
// ============================================================

import { useState } from 'react';
import { useBuilderStore } from '../../../stores/builderStore';
import type { BuilderMode } from '../../../types/builder';
import PlanGenerator, { type GeneratedPlan } from '../plan/PlanGenerator';
import PlanDisplay from '../plan/PlanDisplay';
import {
  CARD_BG,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  SPACE,
  RADIUS,
} from '../../../theme';

interface PlanModeProps {
  hackathonId?: string;
  onModeChange?: (mode: BuilderMode) => void;
}

type PlanState = 'input' | 'generating' | 'display' | 'editing';

export default function PlanMode({ hackathonId, onModeChange }: PlanModeProps) {
  const { project, setCurrentPlan, setMode } = useBuilderStore();
  const [planState, setPlanState] = useState<PlanState>(() => {
    // If we already have a project, go straight to generating
    if (project?.name) return 'generating';
    return 'input';
  });
  const [generatedPlan, setGeneratedPlan] = useState<GeneratedPlan | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Input state for project details
  const [projectName, setProjectName] = useState(project?.name || '');
  const [projectDescription, setProjectDescription] = useState(
    project?.description || ''
  );

  const handleGenerate = () => {
    if (!projectName.trim()) return;
    setError(null);
    setPlanState('generating');
  };

  const handlePlanGenerated = (plan: GeneratedPlan) => {
    setGeneratedPlan(plan);
    setPlanState('display');

    // Save to store
    const now = new Date().toISOString();
    setCurrentPlan({
      id: `plan-${Date.now()}`,
      title: plan.name,
      description: plan.description,
      projectType: inferProjectType(plan.techStack),
      tasks: plan.tasks.map((t) => ({
        id: t.id,
        description: t.description,
        status: 'pending',
        dependencies: t.dependencies,
      })),
      createdAt: now,
      updatedAt: now,
    });
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
    setPlanState('input');
  };

  const handleAcceptPlan = () => {
    // Switch to build mode
    setMode('build');
    if (onModeChange) {
      onModeChange('build');
    }
  };

  const handleEditPlan = () => {
    setPlanState('editing');
    // In a full implementation, this would open an editing interface
    // For now, we'll just go back to input with the current values
    setPlanState('input');
  };

  const handleBackToChat = () => {
    setMode('chat');
    if (onModeChange) {
      onModeChange('chat');
    }
  };

  // Helper to infer project type from tech stack
  const inferProjectType = (techStack: string[]): string => {
    const techs = techStack.map((t) => t.toLowerCase());
    if (techs.some((t) => ['react', 'vue', 'angular', 'svelte'].includes(t))) {
      return 'web-app';
    }
    if (techs.some((t) => ['react native', 'flutter', 'ios', 'android'].includes(t))) {
      return 'mobile-app';
    }
    if (techs.some((t) => ['fastapi', 'express', 'django', 'flask'].includes(t))) {
      return 'api';
    }
    if (techs.some((t) => ['python', 'bash', 'shell'].includes(t))) {
      return 'script';
    }
    return 'web-app';
  };

  // Input form view
  if (planState === 'input') {
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
        <div style={{ maxWidth: 500, width: '100%' }}>
          <h2
            style={{
              margin: 0,
              marginBottom: SPACE.sm,
              fontSize: 24,
              fontWeight: 700,
              color: TEXT_PRIMARY,
              textAlign: 'center',
            }}
          >
            Create Your Project Plan
          </h2>
          <p
            style={{
              margin: 0,
              marginBottom: SPACE.lg,
              color: TEXT_SECONDARY,
              textAlign: 'center',
              fontSize: 14,
            }}
          >
            Tell us about your project idea and our AI will create a detailed roadmap.
          </p>

          {error && (
            <div
              style={{
                padding: SPACE.md,
                marginBottom: SPACE.md,
                background: 'rgba(239, 68, 68, 0.2)',
                borderRadius: RADIUS.md,
                color: '#ef4444',
                fontSize: 14,
              }}
            >
              {error}
            </div>
          )}

          <div style={{ marginBottom: SPACE.md }}>
            <label
              style={{
                display: 'block',
                marginBottom: SPACE.xs,
                color: TEXT_SECONDARY,
                fontSize: 14,
                fontWeight: 500,
              }}
            >
              Project Name
            </label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g., AI Study Buddy"
              style={{
                width: '100%',
                padding: `${SPACE.sm}px ${SPACE.md}px`,
                background: '#334155',
                border: '1px solid #475569',
                borderRadius: RADIUS.md,
                color: TEXT_PRIMARY,
                fontSize: 14,
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          <div style={{ marginBottom: SPACE.lg }}>
            <label
              style={{
                display: 'block',
                marginBottom: SPACE.xs,
                color: TEXT_SECONDARY,
                fontSize: 14,
                fontWeight: 500,
              }}
            >
              Description
            </label>
            <textarea
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              placeholder="Describe what you want to build..."
              rows={4}
              style={{
                width: '100%',
                padding: `${SPACE.sm}px ${SPACE.md}px`,
                background: '#334155',
                border: '1px solid #475569',
                borderRadius: RADIUS.md,
                color: TEXT_PRIMARY,
                fontSize: 14,
                outline: 'none',
                resize: 'vertical',
                boxSizing: 'border-box',
                fontFamily: 'inherit',
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: SPACE.md }}>
            <button
              onClick={handleGenerate}
              disabled={!projectName.trim()}
              style={{
                flex: 1,
                padding: `${SPACE.sm}px ${SPACE.md}px`,
                background: !projectName.trim() ? '#475569' : '#2563eb',
                color: '#fff',
                border: 'none',
                borderRadius: RADIUS.md,
                cursor: !projectName.trim() ? 'not-allowed' : 'pointer',
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Generate Plan
            </button>
            <button
              onClick={handleBackToChat}
              style={{
                padding: `${SPACE.sm}px ${SPACE.md}px`,
                background: 'transparent',
                color: TEXT_SECONDARY,
                border: '1px solid #475569',
                borderRadius: RADIUS.md,
                cursor: 'pointer',
                fontSize: 14,
              }}
            >
              Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Generating view
  if (planState === 'generating') {
    return (
      <PlanGenerator
        projectName={projectName}
        projectDescription={projectDescription}
        hackathonId={hackathonId}
        onPlanGenerated={handlePlanGenerated}
        onError={handleError}
      />
    );
  }

  // Display view
  if (planState === 'display' && generatedPlan) {
    return (
      <PlanDisplay
        plan={generatedPlan}
        onAccept={handleAcceptPlan}
        onEdit={handleEditPlan}
        onBackToChat={handleBackToChat}
      />
    );
  }

  // Fallback (shouldn't happen)
  return null;
}
