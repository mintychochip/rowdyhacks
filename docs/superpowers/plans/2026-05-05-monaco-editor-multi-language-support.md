# Monaco Editor Multi-Language Support Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Monaco editor in the AI assistant visibly support Python, TypeScript, Go, and other languages — not just JavaScript.

**Architecture:** Extract duplicate language mappings into a shared `languageConfig.ts`, add `beforeMount` for TypeScript compiler options, build a New File dialog and template picker, and update both editor components.

**Tech Stack:** React + Vite + TypeScript, `@monaco-editor/react` v4.7.0, `monaco-editor` v0.55.1

**Spec:** `docs/superpowers/specs/2026-05-05-monaco-editor-multi-language-support-design.md`

---

## Chunk 1: Shared Language Config

**Files:**
- Create: `frontend/src/utils/languageConfig.ts`

Pure extraction from both editors with no behavioral changes. The superset of all mappings currently in `StandaloneEditor.tsx` and `CodeEditor.tsx`.

- [ ] **Step 1: Create `frontend/src/utils/languageConfig.ts`**

```typescript
// ── Extension → Monaco language ID ─────────────────────────
export const LANGUAGE_MAP: Record<string, string> = {
  js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
  html: 'html', htm: 'html', css: 'css', scss: 'scss', less: 'less',
  py: 'python', ino: 'cpp', cpp: 'cpp', c: 'c', json: 'json',
  md: 'markdown', yaml: 'yaml', yml: 'yaml', xml: 'xml',
  svg: 'xml', sql: 'sql', sh: 'shell', bash: 'shell',
  gitignore: 'plaintext', env: 'plaintext',
};

export const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  return LANGUAGE_MAP[ext] || 'plaintext';
};

// ── Extension badge colors (for StandaloneEditor) ──────────
export const EXT_BADGE_COLORS: Record<string, string> = {
  ts: '#3178c6', tsx: '#61dafb', js: '#f7df1e', jsx: '#61dafb',
  html: '#e34f26', css: '#1572b6', scss: '#cc6699', py: '#3776ab',
  json: '#292929', md: '#42a5f5', yaml: '#cb171e', yml: '#cb171e',
  svg: '#ffb13b', sql: '#e38c00', sh: '#4eaa25',
  gitignore: '#f05032', env: '#ecd53f',
};

export const getExtBadge = (name: string): { label: string; color: string } => {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  return { label: `.${ext}`, color: EXT_BADGE_COLORS[ext] || '#64748b' };
};

// ── File icons (for CodeEditor) ────────────────────────────
export const FILE_ICONS: Record<string, string> = {
  js: '📜', ts: '📘', jsx: '⚛️', tsx: '⚛️', html: '🌐', css: '🎨',
  py: '🐍', ino: '🔌', json: '📋', md: '📝',
};

export const getFileIcon = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  return FILE_ICONS[ext] || '📄';
};

// ── Starter Templates ──────────────────────────────────────
export interface FileEntry {
  id: string;
  path: string;
  content: string;
  language: string;
}

export interface TemplateDef {
  name: string;
  description: string;
  files: FileEntry[];
}

let fileCounter = 0;
const fileId = () => `f-${Date.now()}-${++fileCounter}`;

const WEB_APP: TemplateDef = {
  name: 'Web App',
  description: 'HTML + CSS + JavaScript',
  files: [
    { id: fileId(), path: 'README.md', content: '# My Project\n\nBuilt with Hack the Valley AI Assistant.\n', language: 'markdown' },
    { id: fileId(), path: 'src/index.html', content: '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>My Project</title>\n  <link rel="stylesheet" href="css/style.css">\n</head>\n<body>\n  <h1>Hello World</h1>\n  <script src="js/app.js"></script>\n</body>\n</html>\n', language: 'html' },
    { id: fileId(), path: 'src/css/style.css', content: 'body {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n  padding: 2rem;\n  background: #0f172a;\n  color: #f1f5f9;\n}\n\nh1 {\n  font-size: 2rem;\n  font-weight: 700;\n}\n', language: 'css' },
    { id: fileId(), path: 'src/js/app.js', content: 'document.addEventListener("DOMContentLoaded", () => {\n  console.log("App ready!");\n});\n', language: 'javascript' },
  ],
};

const PYTHON: TemplateDef = {
  name: 'Python Script',
  description: 'Python with argparse',
  files: [
    { id: fileId(), path: 'README.md', content: '# Python Project\n\nBuilt with Hack the Valley AI Assistant.\n', language: 'markdown' },
    { id: fileId(), path: 'main.py', content: 'import argparse\n\n\ndef main():\n    parser = argparse.ArgumentParser(description="Your script")\n    parser.add_argument("--name", default="World", help="Who to greet")\n    args = parser.parse_args()\n    print(f"Hello, {args.name}!")\n\n\nif __name__ == "__main__":\n    main()\n', language: 'python' },
    { id: fileId(), path: 'requirements.txt', content: '# Add your dependencies here\n# e.g., requests>=2.31.0\n', language: 'plaintext' },
  ],
};

const TYPESCRIPT: TemplateDef = {
  name: 'TypeScript App',
  description: 'TypeScript with strict mode',
  files: [
    { id: fileId(), path: 'README.md', content: '# TypeScript Project\n\nBuilt with Hack the Valley AI Assistant.\n', language: 'markdown' },
    { id: fileId(), path: 'src/index.ts', content: 'interface AppConfig {\n  title: string;\n  version: string;\n}\n\nconst config: AppConfig = {\n  title: "My App",\n  version: "1.0.0",\n};\n\ndocument.addEventListener("DOMContentLoaded", () => {\n  const root = document.getElementById("root");\n  if (root) {\n    root.textContent = `Welcome to ${config.title}`;\n  }\n  console.log("App ready!", config);\n});\n', language: 'typescript' },
    { id: fileId(), path: 'tsconfig.json', content: '{\n  "compilerOptions": {\n    "target": "ES2022",\n    "module": "ESNext",\n    "strict": true,\n    "jsx": "react",\n    "moduleResolution": "bundler",\n    "esModuleInterop": true,\n    "skipLibCheck": true\n  },\n  "include": ["src"]\n}\n', language: 'json' },
  ],
};

const GO: TemplateDef = {
  name: 'Go App',
  description: 'Go HTTP server',
  files: [
    { id: fileId(), path: 'README.md', content: '# Go Project\n\nBuilt with Hack the Valley AI Assistant.\n', language: 'markdown' },
    { id: fileId(), path: 'main.go', content: 'package main\n\nimport (\n\t"fmt"\n\t"log"\n\t"net/http"\n)\n\nfunc main() {\n\thttp.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n\t\tfmt.Fprintf(w, "Hello from Go!")\n\t})\n\tlog.Println("Server starting on :8080")\n\tlog.Fatal(http.ListenAndServe(":8080", nil))\n}\n', language: 'go' },
    { id: fileId(), path: 'go.mod', content: 'module example.com/myapp\n\ngo 1.22\n', language: 'plaintext' },
  ],
};

export const TEMPLATES: TemplateDef[] = [WEB_APP, PYTHON, TYPESCRIPT, GO];
```

