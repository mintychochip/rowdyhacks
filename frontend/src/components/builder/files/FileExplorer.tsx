import { useState } from 'react';
import { useBuilderStore } from '../../../stores/builderStore';
import type { ProjectFile } from '../../../types/builder';
import { CARD_BG, INPUT_BG, PRIMARY, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, ERROR, SUCCESS, BORDER_LIGHT } from '../../../theme';

const getFileIcon = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const icons: Record<string, string> = {
    js: '📜', ts: '📘', jsx: '⚛️', tsx: '⚛️', html: '🌐', css: '🎨',
    py: '🐍', ino: '🔌', cpp: '⚙️', c: '⚙️', json: '📋', md: '📝',
  };
  return icons[ext] || '📄';
};

const getLang = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  const langs: Record<string, string> = {
    js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
    html: 'html', css: 'css', scss: 'scss', py: 'python', ino: 'cpp',
    cpp: 'cpp', c: 'c', json: 'json', md: 'markdown',
  };
  return langs[ext] || 'plaintext';
};

interface FileTreeNode {
  name: string; path: string; type: 'file' | 'directory';
  children?: FileTreeNode[]; file?: ProjectFile;
}

function buildFileTree(files: ProjectFile[]): FileTreeNode[] {
  const root: FileTreeNode[] = [];
  const dirMap = new Map<string, FileTreeNode>();

  files.forEach((file) => {
    const parts = file.path.split('/');
    let currentPath = '';
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      currentPath = currentPath ? currentPath + '/' + part : part;
      if (!dirMap.has(currentPath)) {
        const dirNode: FileTreeNode = { name: part, path: currentPath, type: 'directory', children: [] };
        dirMap.set(currentPath, dirNode);
        if (i === 0) root.push(dirNode);
        else {
          const parentPath = parts.slice(0, i).join('/');
          dirMap.get(parentPath)?.children?.push(dirNode);
        }
      }
    }
  });

  files.forEach((file) => {
    const parts = file.path.split('/');
    const fileName = parts[parts.length - 1];
    if (parts.length === 1) root.push({ name: fileName, path: file.path, type: 'file', file });
    else {
      const parentPath = parts.slice(0, -1).join('/');
      dirMap.get(parentPath)?.children?.push({ name: fileName, path: file.path, type: 'file', file });
    }
  });

  const sortNodes = (nodes: FileTreeNode[]) => {
    nodes.sort((a, b) => (a.type !== b.type ? (a.type === 'directory' ? -1 : 1) : a.name.localeCompare(b.name)));
    nodes.forEach((n) => n.children && sortNodes(n.children));
  };
  sortNodes(root);
  return root;
}

interface FileTreeItemProps {
  node: FileTreeNode; depth: number;
  onFileClick: (file: ProjectFile) => void;
  onDeleteFile: (fileId: string) => void;
  currentFileId: string | null;
}

