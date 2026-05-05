import { useState, useRef, useEffect } from 'react';
import {
  SPACE,
  RADIUS,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER,
  BORDER_LIGHT,
  CARD_BG,
  PRIMARY,
  INPUT_BG,
} from '../../theme';
import type { ModelType } from '../../services/assistant';

interface LinearChatInputProps {
  onSend: (message: string, model: ModelType) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
}

export default function LinearChatInput({
  onSend,
  onStop,
  disabled,
  isStreaming,
  placeholder = 'Type a message to start chatting...',
}: LinearChatInputProps) {
  const [message, setMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState<ModelType>('fast');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [message]);

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
        maxWidth: 720,
        margin: '0 auto',
      }}
    >
      {/* Main Input Container */}
      <div
        style={{
          background: CARD_BG,
          borderRadius: RADIUS.lg,
          border: `1px solid ${isFocused ? BORDER_LIGHT : BORDER}`,
          boxShadow: isFocused ? '0 0 0 3px rgba(94, 106, 210, 0.1)' : '0 2px 8px rgba(0, 0, 0, 0.2)',
          transition: 'all 0.15s ease',
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
            fontFamily: "'Inter', -apple-system, sans-serif",
            lineHeight: 1.6,
            resize: 'none',
            outline: 'none',
            minHeight: 52,
            maxHeight: 200,
          }}
        />

        {/* Bottom Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: `${SPACE.sm}px ${SPACE.md}px`,
            borderTop: `1px solid ${message ? BORDER : 'transparent'}`,
            transition: 'border-color 0.15s ease',
          }}
        >
          {/* Left: Model Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.xs }}>
            <span style={{ fontSize: 12, color: TEXT_MUTED, marginRight: SPACE.xs }}>
              Model
            </span>
            <button
              onClick={() => setSelectedModel('fast')}
              disabled={isStreaming}
              style={{
                padding: `${SPACE.xs}px ${SPACE.sm}px`,
                background: selectedModel === 'fast' ? 'rgba(94, 106, 210, 0.15)' : 'transparent',
                border: `1px solid ${selectedModel === 'fast' ? 'rgba(94, 106, 210, 0.3)' : BORDER}`,
                borderRadius: RADIUS.sm,
                color: selectedModel === 'fast' ? TEXT_PRIMARY : TEXT_SECONDARY,
                fontSize: 12,
                fontWeight: 500,
                cursor: isStreaming ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: SPACE.xs,
                transition: 'all 0.15s ease',
                opacity: isStreaming ? 0.5 : 1,
              }}
            >
              <span style={{ fontSize: 10 }}>⚡</span>
              Fast
            </button>
            <button
              onClick={() => setSelectedModel('thinking')}
              disabled={isStreaming}
              style={{
                padding: `${SPACE.xs}px ${SPACE.sm}px`,
                background: selectedModel === 'thinking' ? 'rgba(94, 106, 210, 0.15)' : 'transparent',
                border: `1px solid ${selectedModel === 'thinking' ? 'rgba(94, 106, 210, 0.3)' : BORDER}`,
                borderRadius: RADIUS.sm,
                color: selectedModel === 'thinking' ? TEXT_PRIMARY : TEXT_SECONDARY,
                fontSize: 12,
                fontWeight: 500,
                cursor: isStreaming ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: SPACE.xs,
                transition: 'all 0.15s ease',
                opacity: isStreaming ? 0.5 : 1,
              }}
            >
              <span style={{ fontSize: 10 }}>🧠</span>
              Thinking
            </button>
          </div>

          {/* Right: Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
            {/* Character count / Hint */}
            <span style={{ fontSize: 12, color: TEXT_MUTED }}>
              {message.length > 0 ? `${message.length} chars` : 'Shift + Enter for new line'}
            </span>

            {/* Send/Stop Button */}
            {isStreaming ? (
              <button
                onClick={onStop}
                style={{
                  padding: `${SPACE.sm}px ${SPACE.md}px`,
                  background: 'rgba(239, 68, 68, 0.9)',
                  border: 'none',
                  borderRadius: RADIUS.md,
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.xs,
                  transition: 'all 0.15s ease',
                }}
              >
                <span style={{ fontSize: 14 }}>■</span>
                Stop
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!message.trim() || disabled}
                style={{
                  padding: `${SPACE.sm}px ${SPACE.md}px`,
                  background: message.trim() && !disabled ? PRIMARY : BORDER,
                  border: 'none',
                  borderRadius: RADIUS.md,
                  color: message.trim() && !disabled ? '#fff' : TEXT_SECONDARY,
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: message.trim() && !disabled ? 'pointer' : 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.xs,
                  transition: 'all 0.15s ease',
                }}
              >
                <span style={{ fontSize: 14 }}>↑</span>
                Send
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Bottom hint */}
      <div
        style={{
          textAlign: 'center',
          marginTop: SPACE.sm,
          fontSize: 12,
          color: TEXT_MUTED,
        }}
      >
        {isStreaming ? (
          <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: SPACE.xs }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: PRIMARY, animation: 'pulse 1.5s infinite' }} />
            AI is responding using {selectedModel === 'thinking' ? '🧠 Thinking' : '⚡ Fast'} model...
          </span>
        ) : (
          <span>Press Enter to send, Shift + Enter for new line</span>
        )}
      </div>
    </div>
  );
}