- [ ] **Step 2: Verify the file builds**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No type errors

---

## Chunk 2: Update StandaloneEditor.tsx

**Files:**
- Modify: `frontend/src/components/assistant/StandaloneEditor.tsx`

Replace local `getLanguageFromPath`, `getExtBadge`, `STARTER_FILES` with imports from `languageConfig`. Add `beforeMount` for TypeScript config. Add template state.

- [ ] **Step 1: Add imports and remove local helpers**

Replace the top of StandaloneEditor.tsx. Remove the local `getLanguageFromPath`, `getExtBadge`, `FileEntry` (will import it), and `STARTER_FILES`.

Add these imports:
```typescript
import {
  getLanguageFromPath, getExtBadge,
  TEMPLATES, type TemplateDef,
} from '../../utils/languageConfig';
export type { FileEntry } from '../../utils/languageConfig';
```

Keep the existing `interface FileEntry` — actually, remove it and re-export from the shared module. This keeps the `AssistantPage.tsx` import working (`import StandaloneEditor, { type FileEntry } from ...`).

- [ ] **Step 2: Add beforeMount handler**

Add a handler for the `<Editor>` `beforeMount` prop:

```typescript
const handleBeforeMount = useCallback((monaco: typeof import('monaco-editor')) => {
  monaco.languages.typescript.javascriptDefaults.setCompilerOptions({
    target: monaco.languages.typescript.ScriptTarget.ES2022,
    strict: true,
    moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
    esModuleInterop: true,
    allowNonTsExtensions: true,
  });

  monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
    target: monaco.languages.typescript.ScriptTarget.ES2022,
    strict: true,
    jsx: monaco.languages.typescript.JsxEmit.React,
    moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
    esModuleInterop: true,
  });
}, []);
```

