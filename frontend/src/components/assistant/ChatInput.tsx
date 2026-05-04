import { useState } from 'react';
import { CARD_BG, PRIMARY, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY } from '../../theme';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  onSend,
  disabled,
  placeholder = 'Ask me anything about the hackathon...',
}: ChatInputProps) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        display: 'flex',
        gap: SPACE.sm,
        padding: SPACE.md,
        background: CARD_BG,
        borderRadius: RADIUS.md,
      }}
    >
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        style={{
          flex: 1,
          background: 'transparent',
          border: 'none',
          color: TEXT_PRIMARY,
          fontSize: 14,
          fontFamily: 'inherit',
          resize: 'none',
          outline: 'none',
          minHeight: 24,
          maxHeight: 120,
        }}
      />
      <button
        type="submit"
        disabled={disabled || !message.trim()}
        style={{
          padding: `${SPACE.sm}px ${SPACE.md}px`,
          background: PRIMARY,
          color: '#fff',
          border: 'none',
          borderRadius: RADIUS.sm,
          cursor: disabled || !message.trim() ? 'not-allowed' : 'pointer',
          opacity: disabled || !message.trim() ? 0.5 : 1,
          fontSize: 14,
          fontWeight: 500,
          display: 'flex',
          alignItems: 'center',
          gap: SPACE.xs,
        }}
      >
        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
          send
        </span>
        Send
      </button>
    </form>
  );
}
