import { useState, useRef, useEffect } from 'react';
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
  CARD_BG,
  PRIMARY,
  PRIMARY_HOVER,
  INPUT_BG,
  TYPO,
  SHADOW,
  BUTTON,
  CARD,
} from '../../theme';
import type { ModelType } from '../../services/assistant';

interface LinearChatInputProps {
  onSend: (message: string, model: ModelType) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
  compact?: boolean;
}

export default function LinearChatInput({
  onSend,
  onStop,
  disabled,
  isStreaming,
  placeholder = 'Type a message...',
  compact = false,
}: LinearChatInputProps) {
  const [message, setMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState<ModelType>('fast');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, compact ? 80 : 200)}px`;
    }
  }, [message, compact]);

  const handleSubmit = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim(), selectedModel);
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: compact ? undefined : 720,
        margin: '0 auto',
      }}
    >
      {/* Main Input Container */}
      <div
        style={{
          background: CARD.background,
          borderRadius: RADIUS.md,
          border: `1px solid ${isFocused ? BORDER_LIGHT : BORDER_SUBTLE}`,
          boxShadow: isFocused
            ? '0 0 0 3px rgba(94, 106, 210, 0.08)'
            : SHADOW.card,
          transition: 'all 150ms ease',
          overflow: 'hidden',
        }}
      >
        {/* Text Area */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          disabled={disabled || isStreaming}
          rows={1}
          style={{
            width: '100%',
            padding: `${SPACE.lg}px ${SPACE.lg}px ${SPACE.md}px`,
            background: 'transparent',
            border: 'none',
            color: TEXT_PRIMARY,
            fontSize: 15,
            fontFamily: TYPO.body.fontFamily,
            lineHeight: 1.6,
            resize: 'none',
            outline: 'none',
            minHeight: 52,
            maxHeight: compact ? 80 : 200,
            letterSpacing: '-0.01em',
            fontFeatureSettings: TYPO.body.fontFeatureSettings,
          }}
        />

        {/* Bottom Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: `${SPACE.sm}px ${SPACE.md}px`,
            borderTop: `1px solid ${message ? BORDER_SUBTLE : 'transparent'}`,
            transition: 'border-color 150ms ease',
          }}
        >
          {/* Left: Model Selector */}
          {!compact && (
            <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.xs }}>
              <span style={{
                fontSize: 11,
                color: TEXT_MUTED,
                marginRight: SPACE.xs,
                fontWeight: 500,
                letterSpacing: '0.02em',
                textTransform: 'uppercase',
              }}>
                Model
              </span>
              <button
                onClick={() => setSelectedModel('fast')}
                disabled={isStreaming}
                style={{
                  padding: `${SPACE.xs}px ${SPACE.sm}px`,
                  background: selectedModel === 'fast' ? 'rgba(94, 106, 210, 0.12)' : 'transparent',
                  border: `1px solid ${selectedModel === 'fast' ? 'rgba(94, 106, 210, 0.25)' : BORDER_SUBTLE}`,
                  borderRadius: RADIUS.sm,
                  color: selectedModel === 'fast' ? TEXT_PRIMARY : TEXT_SECONDARY,
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: isStreaming ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.xs,
                  transition: 'all 150ms ease',
                  opacity: isStreaming ? 0.5 : 1,
                  letterSpacing: '-0.01em',
                  fontFamily: TYPO.body.fontFamily,
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                </svg>
                Fast
              </button>
              <button
                onClick={() => setSelectedModel('thinking')}
                disabled={isStreaming}
                style={{
                  padding: `${SPACE.xs}px ${SPACE.sm}px`,
                  background: selectedModel === 'thinking' ? 'rgba(94, 106, 210, 0.12)' : 'transparent',
                  border: `1px solid ${selectedModel === 'thinking' ? 'rgba(94, 106, 210, 0.25)' : BORDER_SUBTLE}`,
                  borderRadius: RADIUS.sm,
                  color: selectedModel === 'thinking' ? TEXT_PRIMARY : TEXT_SECONDARY,
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: isStreaming ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.xs,
                  transition: 'all 150ms ease',
                  opacity: isStreaming ? 0.5 : 1,
                  letterSpacing: '-0.01em',
                  fontFamily: TYPO.body.fontFamily,
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M12 5c-4.5 0-8 3.5-8 8s3.5 8 8 8 8-3.5 8-8-3.5-8-8-8Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>
                </svg>
                Thinking
              </button>
            </div>
          )}
          {compact && <div />}

          {/* Right: Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
            {/* Character count / Hint */}
            <span style={{
              fontSize: 12,
              color: TEXT_MUTED,
              letterSpacing: '-0.01em',
            }}>
              {message.length > 0 ? `${message.length} chars` : 'Shift + Enter for new line'}
            </span>

            {/* Send/Stop Button */}
            {isStreaming ? (
              <button
                onClick={onStop}
                style={{
                  padding: `${SPACE.sm}px ${SPACE.md}px`,
                  background: 'rgba(239, 68, 68, 0.85)',
                  border: 'none',
                  borderRadius: RADIUS.sm,
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.xs,
                  transition: 'all 150ms ease',
                  letterSpacing: '-0.01em',
                  fontFamily: TYPO.body.fontFamily,
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="6" width="12" height="12" rx="1"/>
                </svg>
                Stop
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!message.trim() || disabled}
                style={{
                  padding: `${SPACE.sm}px ${SPACE.md}px`,
                  background: message.trim() && !disabled ? PRIMARY : 'rgba(255, 255, 255, 0.03)',
                  border: 'none',
                  borderRadius: RADIUS.sm,
                  color: message.trim() && !disabled ? '#fff' : TEXT_MUTED,
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: message.trim() && !disabled ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.xs,
                  transition: 'all 150ms ease',
                  letterSpacing: '-0.01em',
                  fontFamily: TYPO.body.fontFamily,
                }}
                onMouseEnter={(e) => {
                  if (message.trim() && !disabled) {
                    e.currentTarget.style.background = PRIMARY_HOVER;
                  }
                }}
                onMouseLeave={(e) => {
                  if (message.trim() && !disabled) {
                    e.currentTarget.style.background = PRIMARY;
                  }
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
                </svg>
                Send
              </button>
            )}
          </div>
        </div>
      </div>

      {!compact && (
        <div
          style={{
            textAlign: 'center',
            marginTop: SPACE.sm,
            fontSize: 12,
            color: TEXT_MUTED,
            height: 18,
            lineHeight: '18px',
            letterSpacing: '-0.01em',
          }}
        >
          {isStreaming ? (
            <span style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: SPACE.xs,
            }}>
              <span style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: PRIMARY,
                animation: 'pulse 1.5s infinite',
              }} />
              AI is responding...
            </span>
          ) : (
            <span>Press Enter to send, Shift + Enter for new line</span>
          )}
        </div>
      )}
    </div>
  );
}
