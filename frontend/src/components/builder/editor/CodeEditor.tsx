import { useCallback, useState } from 'react';
import Editor from '@monaco-editor/react';
import { useBuilderStore } from '../../../stores/builderStore';
import { CARD_BG, INPUT_BG, PRIMARY, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, SUCCESS, BORDER_LIGHT } from '../../../theme';

const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  const langMap: Record<string, string> = {
    js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
    html: 'html', htm: 'html', css: 'css', scss: 'scss', less: 'less',
    py: 'python', ino: 'cpp', cpp: 'cpp', c: 'c', json: 'json',
    md: 'markdown', yaml: 'yaml', yml: 'yaml', xml: 'xml',
  };
  return langMap[ext] || 'plaintext';
};

const defineCustomTheme = (monaco: typeof import('monaco-editor')) => {
  monaco.editor.defineTheme('hackthevalley-dark', {
    base: 'vs-dark',
    inherit: true,
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
};

const getFileIcon = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const iconMap: Record<string, string> = {
    js: '📜', ts: '📘', jsx: '⚛️', tsx: '⚛️', html: '🌐', css: '🎨',
    py: '🐍', ino: '🔌', json: '📋', md: '📝',
  };
  return iconMap[ext] || '📄';
};

interface CodeEditorProps {
  height?: string;
}

export default function CodeEditor({ height = '100%' }: CodeEditorProps) {
  const { project, currentFileId, updateFile, removeOpenFile, setCurrentFileId, openFiles } = useBuilderStore();
  const [editorInstance, setEditorInstance] = useState<import('monaco-editor').editor.IStandaloneCodeEditor | null>(null);
  const [isEditorReady, setIsEditorReady] = useState(false);

  const currentFile = project?.files.find((f) => f.id === currentFileId);

  const handleEditorDidMount = useCallback((editor: import('monaco-editor').editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => {
    setEditorInstance(editor);
    defineCustomTheme(monaco);
    monaco.editor.setTheme('hackthevalley-dark');
    setIsEditorReady(true);
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => { console.log('Save triggered'); });
  }, []);

  const handleEditorChange = useCallback((value: string | undefined) => {
    if (currentFileId && value !== undefined) updateFile(currentFileId, value);
  }, [currentFileId, updateFile]);

  const handleCloseTab = useCallback((e: React.MouseEvent, fileId: string) => {
    e.stopPropagation();
    removeOpenFile(fileId);
  }, [removeOpenFile]);

  const handleTabClick = useCallback((fileId: string) => { setCurrentFileId(fileId); }, [setCurrentFileId]);

  const openFilesInfo = openFiles.map((id) => project?.files.find((f) => f.id === id)).filter((f): f is NonNullable<typeof f> => f !== undefined);

  const editorOptions = {
    minimap: { enabled: false },
    fontSize: 14,
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    readOnly: false,
    automaticLayout: true,
    padding: { top: 16, bottom: 16 },
    folding: true,
    renderLineHighlight: 'all',
    matchBrackets: 'always',
    tabSize: 2,
    insertSpaces: true,
    wordWrap: 'on',
    smoothScrolling: true,
    cursorBlinking: 'smooth',
    formatOnPaste: true,
    formatOnType: true,
  };

  if (!project) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height, background: CARD_BG }}><span style={{ color: TEXT_MUTED, fontSize: 14 }}>No project loaded</span></div>;
  }

  if (!currentFile) {
    return <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height, background: CARD_BG, gap: SPACE.md }}><span style={{ fontSize: 48 }}>📝</span><span style={{ color: TEXT_SECONDARY, fontSize: 14 }}>Select a file from the explorer to start editing</span></div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height, background: CARD_BG }}>
      {openFilesInfo.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.xs, padding: SPACE.xs + 'px', paddingBottom: 0, background: CARD_BG, borderBottom: '1px solid ' + BORDER_LIGHT, overflowX: 'auto' }}>
          {openFilesInfo.map((file) => {
            const isActive = file.id === currentFileId;
            const fileName = file.path.split('/').pop() || file.path;
            return (
              <div key={file.id} onClick={() => handleTabClick(file.id)} style={{ display: 'flex', alignItems: 'center', gap: SPACE.xs, padding: SPACE.xs + 'px ' + SPACE.sm + 'px', borderRadius: RADIUS.sm + 'px ' + RADIUS.sm + 'px 0 0', background: isActive ? INPUT_BG : 'transparent', borderBottom: '2px solid ' + (isActive ? PRIMARY : 'transparent'), cursor: 'pointer', minWidth: 0, flexShrink: 0 }}>
                <span style={{ fontSize: 12 }}>{getFileIcon(fileName)}</span>
                <span style={{ fontSize: 12, color: isActive ? TEXT_PRIMARY : TEXT_MUTED, fontWeight: isActive ? 500 : 400, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 120 }}>{fileName}</span>
                {file.isModified && <span style={{ width: 6, height: 6, borderRadius: '50%', background: SUCCESS, flexShrink: 0 }} />}
                <button onClick={(e) => handleCloseTab(e, file.id)} style={{ marginLeft: SPACE.xs, padding: '2px 4px', borderRadius: RADIUS.sm, border: 'none', background: 'transparent', color: TEXT_MUTED, fontSize: 10, cursor: 'pointer', opacity: 0.5 }}>✕</button>
              </div>
            );
          })}
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: SPACE.sm + 'px ' + SPACE.md + 'px', background: INPUT_BG, borderBottom: '1px solid ' + BORDER_LIGHT }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
          <span style={{ fontSize: 16 }}>{getFileIcon(currentFile.path.split('/').pop() || '')}</span>
          <span style={{ fontSize: 13, color: TEXT_PRIMARY, fontWeight: 500 }}>{currentFile.path}</span>
          {currentFile.isModified && <span style={{ fontSize: 11, color: SUCCESS, background: SUCCESS + '20', padding: '2px ' + SPACE.xs + 'px', borderRadius: RADIUS.sm }}>Modified</span>}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.md, fontSize: 12, color: TEXT_MUTED }}>
          <span>{getLanguageFromPath(currentFile.path)}</span>
          <span>{currentFile.content.length.toLocaleString()} chars</span>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Editor height="100%" language={getLanguageFromPath(currentFile.path)} value={currentFile.content} theme="hackthevalley-dark" options={editorOptions as any} onChange={handleEditorChange} onMount={handleEditorDidMount}
          loading={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: TEXT_MUTED }}>Loading editor...</div>} />
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: SPACE.xs + 'px ' + SPACE.md + 'px', background: INPUT_BG, borderTop: '1px solid ' + BORDER_LIGHT, fontSize: 11, color: TEXT_MUTED }}>
        <div style={{ display: 'flex', gap: SPACE.md }}>
          {isEditorReady ? <><span>UTF-8</span><span>{getLanguageFromPath(currentFile.path).toUpperCase()}</span></> : <span>Initializing...</span>}
        </div>
        <div style={{ display: 'flex', gap: SPACE.md }}>
          <span>Ln {editorInstance?.getPosition()?.lineNumber || 1}, Col {editorInstance?.getPosition()?.column || 1}</span>
          <span>2 spaces</span>
        </div>
      </div>
    </div>
  );
}
