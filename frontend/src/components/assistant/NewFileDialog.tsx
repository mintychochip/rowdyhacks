import { useState, useCallback, useEffect, useRef } from 'react';
import { getLanguageFromPath } from '../../utils/languageConfig';

const QUICK_EXTENSIONS = [
  '.py', '.ts', '.tsx', '.go', '.js', '.jsx',
  '.html', '.css', '.sql', '.sh', '.yaml', '.json', '.md',
];

interface NewFileDialogProps {
  existingPaths: string[];
  onConfirm: (name: string) => void;
  onCancel: () => void;
}

export default function NewFileDialog({ existingPaths, onConfirm, onCancel }: NewFileDialogProps) {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onCancel]);

  const handleConfirm = useCallback(() => {
    const trimmed = name.trim();
    if (!trimmed) { setError('File name is required'); return; }
    if (existingPaths.includes(trimmed)) { setError('A file with this path already exists'); return; }
    onConfirm(trimmed);
  }, [name, existingPaths, onConfirm]);

  const lang = getLanguageFromPath(name);

  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 10,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.4)',
    }}>
      <div style={{
        background: '#1e293b', borderRadius: 12,
        padding: 20, width: 380, maxWidth: '90%',
        boxShadow: '0 25px 50px rgba(0,0,0,0.4)',
      }} onClick={e => e.stopPropagation()}>
        <h3 style={{ margin: '0 0 12px', color: '#f1f5f9', fontSize: 15, fontWeight: 600 }}>New File</h3>

        <input ref={inputRef} placeholder="src/utils/helper.ts"
          value={name} onChange={e => { setName(e.target.value); setError(null); }}
          onKeyDown={e => { if (e.key === 'Enter') handleConfirm(); }}
          style={{
            width: '100%', padding: '8px 10px', marginBottom: 8,
            background: '#0f172a', border: `1px solid ${error ? '#ef4444' : '#334155'}`,
            borderRadius: 6, color: '#f1f5f9', fontSize: 13, outline: 'none',
            boxSizing: 'border-box',
          }} />
        {error && <div style={{ color: '#ef4444', fontSize: 11, marginBottom: 8 }}>{error}</div>}

        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 10, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Quick extensions</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {QUICK_EXTENSIONS.map(ext => (
              <button key={ext} onClick={() => { setName(`untitled${ext}`); setError(null); }}
                style={{
                  padding: '3px 8px', fontSize: 11, borderRadius: 4,
                  background: name.endsWith(ext) ? '#2563eb' : '#334155',
                  border: 'none', color: '#f1f5f9', cursor: 'pointer',
                }}
              >{ext}</button>
            ))}
          </div>
        </div>

        {name && lang !== 'plaintext' && (
          <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 12 }}>
            Language: <span style={{ color: '#60a5fa', fontWeight: 600 }}>{lang.toUpperCase()}</span>
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onCancel}
            style={{ padding: '6px 14px', background: 'transparent', border: '1px solid #334155', borderRadius: 6, color: '#94a3b8', cursor: 'pointer', fontSize: 12 }}
            onMouseEnter={e => { e.currentTarget.style.background = '#334155'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          >Cancel</button>
          <button onClick={handleConfirm}
            style={{ padding: '6px 14px', background: '#2563eb', border: 'none', borderRadius: 6, color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 500 }}
            onMouseEnter={e => { e.currentTarget.style.background = '#1d4ed8'; }}
            onMouseLeave={e => { e.currentTarget.style.background = '#2563eb'; }}
          >Create</button>
        </div>
      </div>
    </div>
  );
}