- [ ] **Step 3: Add template state**

Replace `const [files, setFiles] = useState<FileEntry[]>(STARTER_FILES);` with:
```typescript
const [files, setFiles] = useState<FileEntry[]>(() => [...TEMPLATES[0].files]);
```

- [ ] **Step 4: Add beforeMount to Editor component**

Update the `<Editor>` component to pass `beforeMount={handleBeforeMount}`:
```tsx
<Editor height="100%" language={activeFile.language} value={activeFile.content}
  theme="hackthevalley-dark"
  options={editorOptions as any}
  onChange={handleEditorChange}
  beforeMount={handleBeforeMount}
  onMount={handleEditorDidMount}
  loading={...} />
```

- [ ] **Step 5: Add TEMPLATES and handleLoadTemplate**

Before the return statement, add:
```typescript
const [showTemplatePicker, setShowTemplatePicker] = useState(false);

const handleLoadTemplate = useCallback((template: TemplateDef) => {
  setFiles([...template.files]);
  setActiveFileId(template.files[0].id);
  setOpenTabs([template.files[0].id]);
  setExpanded(new Set(['src']));
  setShowTemplatePicker(false);
}, []);
```

- [ ] **Step 6: Add TemplatePicker component**

Above the `StandaloneEditor` component (or in a separate message), add a small template picker overlay:

```tsx
function TemplatePicker({
  templates, onSelect, onCancel,
}: {
  templates: TemplateDef[];
  onSelect: (t: TemplateDef) => void;
  onCancel: () => void;
}) {
  return (
    <div style={{
      position: 'absolute', inset: 0, zIndex: 10,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.5)',
    }}>
      <div style={{
        background: '#1e293b', borderRadius: 12,
        padding: 24, width: 420, maxWidth: '90%',
        boxShadow: '0 25px 50px rgba(0,0,0,0.4)',
      }}>
        <h3 style={{ margin: '0 0 4px', color: '#f1f5f9', fontSize: 16, fontWeight: 600 }}>New Project</h3>
        <p style={{ margin: '0 0 16px', color: '#94a3b8', fontSize: 13 }}>Choose a starter template</p>
        {templates.map(t => (
          <button key={t.name} onClick={() => onSelect(t)}
            style={{
              display: 'block', width: '100%', textAlign: 'left',
              padding: '10px 14px', marginBottom: 8,
              background: '#0f172a', border: '1px solid #334155',
              borderRadius: 8, cursor: 'pointer', color: '#f1f5f9',
              transition: 'border-color 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#2563eb'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#334155'; }}
          >
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2 }}>{t.name}</div>
            <div style={{ color: '#94a3b8', fontSize: 12 }}>{t.description} &middot; {t.files.length} files</div>
          </button>
        ))}
        <button onClick={onCancel}
          style={{
            width: '100%', padding: '8px', marginTop: 4,
            background: 'transparent', border: 'none',
            color: '#94a3b8', cursor: 'pointer', fontSize: 13,
          }}
          onMouseEnter={e => { e.currentTarget.style.color = '#f1f5f9'; }}
          onMouseLeave={e => { e.currentTarget.style.color = '#94a3b8'; }}
        >Cancel</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Wire up the "New Project" confirmation and template picker**

Before the Explorer header, add a confirmation check:
```typescript
const handleNewProjectClick = useCallback(() => {
  const hasChanges = files.some(f => f.content.length > 0);
  if (hasChanges && !window.confirm('This will replace all current files. Continue?')) return;
  setShowTemplatePicker(true);
}, [files]);
```

And wrap the editor area with a relative container so the template picker overlay works:
```tsx
<div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden', position: 'relative' }}>
  {showTemplatePicker && (
    <TemplatePicker
      templates={TEMPLATES}
      onSelect={handleLoadTemplate}
      onCancel={() => setShowTemplatePicker(false)} />
  )}
  {/* existing tab bar, editor, status bar */}
