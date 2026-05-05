// ============================================================
// Mode Switcher - Tab bar for switching between Chat/Plan/Build modes
// ============================================================

import { useBuilderStore } from '../../stores/builderStore';
import type { BuilderMode } from '../../types/builder';
import {
  CARD_BG,
  PRIMARY,
  PRIMARY_BG20,
  RADIUS,
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  ERROR,
} from '../../theme';

const MODES: { id: BuilderMode; label: string; icon: string }[] = [
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'plan', label: 'Plan', icon: '📋' },
  { id: 'build', label: 'Build', icon: '🔨' },
];

export default function ModeSwitcher() {
  const { mode, setMode, project, reset } = useBuilderStore();

  const handleClearProject = () => {
    if (confirm('Are you sure you want to clear the current project?')) {
      reset();
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: `${SPACE.sm}px ${SPACE.md}px`,
        background: CARD_BG,
        borderBottom: '1px solid rgba(255,255,255,0.1)',
      }}
    >
      {/* Mode tabs */}
      <div
        style={{
          display: 'flex',
          gap: SPACE.xs,
        }}
      >
        {MODES.map(({ id, label, icon }) => {
          const isActive = mode === id;
          return (
            <button
              key={id}
              onClick={() => setMode(id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: SPACE.xs,
                padding: `${SPACE.sm}px ${SPACE.md}px`,
                borderRadius: RADIUS.md,
                border: 'none',
                background: isActive ? PRIMARY_BG20 : 'transparent',
                color: isActive ? PRIMARY : TEXT_SECONDARY,
                fontSize: 14,
                fontWeight: isActive ? 600 : 500,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                  e.currentTarget.style.color = TEXT_PRIMARY;
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = TEXT_SECONDARY;
                }
              }}
            >
              <span style={{ fontSize: 16 }}>{icon}</span>
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* Project info and clear button */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: SPACE.md,
        }}
      >
        {project && (
          <span
            style={{
              fontSize: 13,
              color: TEXT_MUTED,
            }}
          >
            {project.name}
          </span>
        )}
        <button
          onClick={handleClearProject}
          style={{
            padding: `${SPACE.xs}px ${SPACE.sm}px`,
            borderRadius: RADIUS.sm,
            border: `1px solid ${ERROR}40`,
            background: 'transparent',
            color: ERROR,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = `${ERROR}20`;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
          }}
        >
          Clear Project
        </button>
      </div>
    </div>
  );
}
