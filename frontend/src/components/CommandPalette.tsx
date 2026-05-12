import { useState, useEffect, useCallback } from 'react';

interface CommandPaletteProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  return { isOpen, open, close };
}

const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;
  return (
    <div
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(0,0,0,0.5)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '10vh',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#0f172a',
          border: '1px solid rgba(148,163,184,0.15)',
          borderRadius: 8,
          width: 560,
          maxWidth: '90vw',
          padding: 16,
        }}
        onClick={e => e.stopPropagation()}
      >
        <input
          autoFocus
          placeholder="Search..."
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            color: '#f1f5f9',
            fontSize: 16,
            outline: 'none',
          }}
        />
      </div>
    </div>
  );
};

export default CommandPalette;
