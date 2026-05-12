import { useEffect, useRef } from 'react';
import {
  SPACE,
  RADIUS,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_TERTIARY,
  TEXT_MUTED,
  BORDER,
  BORDER_SUBTLE,
  BORDER_LIGHT,
  PRIMARY,
  PRIMARY_HOVER,
  TYPO,
  CARD,
} from '../../theme';

// Message role type matching backend AssistantMessageRole
interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  isStreaming?: boolean;
  toolCalls?: any[];
}

export default function ChatMessage({
  role,
  content,
  isStreaming,
  toolCalls,
}: ChatMessageProps) {
  const messageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isStreaming && messageRef.current) {
      messageRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [content, isStreaming]);

  const isUser = role === 'user';
  const isAssistant = role === 'assistant';

  // Format content - handle markdown-style code blocks
  const formatContent = (text: string) => {
    if (!text) return null;

    // Split by code blocks
    const parts = text.split(/(```[\s\S]*?```)/g);

    return parts.map((part, index) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        // Extract language and code
        const match = part.match(/```(\w+)?\n?([\s\S]*?)```/);
        const lang = match?.[1] || 'text';
        const code = match?.[2] || part.slice(3, -3);

        return (
          <pre
            key={index}
            style={{
              background: 'rgba(0, 0, 0, 0.3)',
              border: CARD.border,
              borderRadius: RADIUS.md,
              padding: SPACE.md,
              margin: `${SPACE.md}px 0`,
              overflow: 'auto',
              fontFamily: TYPO.mono.fontFamily,
              fontSize: 13,
              lineHeight: 1.5,
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: SPACE.sm,
                paddingBottom: SPACE.sm,
                borderBottom: `1px solid ${BORDER_SUBTLE}`,
              }}
            >
              <span style={{
                fontSize: 11,
                color: TEXT_MUTED,
                textTransform: 'uppercase',
                fontWeight: 500,
                letterSpacing: '0.05em',
              }}>
                {lang}
              </span>
            </div>
            <code style={{ color: TEXT_PRIMARY }}>{code}</code>
          </pre>
        );
      }

      // Regular text - handle inline code and paragraphs
      return part.split('\n').map((line, lineIndex) => {
        // Handle inline code
        const inlineParts = line.split(/(`[^`]+`)/g);
        const processedLine = inlineParts.map((inlinePart, i) => {
          if (inlinePart.startsWith('`') && inlinePart.endsWith('`')) {
            return (
              <code
                key={i}
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  padding: '2px 6px',
                  borderRadius: RADIUS.micro,
                  fontFamily: TYPO.mono.fontFamily,
                  fontSize: '0.9em',
                  color: TEXT_PRIMARY,
                }}
              >
                {inlinePart.slice(1, -1)}
              </code>
            );
          }
          return inlinePart;
        });

        return (
          <span key={`${index}-${lineIndex}`}>
            {processedLine}
            {lineIndex < part.split('\n').length - 1 && <br />}
          </span>
        );
      });
    });
  };

  return (
    <div
      ref={messageRef}
      style={{
        display: 'flex',
        gap: SPACE.md,
        marginBottom: SPACE.lg,
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}
    >
      {/* Avatar */}
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: RADIUS.sm,
          background: isUser
            ? 'rgba(94, 106, 210, 0.15)'
            : 'rgba(255, 255, 255, 0.04)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          border: `1px solid ${isUser ? 'rgba(94, 106, 210, 0.2)' : BORDER_SUBTLE}`,
        }}
      >
        {isUser ? (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={TEXT_SECONDARY} strokeWidth="2" strokeLinecap="round">
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={PRIMARY} strokeWidth="2" strokeLinecap="round">
            <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>
          </svg>
        )}
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          maxWidth: 'calc(100% - 60px)',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: SPACE.sm,
            marginBottom: SPACE.xs,
          }}
        >
          <span
            style={{
              fontSize: 12,
              fontWeight: 500,
              color: isUser ? TEXT_PRIMARY : TEXT_SECONDARY,
              letterSpacing: '-0.01em',
            }}
          >
            {isUser ? 'You' : 'Assistant'}
          </span>
        </div>

        {/* Message Bubble */}
        <div
          style={{
            padding: isUser ? `${SPACE.md}px` : 0,
            background: isUser ? 'rgba(94, 106, 210, 0.08)' : 'transparent',
            border: isUser ? `1px solid rgba(94, 106, 210, 0.15)` : 'none',
            borderRadius: isUser ? RADIUS.md : 0,
            color: TEXT_PRIMARY,
            fontSize: 15,
            lineHeight: 1.6,
            wordBreak: 'break-word',
            letterSpacing: '-0.01em',
          }}
        >
          {formatContent(content)}

          {/* Streaming indicator */}
          {isStreaming && (
            <span
              style={{
                display: 'inline-block',
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: PRIMARY,
                marginLeft: SPACE.xs,
                animation: 'pulse 1.5s infinite',
                verticalAlign: 'middle',
              }}
            />
          )}
        </div>

        {/* Tool call indicators */}
        {toolCalls && toolCalls.length > 0 && (
          <div
            style={{
              marginTop: SPACE.sm,
              padding: `${SPACE.sm}px ${SPACE.md}px`,
              background: 'rgba(94, 106, 210, 0.06)',
              border: '1px solid rgba(94, 106, 210, 0.12)',
              borderRadius: RADIUS.md,
              fontSize: 12,
              color: TEXT_SECONDARY,
              display: 'flex',
              alignItems: 'center',
              gap: SPACE.xs,
              letterSpacing: '-0.01em',
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke={PRIMARY} strokeWidth="2" strokeLinecap="round">
              <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>
            </svg>
            <span style={{ color: TEXT_TERTIARY }}>Using tools:</span>
            {toolCalls.map((tc, i) => (
              <span
                key={i}
                style={{
                  padding: '2px 8px',
                  background: 'rgba(94, 106, 210, 0.1)',
                  borderRadius: RADIUS.micro,
                  color: PRIMARY,
                  fontWeight: 500,
                  fontFamily: TYPO.mono.fontFamily,
                  fontSize: 11,
                }}
              >
                {tc.function?.name || tc.tool}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
