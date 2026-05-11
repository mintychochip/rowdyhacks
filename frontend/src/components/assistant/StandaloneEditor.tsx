import { useCallback, useState, useMemo, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import {
  CARD_BG,
  INPUT_BG,
  PRIMARY,
  RADIUS,
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER,
} from '../../theme';
import {
  getLanguageFromPath, getExtBadge,
  TEMPLATES, type TemplateDef,
} from '../../utils/languageConfig';
import type { FileEntry } from '../../utils/languageConfig';
import NewFileDialog from './NewFileDialog';
export type { FileEntry };

interface TreeNode {
  name: string;
  path: string;
  isFolder: boolean;
  children: TreeNode[];
  file?: FileEntry;
}

function buildTree(files: FileEntry[]): TreeNode[] {
  const root: TreeNode[] = [];
  for (const file of files) {
    const parts = file.path.split('/');
    let current = root;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const currentPath = parts.slice(0, i + 1).join('/');
      let node = current.find(n => n.name === part);
      if (!node) {
        node = { name: part, path: currentPath, isFolder: !isLast, children: [], file: isLast ? file : undefined };
        current.push(node);
      }
      if (isLast) { node.isFolder = false; node.file = file; }
      current = node.children;
    }
  }
  const sort = (ns: TreeNode[]) => {
    ns.sort((a, b) => {
      if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    for (const n of ns) if (n.isFolder) sort(n.children);
  };
  sort(root);
  return root;
}

// ── Tree Node Component ────────────────────────────────────────

function TreeNodeRow({
  node, depth, activeFileId, expanded, onToggle, onSelect,
}: {
  node: TreeNode; depth: number; activeFileId: string | null;
  expanded: Set<string>; onToggle: (p: string) => void; onSelect: (id: string) => void;
}) {
  const indent = depth * 16 + 8;
  const isExpanded = expanded.has(node.path);
  const isActive = node.file?.id === activeFileId;

  if (node.isFolder) {
    return (
      <>
        <div
          onClick={() => onToggle(node.path)}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: `2px ${SPACE.sm}px 2px ${indent}px`,
            cursor: 'pointer', borderRadius: RADIUS.sm,
            color: TEXT_SECONDARY, fontSize: 13, userSelect: 'none',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = INPUT_BG; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
        >
          <span style={{
            fontSize: 10, width: 12, textAlign: 'center',
            transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 0.12s',
          }}>▶</span>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={isExpanded ? '#60a5fa' : TEXT_MUTED} strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{node.name}</span>
        </div>
        {isExpanded && node.children.map(c => (
          <TreeNodeRow key={c.path} node={c} depth={depth + 1} activeFileId={activeFileId} expanded={expanded} onToggle={onToggle} onSelect={onSelect} />
        ))}
      </>
    );
  }

  const badge = getExtBadge(node.name);
  return (
    <div
      onClick={() => { if (node.file) onSelect(node.file.id); }}
      style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: `2px ${SPACE.sm}px 2px ${indent + 12}px`,
        cursor: 'pointer', borderRadius: RADIUS.sm,
        color: isActive ? TEXT_PRIMARY : TEXT_SECONDARY,
        background: isActive ? 'rgba(94, 106, 210, 0.12)' : 'transparent',
        fontSize: 13, userSelect: 'none',
      }}
      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = INPUT_BG; }}
      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = isActive ? 'rgba(94, 106, 210, 0.12)' : 'transparent'; }}
    >
      <span style={{
        fontSize: 9, fontWeight: 700, color: badge.color,
        width: 28, textAlign: 'right', fontFamily: 'JetBrains Mono, monospace',
        letterSpacing: '-0.02em',
      }}>{badge.label}</span>
      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{node.name}</span>
    </div>
  );
}

// ── Template Picker ───────────────────────────────────────────

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

// ── StandaloneEditor Component ─────────────────────────────────

