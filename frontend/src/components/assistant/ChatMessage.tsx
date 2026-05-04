import { useEffect, useRef, useState } from 'react';
import { CARD_BG, PRIMARY, SPACE, TEXT_PRIMARY, TEXT_SECONDARY } from '../../theme';

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'tool';
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
    // Auto-scroll to bottom if streaming
    if (isStreaming && messageRef.current) {
      messageRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [content, isStreaming]);

  const isUser = role === 'user';
  const isAssistant = role === 'assistant';

  return (
    <div
      ref={messageRef}
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: SPACE.md,
      }}
    >
      <div
        style={{
          maxWidth: '85%',
          padding: SPACE.md,
          borderRadius: 12,
          background: isUser ? PRIMARY : CARD_BG,
          color: isUser ? '#fff' : TEXT_PRIMARY,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {/* Role indicator */}
        <div
          style={{
            fontSize: 12,
            color: isUser ? 'rgba(255,255,255,0.7)' : TEXT_SECONDARY,
            marginBottom: SPACE.xs,
            textTransform: 'uppercase',
            letterSpacing: 0.5,
          }}
        >
          {isUser ? 'You' : isAssistant ? 'Assistant' : 'Tool'}
        </div>

        {/* Message content */}
        <div style={{ lineHeight: 1.6 }}>{content}</div>

        {/* Tool call indicators */}
        {toolCalls && toolCalls.length > 0 && (
          <div
            style={{
              marginTop: SPACE.sm,
              padding: SPACE.sm,
              background: 'rgba(0,0,0,0.2)',
              borderRadius: 6,
              fontSize: 12,
            }}
          >
            <span style={{ color: TEXT_SECONDARY }}>Using tools:</span>
            {toolCalls.map((tc, i) => (
              <span
                key={i}
                style={{
                  marginLeft: SPACE.xs,
                  color: PRIMARY,
                }}
              >
                {tc.function?.name || tc.tool}
              </span>
            ))}
          </div>
        )}

        {/* Streaming indicator */}
        {isStreaming && (
          <span
            style={{
              display: 'inline-block',
              width: 8,
              height: 8,
              background: PRIMARY,
              borderRadius: '50%',
              marginLeft: SPACE.xs,
              animation: 'pulse 1s infinite',
            }}
          />
        )}
      </div>
    </div>
  );
}
