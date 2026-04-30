import { useState, useRef, useEffect } from 'react';
import { PRIMARY, TEXT_PRIMARY, TEXT_MUTED, TEXT_WHITE, INPUT_BG, BORDER, CARD_BG, RADIUS } from '../theme';

const TECH_SUGGESTIONS = [
  'React', 'Vue', 'Angular', 'Svelte', 'Next.js', 'Nuxt', 'Gatsby', 'Remix',
  'TypeScript', 'JavaScript', 'Python', 'Go', 'Rust', 'Java', 'C#', 'C++', 'Kotlin', 'Swift', 'Dart', 'Ruby', 'PHP', 'Scala',
  'Node.js', 'Deno', 'Bun', 'Express', 'Fastify', 'NestJS', 'Django', 'Flask', 'FastAPI', 'Spring Boot', 'Rails', 'Laravel',
  'GraphQL', 'REST', 'tRPC', 'gRPC', 'WebSockets',
  'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Supabase', 'Firebase', 'DynamoDB', 'Neon', 'PlanetScale',
  'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure', 'Vercel', 'Netlify', 'Cloudflare', 'Railway', 'Render', 'Fly.io',
  'Tailwind CSS', 'Sass', 'CSS Modules', 'styled-components', 'Chakra UI', 'Material UI', 'shadcn/ui',
  'Prisma', 'Drizzle', 'tRPC', 'Zustand', 'Redux', 'Jotai', 'Recoil',
  'OpenAI', 'LangChain', 'Hugging Face', 'TensorFlow', 'PyTorch', 'scikit-learn',
  'React Native', 'Flutter', 'Expo', 'Tauri', 'Electron',
];

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
}

export default function TagInput({ value, onChange, placeholder = 'Search technologies...' }: TagInputProps) {
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = TECH_SUGGESTIONS.filter(
    (s) => s.toLowerCase().includes(input.toLowerCase()) && !value.includes(s)
  );

  useEffect(() => {
    setHighlightIndex(0);
  }, [input]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const addTag = (tag: string) => {
    if (!value.includes(tag)) {
      onChange([...value, tag]);
    }
    setInput('');
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const removeTag = (tag: string) => {
    onChange(value.filter((t) => t !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !input && value.length) {
      removeTag(value[value.length - 1]);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (input && filtered.length > 0) {
        addTag(filtered[highlightIndex] || filtered[0]);
      } else if (input.trim()) {
        addTag(input.trim());
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightIndex((prev) => Math.min(prev + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative' }}>
      <div
        style={{
          display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center',
          padding: '8px 12px', minHeight: 44,
          background: INPUT_BG, border: `2px solid ${PRIMARY}40`, borderRadius: RADIUS.md,
          cursor: 'text',
        }}
        onClick={() => inputRef.current?.focus()}
      >
        {value.map((tag) => (
          <span key={tag} style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '3px 8px', background: '#1a5ce730', borderRadius: RADIUS.sm,
            fontSize: 13, color: TEXT_PRIMARY, fontWeight: 500,
          }}>
            {tag}
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); removeTag(tag); }}
              style={{
                background: 'none', border: 'none', color: TEXT_MUTED,
                cursor: 'pointer', padding: 0, fontSize: 15, lineHeight: 1,
              }}
            >
              &times;
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => { setInput(e.target.value); setShowSuggestions(true); }}
          onFocus={() => setShowSuggestions(true)}
          onKeyDown={handleKeyDown}
          placeholder={value.length ? '' : placeholder}
          style={{
            flex: 1, minWidth: 120, border: 'none', background: 'none',
            color: TEXT_PRIMARY, fontSize: 14, outline: 'none',
            padding: '4px 0',
          }}
        />
      </div>

      {showSuggestions && input && filtered.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
          marginTop: 4, background: CARD_BG, border: `1px solid ${BORDER}`,
          borderRadius: RADIUS.md, maxHeight: 180, overflowY: 'auto',
          boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        }}>
          {filtered.map((s, i) => (
            <div
              key={s}
              onClick={() => addTag(s)}
              style={{
                padding: '8px 12px', cursor: 'pointer', fontSize: 14,
                color: i === highlightIndex ? TEXT_WHITE : TEXT_PRIMARY,
                background: i === highlightIndex ? '#1a5ce740' : 'transparent',
              }}
              onMouseEnter={() => setHighlightIndex(i)}
            >
              {s}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