interface StandaloneEditorProps {
  height?: string;
  onFilesChange?: (files: FileEntry[]) => void;
}

export default function StandaloneEditor({ height = '100%', onFilesChange }: StandaloneEditorProps) {
  const [files, setFiles] = useState<FileEntry[]>(() => [...TEMPLATES[0].files]);
  const [activeFileId, setActiveFileId] = useState<string>(TEMPLATES[0].files[0].id);
  const [openTabs, setOpenTabs] = useState<string[]>([TEMPLATES[0].files[0].id]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['src']));
  const [editorInstance, setEditorInstance] = useState<import('monaco-editor').editor.IStandaloneCodeEditor | null>(null);
  const [explorerWidth, setExplorerWidth] = useState(200);
  const [isDragging, setIsDragging] = useState(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [showNewFileDialog, setShowNewFileDialog] = useState(false);
  const [showNewMenu, setShowNewMenu] = useState(false);

  const activeFile = files.find(f => f.id === activeFileId);
  const tree = useMemo(() => buildTree(files), [files]);

  useEffect(() => { onFilesChange?.(files); }, [files, onFilesChange]);

  // Resize
  useEffect(() => {
    if (!isDragging) return;
    const mm = (e: MouseEvent) => setExplorerWidth(Math.max(140, Math.min(350, e.clientX - 260)));
    const mu = () => setIsDragging(false);
    window.addEventListener('mousemove', mm);
    window.addEventListener('mouseup', mu);
    return () => { window.removeEventListener('mousemove', mm); window.removeEventListener('mouseup', mu); };
  }, [isDragging]);

  useEffect(() => {
    if (!showNewMenu) return;
    const close = () => setShowNewMenu(false);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [showNewMenu]);

  // Monaco
  const handleBeforeMount = useCallback((m: any) => {
    m.languages.typescript.javascriptDefaults.setCompilerOptions({
      target: m.languages.typescript.ScriptTarget.ES2022,
      strict: true,
      moduleResolution: m.languages.typescript.ModuleResolutionKind.Node10,
      esModuleInterop: true,
      allowNonTsExtensions: true,
    });
    m.languages.typescript.typescriptDefaults.setCompilerOptions({
      target: m.languages.typescript.ScriptTarget.ES2022,
      strict: true,
      jsx: m.languages.typescript.JsxEmit.React,
      moduleResolution: m.languages.typescript.ModuleResolutionKind.Node10,
      esModuleInterop: true,
    });
  }, []);

  const handleEditorDidMount = useCallback((editor: import('monaco-editor').editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => {
    setEditorInstance(editor);
    monaco.editor.defineTheme('openhack-dark', {
      base: 'vs-dark', inherit: true,
      rules: [
        { token: 'comment', foreground: '64748B', fontStyle: 'italic' },
        { token: 'keyword', foreground: '60A5FA' },
        { token: 'string', foreground: '34D399' },
        { token: 'number', foreground: 'FBBF24' },
        { token: 'type', foreground: '22D3EE' },
        { token: 'function', foreground: 'A78BFA' },
      ],
      colors: {
        'editor.background': '#1E293B',
        'editor.foreground': '#F1F5F9',
        'editor.lineHighlightBackground': '#33415550',
        'editor.selectionBackground': '#2563EB40',
        'editorCursor.foreground': '#2563EB',
        'editorLineNumber.foreground': '#64748B',
        'editorLineNumber.activeForeground': '#F1F5F9',
        'scrollbarSlider.background': '#47556980',
        'scrollbarSlider.hoverBackground': '#64748BB0',
      },
    });
    monaco.editor.setTheme('openhack-dark');
  }, []);

  const handleEditorChange = useCallback((value: string | undefined) => {
    if (value === undefined || !activeFileId) return;
    setFiles(prev => prev.map(f => f.id === activeFileId ? { ...f, content: value } : f));
  }, [activeFileId]);

  const handleSelectFile = useCallback((fileId: string) => {
    setActiveFileId(fileId);
    setOpenTabs(prev => prev.includes(fileId) ? prev : [...prev, fileId]);
  }, []);

  const handleCloseTab = useCallback((fileId: string) => {
    setOpenTabs(prev => {
      const filtered = prev.filter(id => id !== fileId);
      if (fileId === activeFileId && filtered.length > 0) setActiveFileId(filtered[filtered.length - 1]);
      return filtered;
    });
  }, [activeFileId]);

  const handleToggleFolder = useCallback((path: string) => {
    setExpanded(prev => { const n = new Set(prev); if (n.has(path)) n.delete(path); else n.add(path); return n; });
  }, []);

  const handleCreateFolder = useCallback((parentPath: string) => {
    const name = prompt('Folder name:');
    if (!name) return;
    const path = parentPath ? `${parentPath}/${name}` : name;
    const id = `file-${Date.now()}`;
    setFiles(prev => [...prev, { id, path: `${path}/.gitkeep`, content: '', language: 'plaintext' }]);
    setExpanded(prev => new Set([...prev, path]));
  }, []);

  const openTabFiles = openTabs.map(id => files.find(f => f.id === id)).filter((f): f is FileEntry => f !== undefined);

  type MonacoEditorOptions = import('monaco-editor').editor.IStandaloneEditorConstructionOptions;
  const editorOptions: MonacoEditorOptions = {
    minimap: { enabled: false },
    fontSize: 13,
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    lineNumbers: 'on' as const,
    scrollBeyondLastLine: false,
    readOnly: false,
    automaticLayout: true,
    padding: { top: 12, bottom: 12 },
    folding: true,
    renderLineHighlight: 'all' as const,
    matchBrackets: 'always' as const,
    tabSize: 2, insertSpaces: true,
    wordWrap: 'on' as const,
    smoothScrolling: true,
    cursorBlinking: 'smooth' as const,
    formatOnPaste: true,
  };

  const handleLoadTemplate = useCallback((template: TemplateDef) => {
    if (template.files.length === 0) {
      setFiles([]);
      setActiveFileId('');
      setOpenTabs([]);
      setExpanded(new Set());
      setShowTemplatePicker(false);
      return;
    }
    setFiles([...template.files]);
    setActiveFileId(template.files[0].id);
    setOpenTabs([template.files[0].id]);
    setExpanded(new Set(template.files.some(f => f.path.startsWith('src/')) ? ['src'] : []));
    setShowTemplatePicker(false);
  }, []);

  const handleNewProjectClick = useCallback(() => {
    const hasChanges = files.some(f => f.content.length > 0);
    if (hasChanges && !window.confirm('This will replace all current files. Continue?')) return;
    setShowTemplatePicker(true);
  }, [files]);

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

  return (
    <div style={{ display: 'flex', height, background: CARD_BG, overflow: 'hidden' }}>
      {/* File Explorer */}
      <div style={{ width: explorerWidth, minWidth: 140, display: 'flex', flexDirection: 'column', borderRight: `1px solid ${BORDER}`, background: CARD_BG, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: `6px ${SPACE.md}px`, fontSize: 10, fontWeight: 600, color: TEXT_MUTED, textTransform: 'uppercase', letterSpacing: '0.06em', borderBottom: `1px solid ${BORDER}`, flexShrink: 0 }}>
          Explorer
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
                  { label: 'New File', action: () => { setShowNewMenu(false); handleNewFileClick(); } },
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
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: `${SPACE.xs}px 0` }}>
          {tree.map(n => <TreeNodeRow key={n.path} node={n} depth={0} activeFileId={activeFileId} expanded={expanded} onToggle={handleToggleFolder} onSelect={handleSelectFile} />)}
        </div>
      </div>

      {/* Resize handle */}
      <div onMouseDown={() => setIsDragging(true)}
        style={{ width: 3, cursor: 'col-resize', background: 'transparent', flexShrink: 0 }}
        onMouseEnter={e => { e.currentTarget.style.background = PRIMARY; }}
        onMouseLeave={e => { if (!isDragging) e.currentTarget.style.background = 'transparent'; }}
      />

      {/* Editor Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden', position: 'relative' }}>
        {showTemplatePicker && (
          <TemplatePicker
            templates={TEMPLATES}
            onSelect={handleLoadTemplate}
            onCancel={() => setShowTemplatePicker(false)} />
        )}
        {showNewFileDialog && (
          <NewFileDialog
            existingPaths={files.map(f => f.path)}
            onConfirm={handleCreateFileFromDialog}
            onCancel={() => setShowNewFileDialog(false)} />
        )}
        {openTabFiles.length > 0 && (
          <div style={{ display: 'flex', background: CARD_BG, borderBottom: `1px solid ${BORDER}`, overflowX: 'auto', flexShrink: 0 }}>
            {openTabFiles.map(file => {
              const isActive = file.id === activeFileId;
              const name = file.path.split('/').pop() || file.path;
              const badge = getExtBadge(name);
              return (
                <div key={file.id} onClick={() => setActiveFileId(file.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: `6px ${SPACE.md}px`, cursor: 'pointer',
                    background: isActive ? INPUT_BG : 'transparent',
                    borderRight: `1px solid ${BORDER}`,
                    borderBottom: `2px solid ${isActive ? PRIMARY : 'transparent'}`,
                    fontSize: 12, color: isActive ? TEXT_PRIMARY : TEXT_MUTED,
                    fontWeight: isActive ? 500 : 400, userSelect: 'none',
                    whiteSpace: 'nowrap',
                  }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: badge.color, fontFamily: 'JetBrains Mono, monospace' }}>{badge.label}</span>
                  <span style={{ maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis' }}>{name}</span>
                  <button onClick={e => { e.stopPropagation(); handleCloseTab(file.id); }}
                    style={{ background: 'transparent', border: 'none', color: TEXT_MUTED, cursor: 'pointer', fontSize: 10, padding: '1px 4px', borderRadius: 3, marginLeft: 2 }}
                    onMouseEnter={e => { e.currentTarget.style.color = TEXT_PRIMARY; }}
                    onMouseLeave={e => { e.currentTarget.style.color = TEXT_MUTED; }}>×</button>
                </div>
              );
            })}
          </div>
        )}

        <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
          {activeFile ? (
            <Editor height="100%" language={activeFile.language} value={activeFile.content} theme="openhack-dark"
              options={editorOptions} onChange={handleEditorChange}
              beforeMount={handleBeforeMount}
              onMount={handleEditorDidMount}
              loading={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: TEXT_MUTED, fontSize: 13 }}>Loading editor...</div>} />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: TEXT_MUTED, fontSize: 13, flexDirection: 'column', gap: SPACE.md }}>
              <span>Select a file to edit</span>
            </div>
          )}
        </div>

        {/* Status bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: `2px ${SPACE.md}px`, background: INPUT_BG, borderTop: `1px solid ${BORDER}`, fontSize: 11, color: TEXT_MUTED, flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: SPACE.md }}>
            <span>{activeFile?.language?.toUpperCase() || 'PLAINTEXT'}</span>
            <span>{files.length} files</span>
          </div>
          <div style={{ display: 'flex', gap: SPACE.md }}>
            <span>Ln {editorInstance?.getPosition()?.lineNumber || 1}, Col {editorInstance?.getPosition()?.column || 1}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

const iconBtnStyle: React.CSSProperties = {
  background: 'transparent', border: 'none', color: TEXT_MUTED,
  cursor: 'pointer', fontSize: 11, padding: '0 4px', borderRadius: 3,
  fontFamily: 'JetBrains Mono, monospace',
};
