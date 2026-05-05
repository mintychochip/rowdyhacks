import { useEffect, useRef } from 'react';
import {
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER,
  PRIMARY,
  CARD_BG,
  RADIUS,
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
              border: `1px solid ${BORDER}`,
              borderRadius: RADIUS.md,
              padding: SPACE.md,
              margin: `${SPACE.md}px 0`,
              overflow: 'auto',
              fontFamily: "'JetBrains Mono', monospace",
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
                borderBottom: `1px solid ${BORDER}`,
              }}
            >
              <span style={{ fontSize: 11, color: TEXT_MUTED, textTransform: 'uppercase' }}>
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
                  background: 'rgba(255, 255, 255, 0.1)',
                  padding: '2px 6px',
                  borderRadius: RADIUS.sm,
                  fontFamily: "'JetBrains Mono', monospace",
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
          width: 32,
          height: 32,
          borderRadius: RADIUS.md,
          background: isUser ? PRIMARY : 'rgba(94, 106, 210, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 14,
          flexShrink: 0,
        }}
      >
        {isUser ? '👤' : '🤖'}
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
              fontSize: 13,
              fontWeight: 600,
              color: isUser ? TEXT_PRIMARY : TEXT_SECONDARY,
            }}
          >
            {isUser ? 'You' : 'Assistant'}
          </span>
        </div>

        {/* Message Bubble */}
        <div
          style={{
            padding: isUser ? `${SPACE.md}px` : 0,
            background: isUser ? 'rgba(94, 106, 210, 0.15)' : 'transparent',
            border: isUser ? `1px solid rgba(94, 106, 210, 0.25)` : 'none',
            borderRadius: isUser ? RADIUS.md : 0,
            color: TEXT_PRIMARY,
            fontSize: 15,
            lineHeight: 1.6,
            wordBreak: 'break-word',
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
                background: PRIMARY,
                borderRadius: '50%',
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
              background: 'rgba(94, 106, 210, 0.08)',
              border: '1px solid rgba(94, 106, 210, 0.2)',
              borderRadius: RADIUS.md,
              fontSize: 12,
              color: TEXT_SECONDARY,
              display: 'flex',
              alignItems: 'center',
              gap: SPACE.xs,
            }}
          >
            <span style={{ color: PRIMARY }}>⚡</span>
            Using tools:
            {toolCalls.map((tc, i) => (
              <span
                key={i}
                style={{
                  padding: '2px 8px',
                  background: 'rgba(94, 106, 210, 0.15)',
                  borderRadius: RADIUS.sm,
                  color: PRIMARY,
                  fontWeight: 500,
                  fontFamily: "'JetBrains Mono', monospace",
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
