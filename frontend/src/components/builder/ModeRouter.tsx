// ============================================================
// Mode Router - Switches between Chat, Plan, and Build modes
// ============================================================

import { useBuilderStore } from '../../stores/builderStore';
import {
  CARD_BG,
  PRIMARY,
  RADIUS,
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
} from '../../theme';

// Placeholder components - will be implemented in subsequent chunks
function ChatMode() {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: TEXT_SECONDARY,
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: SPACE.md }}>💬</div>
        <div style={{ color: TEXT_PRIMARY, fontSize: 18, fontWeight: 600 }}>
          Chat Mode
        </div>
        <div style={{ marginTop: SPACE.sm }}>
          Start a conversation to build your project
        </div>
      </div>
    </div>
  );
}

function PlanMode() {
  const { project } = useBuilderStore();

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: TEXT_SECONDARY,
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: SPACE.md }}>📋</div>
        <div style={{ color: TEXT_PRIMARY, fontSize: 18, fontWeight: 600 }}>
          Plan Mode
        </div>
        <div style={{ marginTop: SPACE.sm }}>
          {project?.plan
            ? `Viewing plan: ${project.plan.title}`
            : 'Generate a plan for your project'}
        </div>
      </div>
    </div>
  );
}

function BuildMode() {
  const { project, openFiles } = useBuilderStore();

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: TEXT_SECONDARY,
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: SPACE.md }}>🔨</div>
        <div style={{ color: TEXT_PRIMARY, fontSize: 18, fontWeight: 600 }}>
          Build Mode
        </div>
        <div style={{ marginTop: SPACE.sm }}>
          {openFiles.length > 0
            ? `Editing ${openFiles.length} file(s)`
            : project
              ? 'Open files to start building'
              : 'Create a project to start building'}
        </div>
      </div>
    </div>
  );
}

export default function ModeRouter() {
  const { mode } = useBuilderStore();

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        background: CARD_BG,
        borderRadius: RADIUS.md,
        overflow: 'hidden',
      }}
    >
      {/* Mode indicator header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: SPACE.sm,
          padding: `${SPACE.sm}px ${SPACE.md}px`,
          borderBottom: `1px solid rgba(255,255,255,0.1)`,
          background: 'rgba(0,0,0,0.2)',
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: PRIMARY,
            animation: mode === 'chat' ? 'none' : 'pulse 2s infinite',
          }}
        />
        <span
          style={{
            fontSize: 12,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: 1,
            color: TEXT_PRIMARY,
          }}
        >
          {mode} Mode
        </span>
      </div>

      {/* Mode content */}
      <div style={{ flex: 1, overflow: 'auto', padding: SPACE.md }}>
        {mode === 'chat' && <ChatMode />}
        {mode === 'plan' && <PlanMode />}
        {mode === 'build' && <BuildMode />}
      </div>

      {/* CSS for pulse animation */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
