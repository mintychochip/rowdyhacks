import { CARD_BG, PRIMARY, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY } from '../../theme';
import type { Conversation } from '../../services/assistant';

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId?: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: ConversationSidebarProps) {
  return (
    <div
      style={{
        width: 260,
        background: CARD_BG,
        borderRadius: RADIUS.md,
        padding: SPACE.md,
        display: 'flex',
        flexDirection: 'column',
        gap: SPACE.md,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: 16,
            color: TEXT_PRIMARY,
            fontWeight: 600,
          }}
        >
          Conversations
        </h3>
        <button
          onClick={onNew}
          style={{
            padding: `${SPACE.xs}px ${SPACE.sm}px`,
            background: PRIMARY,
            color: '#fff',
            border: 'none',
            borderRadius: RADIUS.sm,
            cursor: 'pointer',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: SPACE.xs,
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
            add
          </span>
          New
        </button>
      </div>

      {/* List */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: SPACE.xs,
          overflowY: 'auto',
          flex: 1,
        }}
      >
        {conversations.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              color: TEXT_SECONDARY,
              padding: SPACE.lg,
              fontSize: 14,
            }}
          >
            No conversations yet.
            <br />
            Start a new chat!
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => onSelect(conv.id)}
              style={{
                padding: SPACE.sm,
                borderRadius: RADIUS.sm,
                cursor: 'pointer',
                background: activeId === conv.id ? PRIMARY : 'transparent',
                color: activeId === conv.id ? '#fff' : TEXT_PRIMARY,
                position: 'relative',
                transition: 'background 0.2s',
              }}
            >
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  paddingRight: 24,
                }}
              >
                {conv.title || 'New conversation'}
              </div>
              <div
                style={{
                  fontSize: 11,
                  opacity: 0.7,
                  marginTop: 2,
                }}
              >
                {new Date(conv.updated_at).toLocaleDateString()}
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
                  position: 'absolute',
                  right: SPACE.xs,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'transparent',
                  border: 'none',
                  color: 'inherit',
                  cursor: 'pointer',
                  padding: SPACE.xs,
                  opacity: 0.5,
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                  delete
                </span>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