</div>
```

- [ ] **Step 8: Replace explorer header buttons**

Replace the current "+" and "+F" buttons in the Explorer header with a single "New" dropdown:

```tsx
{/* In the Explorer header, replace the button div: */}
<div style={{ display: 'flex', gap: 2, position: 'relative' }}>
  <button onClick={() => setShowNewMenu(!showNewMenu)}
    title="New..."
    style={iconBtnStyle}>+</button>
  {showNewMenu && (
    <div style={{
      position: 'absolute', top: '100%', left: 0, zIndex: 20,
      background: '#1e293b', border: '1px solid #334155',
      borderRadius: 8, padding: 4, minWidth: 140,
      boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
    }}>
      {[
        { label: 'New File', action: () => { setShowNewMenu(false); handleCreateFile(''); } },
        { label: 'New Folder', action: () => { setShowNewMenu(false); handleCreateFolder(''); } },
        { label: 'New Project', action: () => { setShowNewMenu(false); handleNewProjectClick(); } },
      ].map(item => (
        <button key={item.label} onClick={item.action}
          style={{
            display: 'block', width: '100%', textAlign: 'left',
            padding: '6px 10px', background: 'transparent', border: 'none',
            color: '#94a3b8', cursor: 'pointer', fontSize: 12, borderRadius: 4,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#334155'; e.currentTarget.style.color = '#f1f5f9'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94a3b8'; }}
        >{item.label}</button>
      ))}
    </div>
  )}
</div>
```

Add `showNewMenu` state:
```typescript
const [showNewMenu, setShowNewMenu] = useState(false);
```

And close the menu when clicking outside:
```typescript
useEffect(() => {
  if (!showNewMenu) return;
  const close = () => setShowNewMenu(false);
  window.addEventListener('click', close);
  return () => window.removeEventListener('click', close);
}, [showNewMenu]);
```

- [ ] **Step 9: Verify TypeScript compiles**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No type errors

---

## Chunk 3: Update CodeEditor.tsx

**Files:**
- Modify: `frontend/src/components/builder/editor/CodeEditor.tsx`

Replace local helpers with shared config, add `beforeMount` for TypeScript.

- [ ] **Step 1: Replace imports and remove local helpers**

Remove local `getLanguageFromPath`, `getFileIcon`. Add import:
```typescript
import { getLanguageFromPath, getFileIcon } from '../../../utils/languageConfig';
```

Keep the `CodeEditorProps` interface and all other code unchanged.

- [ ] **Step 2: Add beforeMount handler**

Add the same `beforeMount` handler as StandaloneEditor:
```typescript
const handleBeforeMount = useCallback((monaco: typeof import('monaco-editor')) => {
  monaco.languages.typescript.javascriptDefaults.setCompilerOptions({
    target: monaco.languages.typescript.ScriptTarget.ES2022,
    strict: true,
    moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
    esModuleInterop: true,
    allowNonTsExtensions: true,
  });

  monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
    target: monaco.languages.typescript.ScriptTarget.ES2022,
    strict: true,
    jsx: monaco.languages.typescript.JsxEmit.React,
    moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
    esModuleInterop: true,
  });
}, []);
```

- [ ] **Step 3: Wire beforeMount to Editor**

Pass `beforeMount={handleBeforeMount}` to the `<Editor>` component on line 143.

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No type errors

---

## Chunk 4: New File Dialog

**Files:**
- Create: `frontend/src/components/assistant/NewFileDialog.tsx`
- Modify: `frontend/src/components/assistant/StandaloneEditor.tsx`

- [ ] **Step 1: Create `frontend/src/components/assistant/NewFileDialog.tsx`**

```tsx
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
```

- [ ] **Step 2: Wire NewFileDialog into StandaloneEditor**

Add state:
```typescript
const [showNewFileDialog, setShowNewFileDialog] = useState(false);
```

Replace the `handleCreateFile` to use the dialog:
```typescript
const handleNewFileClick = useCallback(() => {
  setShowNewFileDialog(true);
}, []);

