import {
  PAGE_BG,
  CARD_BG,
  PRIMARY,
  RADIUS,
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER,
  BORDER_LIGHT,
} from '../../theme';
import type { Conversation } from '../../services/assistant';

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId?: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onClose?: () => void;
  isOpen?: boolean;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onClose,
}: ConversationSidebarProps) {
  return (
    <div
      style={{
        width: 280,
        minWidth: 280,
        height: '100%',
        background: PAGE_BG,
        borderRight: `1px solid ${BORDER}`,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: `${SPACE.md}px ${SPACE.lg}px`,
          borderBottom: `1px solid ${BORDER}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: TEXT_MUTED,
          }}
        >
          Conversations
        </span>
        <button
          onClick={onNew}
          style={{
            width: 28,
            height: 28,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'transparent',
            border: `1px solid ${BORDER}`,
            borderRadius: RADIUS.md,
            color: TEXT_SECONDARY,
            cursor: 'pointer',
            fontSize: 16,
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = BORDER_LIGHT;
            e.currentTarget.style.color = TEXT_PRIMARY;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = BORDER;
            e.currentTarget.style.color = TEXT_SECONDARY;
          }}
          title="New conversation"
        >
          +
        </button>
      </div>

      {/* Conversation List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: SPACE.sm,
        }}
      >
        {conversations.length === 0 ? (
          <div
            style={{
              padding: SPACE.xl,
              textAlign: 'center',
              color: TEXT_MUTED,
              fontSize: 13,
            }}
          >
            No conversations yet.
            <br />
            Start a new chat!
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.xs }}>
            {conversations.map((conv) => {
              const isActive = activeId === conv.id;
              return (
                <div
                  key={conv.id}
                  onClick={() => onSelect(conv.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: SPACE.sm,
                    padding: `${SPACE.sm}px ${SPACE.md}px`,
                    borderRadius: RADIUS.md,
                    cursor: 'pointer',
                    background: isActive ? 'rgba(94, 106, 210, 0.15)' : 'transparent',
                    border: `1px solid ${isActive ? 'rgba(94, 106, 210, 0.3)' : 'transparent'}`,
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                    }
                  }}
                >
                  {/* Chat icon */}
                  <span style={{ fontSize: 14, opacity: 0.6 }}>💬</span>

                  {/* Content */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: 500,
                        color: isActive ? TEXT_PRIMARY : TEXT_SECONDARY,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {conv.title || 'New conversation'}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: TEXT_MUTED,
                        marginTop: 2,
                      }}
                    >
                      {new Date(conv.updated_at).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                      })}
                    </div>
                  </div>

                  {/* Delete button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm('Delete this conversation?')) {
                        onDelete(conv.id);
                      }
                    }}
                    style={{
                      width: 20,
                      height: 20,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'transparent',
                      border: 'none',
                      color: TEXT_MUTED,
                      cursor: 'pointer',
                      fontSize: 12,
                      opacity: 0,
                      transition: 'opacity 0.15s ease',
                      borderRadius: RADIUS.sm,
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
                      e.currentTarget.style.color = '#ef4444';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = TEXT_MUTED;
                    }}
                  >
                    ×
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer hint */}
      <div
        style={{
          padding: `${SPACE.md}px ${SPACE.lg}px`,
          borderTop: `1px solid ${BORDER}`,
          fontSize: 11,
          color: TEXT_MUTED,
        }}
      >
        Press Ctrl+N for new chat
      </div>
    </div>
  );
}