function FileTreeItem({ node, depth, onFileClick, onDeleteFile, currentFileId }: FileTreeItemProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showDelete, setShowDelete] = useState(false);
  const isActive = node.file?.id === currentFileId;
  const isModified = node.file?.isModified;

  const handleClick = () => {
    if (node.type === 'directory') setIsExpanded(!isExpanded);
    else if (node.file) onFileClick(node.file);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (node.file && confirm('Delete ' + node.name + '?')) onDeleteFile(node.file.id);
  };

  return (
    <div>
      <div onClick={handleClick} onMouseEnter={() => node.type === 'file' && setShowDelete(true)} onMouseLeave={() => setShowDelete(false)}
        style={{
          display: 'flex', alignItems: 'center', gap: SPACE.xs,
          padding: SPACE.xs + 'px ' + SPACE.sm + 'px', paddingLeft: (SPACE.sm + depth * 16) + 'px',
          cursor: 'pointer', background: isActive ? PRIMARY + '30' : 'transparent',
          borderLeft: '3px solid ' + (isActive ? PRIMARY : 'transparent'), transition: 'all 0.15s ease',
        }}>
        {node.type === 'directory' && (
          <span style={{ fontSize: 10, color: TEXT_MUTED, transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }}>▶</span>
        )}
        <span style={{ fontSize: 14 }}>{node.type === 'directory' ? '📁' : getFileIcon(node.name)}</span>
        <span style={{ flex: 1, fontSize: 13, color: isActive ? TEXT_PRIMARY : TEXT_SECONDARY, fontWeight: isActive ? 500 : 400, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {node.name}
        </span>
        {isModified && <span style={{ width: 6, height: 6, borderRadius: '50%', background: SUCCESS }} />}
        {showDelete && node.type === 'file' && (
          <button onClick={handleDelete} style={{ padding: '2px 4px', borderRadius: RADIUS.sm, border: 'none', background: 'transparent', color: ERROR, fontSize: 12, cursor: 'pointer', opacity: 0.7 }}>🗑️</button>
        )}
      </div>
      {node.type === 'directory' && isExpanded && node.children && (
        <div>{node.children.map((child) => <FileTreeItem key={child.path} node={child} depth={depth + 1} onFileClick={onFileClick} onDeleteFile={onDeleteFile} currentFileId={currentFileId} />)}</div>
      )}
    </div>
  );
}

export default function FileExplorer() {
  const { project, currentFileId, setCurrentFileId, addOpenFile, removeOpenFile, setProject } = useBuilderStore();
  const [isCreating, setIsCreating] = useState(false);
  const [newFilePath, setNewFilePath] = useState('');

  if (!project) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', padding: SPACE.md }}><span style={{ color: TEXT_MUTED, fontSize: 13 }}>No project loaded</span></div>;
  }

  const tree = buildFileTree(project.files);
  const handleFileClick = (file: ProjectFile) => { setCurrentFileId(file.id); addOpenFile(file.id); };
  const handleDeleteFile = (fileId: string) => {
    setProject({ ...project, files: project.files.filter((f) => f.id !== fileId), currentFileId: currentFileId === fileId ? null : project.currentFileId });
    removeOpenFile(fileId);
  };
  const handleCreateFile = () => {
    if (!newFilePath.trim()) return;
    const path = newFilePath.startsWith('/') ? newFilePath.slice(1) : newFilePath;
    if (project.files.some((f) => f.path === path)) { alert('File ' + path + ' already exists'); return; }
    const newFile: ProjectFile = { id: Date.now() + '-' + Math.random().toString(36).substr(2, 9), path, content: '', language: getLang(path), isModified: false, isOpen: true };
    setProject({ ...project, files: [...project.files, newFile] });
    setCurrentFileId(newFile.id); addOpenFile(newFile.id); setNewFilePath(''); setIsCreating(false);
  };
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleCreateFile();
    else if (e.key === 'Escape') { setIsCreating(false); setNewFilePath(''); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: CARD_BG, borderRight: '1px solid ' + BORDER_LIGHT }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: SPACE.sm + 'px ' + SPACE.md + 'px', borderBottom: '1px solid ' + BORDER_LIGHT }}>
        <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1, color: TEXT_MUTED }}>Files</span>
        <button onClick={() => setIsCreating(true)} style={{ padding: SPACE.xs + 'px', borderRadius: RADIUS.sm, border: 'none', background: 'transparent', color: PRIMARY, fontSize: 16, cursor: 'pointer' }} title="New File">+📄</button>
      </div>
      {isCreating && (
        <div style={{ padding: SPACE.sm + 'px', borderBottom: '1px solid ' + BORDER_LIGHT }}>
          <input type="text" value={newFilePath} onChange={(e) => setNewFilePath(e.target.value)} onKeyDown={handleKeyDown} onBlur={() => { if (!newFilePath.trim()) setIsCreating(false); }} placeholder="path/to/file.js" autoFocus
            style={{ width: '100%', padding: SPACE.xs + 'px ' + SPACE.sm + 'px', borderRadius: RADIUS.sm, border: '1px solid ' + PRIMARY + '40', background: INPUT_BG, color: TEXT_PRIMARY, fontSize: 13, outline: 'none' }} />
        </div>
      )}
      <div style={{ flex: 1, overflow: 'auto', padding: SPACE.xs + 'px 0' }}>
        {tree.length === 0 ? <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: SPACE.lg }}><span style={{ color: TEXT_MUTED, fontSize: 13 }}>No files yet</span></div>
          : tree.map((node) => <FileTreeItem key={node.path} node={node} depth={0} onFileClick={handleFileClick} onDeleteFile={handleDeleteFile} currentFileId={currentFileId} />)}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: SPACE.sm + 'px ' + SPACE.md + 'px', borderTop: '1px solid ' + BORDER_LIGHT, fontSize: 12, color: TEXT_MUTED }}>
        <span>{project.files.length} file{project.files.length !== 1 ? 's' : ''}</span>
        {project.files.some((f) => f.isModified) && <span style={{ color: SUCCESS }}>● Modified</span>}
      </div>
    </div>
  );
}