const handleCreateFileFromDialog = useCallback((name: string) => {
  const id = `file-${Date.now()}`;
  const f: FileEntry = { id, path: name, content: '', language: getLanguageFromPath(name) };
  setFiles(prev => [...prev, f]);
  setActiveFileId(id);
  setOpenTabs(prev => [...prev, id]);
  setShowNewFileDialog(false);
}, []);
```

Wire the "New File" menu item: change `handleCreateFile('')` to `handleNewFileClick`.

Add the dialog in the editor area:
```tsx
{showNewFileDialog && (
  <NewFileDialog
    existingPaths={files.map(f => f.path)}
    onConfirm={handleCreateFileFromDialog}
    onCancel={() => setShowNewFileDialog(false)} />
)}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No type errors

---

## Chunk 5: Close menu on click outside + cleanup

- [ ] **Step 1: Add click-outside handler for the New menu**

In StandaloneEditor, add the existing `useEffect` for closing the new menu (already described above).

- [ ] **Step 2: Remove unused handleCreateFile and handleCreateFolder**

After wiring the New File Dialog, `handleCreateFile` and `handleCreateFolder` are still used for New Folder (which still uses `prompt()`). Keep `handleCreateFolder` unchanged. The old `handleCreateFile` with `prompt()` is replaced by the dialog — remove it.

- [ ] **Step 3: Final TypeScript check**

Run: `cd frontend && npx tsc -b --noEmit`
Expected: No type errors

---

## Chunk 6: Verification

- [ ] **Step 1: Build the frontend**

Run: `cd frontend && npx vite build`
Expected: Build succeeds with no errors

- [ ] **Step 2: Check config parity**

Verify that `getLanguageFromPath` mappings are correct by checking the shared module covers both editors' previous mappings:
- `getLanguageFromPath('file.ino') === 'cpp'` (was only in CodeEditor)
- `getLanguageFromPath('file.svg') === 'xml'` (was only in StandaloneEditor)
- `getLanguageFromPath('file.sh') === 'shell'` (was only in StandaloneEditor)
- `getLanguageFromPath('file.env') === 'plaintext'` (was only in StandaloneEditor)

These are all in the shared `LANGUAGE_MAP` now.

- [ ] **Step 3: Verify no regressions in the builder**

Check that `CodeEditor.tsx` still renders correctly with imported `getLanguageFromPath` and `getFileIcon`:
- `getFileIcon('app.ts')` returns `'📘'` (was in CodeEditor's local map)
- `getFileIcon('app.svelte')` returns `'📄'` (fallback, unchanged)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/languageConfig.ts
git add frontend/src/components/assistant/StandaloneEditor.tsx
git add frontend/src/components/assistant/NewFileDialog.tsx
git add frontend/src/components/builder/editor/CodeEditor.tsx
git commit -m "feat: multi-language support for Monaco editor

- Extract shared language config into utils/languageConfig.ts
- Add beforeMount for TypeScript strict mode in both editors
- Add template picker with Web, Python, TypeScript, Go templates
- Add New File dialog with quick extension buttons
- Replace explorer +/+F buttons with unified New dropdown

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
