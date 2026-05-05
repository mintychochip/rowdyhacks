// ============================================================
// Plan Display - Shows generated AI plan with tasks and actions
// ============================================================

import { useState } from 'react';
import { useBuilderStore } from '../../../stores/builderStore';
import { generateProject } from '../../../services/builder';
import type { ProjectPlan, ProjectFile } from '../../../types/builder';
import {
  CARD_BG,
  PRIMARY,
  PRIMARY_HOVER,
  CYAN,
  CYAN_BG20,
  GOLD,
  GOLD_BG20,
  SUCCESS,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER,
  BORDER_LIGHT,
  SPACE,
  RADIUS,
  SHADOW,
} from '../../../theme';
import type { GeneratedPlan, PlanTask } from './PlanGenerator';

interface PlanDisplayProps {
  plan: GeneratedPlan;
  projectPlan: ProjectPlan;
  onAccept?: () => void;
  onEdit: () => void;
  onBackToChat: () => void;
}

export default function PlanDisplay({
  plan,
  projectPlan,
  onAccept,
  onEdit,
  onBackToChat,
}: PlanDisplayProps) {
  const { setMode, project, setProject, setOpenFiles, setCurrentFileId } = useBuilderStore();
  const [completedTasks, setCompletedTasks] = useState<Set<string>>(new Set());
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  const toggleTaskComplete = (taskId: string) => {
    setCompletedTasks((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  const toggleTaskExpand = (taskId: string) => {
    setExpandedTasks((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  const handleAccept = async () => {
    setIsGenerating(true);
    setGenerationError(null);

    try {
      const { files, readme } = await generateProject(projectPlan);

      // Create README file
      const readmeFile: ProjectFile = {
        id: `readme-${Date.now()}`,
        path: 'README.md',
        content: readme,
        language: 'markdown',
        isModified: false,
        isOpen: true,
      };

      // Combine all files with README
      const allFiles = [...files, readmeFile];

      // Update project with files
      if (project) {
        setProject({
          ...project,
          files: allFiles,
          currentFileId: allFiles[0]?.id || null,
          plan: projectPlan,
          updatedAt: new Date().toISOString(),
        });
      }

      // Set open files (first 3 files or all if less)
      const filesToOpen = allFiles.slice(0, 3).map((f) => f.id);
      setOpenFiles(filesToOpen);
      setCurrentFileId(filesToOpen[0] || null);

      // Switch to build mode
      setMode('build');

      // Call optional onAccept callback
      if (onAccept) {
        onAccept();
      }
    } catch (error) {
      console.error('Failed to generate project:', error);
      setGenerationError(
        error instanceof Error
          ? error.message
          : 'Failed to generate project. Please try again.'
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const completedCount = completedTasks.size;
  const totalTasks = plan.tasks.length;
  const progressPercent = totalTasks > 0 ? (completedCount / totalTasks) * 100 : 0;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: `${SPACE.lg}px ${SPACE.lg}px ${SPACE.md}px`,
          borderBottom: `1px solid ${BORDER}`,
          background: CARD_BG,
        }}
      >
        {/* Project name and track badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: SPACE.md,
            marginBottom: SPACE.sm,
          }}
        >
          <h1
            style={{
              margin: 0,
              fontSize: 24,
              fontWeight: 700,
              color: TEXT_PRIMARY,
              lineHeight: 1.3,
            }}
          >
            {plan.name}
          </h1>
          <span
            style={{
              padding: `${SPACE.xs}px ${SPACE.sm}px`,
              background: `${PRIMARY}20`,
              color: PRIMARY,
              borderRadius: RADIUS.md,
              fontSize: 12,
              fontWeight: 600,
              whiteSpace: 'nowrap',
            }}
          >
            {plan.targetTrack}
          </span>
        </div>

        {/* Description */}
        <p
          style={{
            margin: 0,
            marginBottom: SPACE.md,
            color: TEXT_SECONDARY,
            fontSize: 14,
            lineHeight: 1.5,
          }}
        >
          {plan.description}
        </p>

        {/* Meta info row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: SPACE.lg,
            flexWrap: 'wrap',
          }}
        >
          {/* Estimated hours */}
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.xs }}>
            <span style={{ fontSize: 16 }}>⏱️</span>
            <span style={{ color: TEXT_SECONDARY, fontSize: 14 }}>
              Estimated: <strong style={{ color: TEXT_PRIMARY }}>{plan.estimatedHours}h</strong>
            </span>
          </div>

          {/* Progress */}
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.xs }}>
            <span style={{ fontSize: 16 }}>📊</span>
            <span style={{ color: TEXT_SECONDARY, fontSize: 14 }}>
              Progress:{' '}
              <strong style={{ color: TEXT_PRIMARY }}>
                {completedCount}/{totalTasks}
              </strong>
            </span>
            <div
              style={{
                width: 60,
                height: 4,
                background: BORDER,
                borderRadius: RADIUS.full,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${progressPercent}%`,
                  height: '100%',
                  background: SUCCESS,
                  borderRadius: RADIUS.full,
                  transition: 'width 0.3s ease',
                }}
              />
            </div>
          </div>
        </div>

        {/* Tech stack tags */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: SPACE.xs,
            marginTop: SPACE.md,
          }}
        >
          {plan.techStack.map((tech) => (
            <span
              key={tech}
              style={{
                padding: `${SPACE.xs}px ${SPACE.sm}px`,
                background: CYAN_BG20,
                color: CYAN,
                borderRadius: RADIUS.sm,
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {tech}
            </span>
          ))}
        </div>
      </div>

      {/* Scrollable content */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: SPACE.lg,
        }}
      >
        {/* Tasks section */}
        <div style={{ marginBottom: SPACE.lg }}>
          <h2
            style={{
              margin: 0,
              marginBottom: SPACE.md,
              fontSize: 16,
              fontWeight: 600,
              color: TEXT_PRIMARY,
              display: 'flex',
              alignItems: 'center',
              gap: SPACE.xs,
            }}
          >
            <span>📝</span> Tasks
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
            {plan.tasks.map((task, index) => (
              <TaskItem
                key={task.id}
                task={task}
                index={index}
                isCompleted={completedTasks.has(task.id)}
                isExpanded={expandedTasks.has(task.id)}
                onToggleComplete={() => toggleTaskComplete(task.id)}
                onToggleExpand={() => toggleTaskExpand(task.id)}
                formatDuration={formatDuration}
              />
            ))}
          </div>
        </div>

        {/* Stretch goals section */}
        {plan.stretchGoals.length > 0 && (
          <div>
            <h2
              style={{
                margin: 0,
                marginBottom: SPACE.md,
                fontSize: 16,
                fontWeight: 600,
                color: TEXT_PRIMARY,
                display: 'flex',
                alignItems: 'center',
                gap: SPACE.xs,
              }}
            >
              <span>⭐</span> Stretch Goals
            </h2>

            <div
              style={{
                padding: SPACE.md,
                background: GOLD_BG20,
                borderRadius: RADIUS.md,
                border: `1px solid ${GOLD}30`,
              }}
            >
              <ul
                style={{
                  margin: 0,
                  paddingLeft: SPACE.lg,
                  color: TEXT_SECONDARY,
                  fontSize: 14,
                  lineHeight: 1.6,
                }}
              >
                {plan.stretchGoals.map((goal, index) => (
                  <li key={index} style={{ marginBottom: SPACE.xs }}>
                    {goal}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {generationError && (
        <div
          style={{
            padding: SPACE.md,
            margin: `${SPACE.md}px ${SPACE.lg}px 0`,
            background: 'rgba(239, 68, 68, 0.2)',
            borderRadius: RADIUS.md,
            color: '#ef4444',
            fontSize: 14,
          }}
        >
          {generationError}
        </div>
      )}

      {/* Action buttons footer */}
      <div
        style={{
          padding: `${SPACE.md}px ${SPACE.lg}px`,
          borderTop: `1px solid ${BORDER}`,
          background: CARD_BG,
          display: 'flex',
          gap: SPACE.md,
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        <button
          onClick={handleAccept}
          disabled={isGenerating}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: SPACE.xs,
            padding: `${SPACE.sm}px ${SPACE.lg}px`,
            background: isGenerating ? '#475569' : PRIMARY,
            color: '#fff',
            border: 'none',
            borderRadius: RADIUS.md,
            cursor: isGenerating ? 'not-allowed' : 'pointer',
            fontSize: 14,
            fontWeight: 600,
            transition: 'all 0.2s ease',
            boxShadow: SHADOW.elevated,
            opacity: isGenerating ? 0.7 : 1,
          }}
          onMouseEnter={(e) => {
            if (!isGenerating) {
              e.currentTarget.style.background = PRIMARY_HOVER;
              e.currentTarget.style.transform = 'translateY(-2px)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isGenerating) {
              e.currentTarget.style.background = PRIMARY;
              e.currentTarget.style.transform = 'translateY(0)';
            }
          }}
        >
          {isGenerating ? (
            <>
              <span>⏳</span> Generating...
            </>
          ) : (
            <>
              <span>🚀</span> Accept & Start Building
            </>
          )}
        </button>

        <button
          onClick={onEdit}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: SPACE.xs,
            padding: `${SPACE.sm}px ${SPACE.lg}px`,
            background: 'transparent',
            color: CYAN,
            border: `1px solid ${CYAN}`,
            borderRadius: RADIUS.md,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 500,
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = CYAN_BG20;
            e.currentTarget.style.transform = 'translateY(-2px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          <span>✏️</span> Edit Plan
        </button>

        <button
          onClick={onBackToChat}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: SPACE.xs,
            padding: `${SPACE.sm}px ${SPACE.lg}px`,
            background: 'transparent',
            color: TEXT_SECONDARY,
            border: `1px solid ${BORDER}`,
            borderRadius: RADIUS.md,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 500,
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = BORDER;
            e.currentTarget.style.color = TEXT_PRIMARY;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = TEXT_SECONDARY;
          }}
        >
          <span>💬</span> Back to Chat
        </button>
      </div>
    </div>
  );
}

// Task item component
interface TaskItemProps {
  task: PlanTask;
  index: number;
  isCompleted: boolean;
  isExpanded: boolean;
  onToggleComplete: () => void;
  onToggleExpand: () => void;
  formatDuration: (minutes: number) => string;
}

function TaskItem({
  task,
  index,
  isCompleted,
  isExpanded,
  onToggleComplete,
  onToggleExpand,
  formatDuration,
}: TaskItemProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        padding: SPACE.md,
        background: isCompleted ? `${SUCCESS}10` : CARD_BG,
        borderRadius: RADIUS.md,
        border: `1px solid ${isCompleted ? `${SUCCESS}30` : BORDER}`,
        transition: 'all 0.2s ease',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
        {/* Checkbox */}
        <button
          onClick={onToggleComplete}
          style={{
            width: 20,
            height: 20,
            borderRadius: RADIUS.sm,
            border: `2px solid ${isCompleted ? SUCCESS : BORDER_LIGHT}`,
            background: isCompleted ? SUCCESS : 'transparent',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 0,
            transition: 'all 0.2s ease',
            flexShrink: 0,
          }}
        >
          {isCompleted && (
            <span style={{ color: '#fff', fontSize: 12 }}>✓</span>
          )}
        </button>

        {/* Task number and description */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: SPACE.xs,
              marginBottom: 2,
            }}
          >
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                color: TEXT_MUTED,
              }}
            >
              Task {index + 1}
            </span>
            <span
              style={{
                fontSize: 12,
                color: TEXT_MUTED,
              }}
            >
              ({formatDuration(task.estimatedMinutes)})
            </span>
          </div>
          <p
            style={{
              margin: 0,
              fontSize: 14,
              color: isCompleted ? TEXT_MUTED : TEXT_PRIMARY,
              textDecoration: isCompleted ? 'line-through' : 'none',
              lineHeight: 1.4,
            }}
          >
            {task.description}
          </p>
        </div>

        {/* Expand button (if has dependencies) */}
        {task.dependencies.length > 0 && (
          <button
            onClick={onToggleExpand}
            style={{
              padding: SPACE.xs,
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: TEXT_MUTED,
              fontSize: 12,
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.2s ease',
            }}
          >
            ▼
          </button>
        )}
      </div>

      {/* Dependencies (expanded) */}
      {isExpanded && task.dependencies.length > 0 && (
        <div
          style={{
            marginTop: SPACE.sm,
            marginLeft: 28,
            padding: SPACE.sm,
            background: `${PRIMARY}10`,
            borderRadius: RADIUS.sm,
          }}
        >
          <p
            style={{
              margin: 0,
              marginBottom: SPACE.xs,
              fontSize: 12,
              color: TEXT_MUTED,
            }}
          >
            Dependencies:
          </p>
          <ul
            style={{
              margin: 0,
              paddingLeft: SPACE.lg,
              fontSize: 12,
              color: TEXT_SECONDARY,
            }}
          >
            {task.dependencies.map((dep, i) => (
              <li key={i}>{dep}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
