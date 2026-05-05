import { useState } from 'react';
import { useBuilderStore } from '../../../stores/builderStore';
import FileExplorer from '../files/FileExplorer';
import CodeEditor from '../editor/CodeEditor';
import { CARD_BG, PRIMARY, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, BORDER_LIGHT } from '../../../theme';

function PreviewPanel() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: CARD_BG, borderLeft: '1px solid ' + BORDER_LIGHT }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: SPACE.sm + 'px ' + SPACE.md + 'px', borderBottom: '1px solid ' + BORDER_LIGHT }}>
        <span style={{ fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1, color: TEXT_MUTED }}>Preview</span>
        <div style={{ display: 'flex', gap: SPACE.xs }}>
          <button style={{ padding: SPACE.xs + 'px', borderRadius: RADIUS.sm, border: 'none', background: 'transparent', color: TEXT_MUTED, fontSize: 12, cursor: 'pointer' }}>🔄</button>
          <button style={{ padding: SPACE.xs + 'px', borderRadius: RADIUS.sm, border: 'none', background: 'transparent', color: TEXT_MUTED, fontSize: 12, cursor: 'pointer' }}>🔗</button>
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: SPACE.lg, gap: SPACE.md }}>
        <span style={{ fontSize: 48 }}>👁️</span>
        <div style={{ textAlign: 'center' }}>
          <div style={{ color: TEXT_PRIMARY, fontWeight: 500, marginBottom: SPACE.xs }}>Preview Panel</div>
          <div style={{ color: TEXT_MUTED, fontSize: 13 }}>Live preview will appear here</div>
        </div>
        <div style={{ padding: SPACE.sm + 'px ' + SPACE.md + 'px', background: 'rgba(37, 99, 235, 0.1)', borderRadius: RADIUS.md, border: '1px solid ' + PRIMARY + '40', fontSize: 12, color: PRIMARY }}>🚧 Coming soon in Chunk 5</div>
      </div>
    </div>
  );
}

export default function BuildMode() {
  const { project } = useBuilderStore();
  const [panelSizes, setPanelSizes] = useState({ filePanel: 240, preview: 280 });
  const [isResizing, setIsResizing] = useState<string | null>(null);

  const handleResizeStart = (panel: string) => setIsResizing(panel);
  const handleResizeEnd = () => setIsResizing(null);
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isResizing) return;
    if (isResizing === 'fileEditor') {
      const newSize = Math.max(180, Math.min(400, e.clientX - 16));
      setPanelSizes((prev) => ({ ...prev, filePanel: newSize }));
    }
  };

  if (!project) {
    return <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: SPACE.lg, gap: SPACE.md }}><span style={{ fontSize: 64 }}>🔨</span><div style={{ textAlign: 'center' }}><div style={{ color: TEXT_PRIMARY, fontSize: 20, fontWeight: 600, marginBottom: SPACE.sm }}>Build Mode</div><div style={{ color: TEXT_SECONDARY, fontSize: 14 }}>Create a project to start building</div></div></div>;
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }} onMouseMove={handleMouseMove} onMouseUp={handleResizeEnd} onMouseLeave={handleResizeEnd}>
      <div style={{ width: panelSizes.filePanel, minWidth: 180, maxWidth: 400, flexShrink: 0, height: '100%', overflow: 'hidden' }}><FileExplorer /></div>
      <div onMouseDown={() => handleResizeStart('fileEditor')} style={{ width: 4, cursor: 'col-resize', background: isResizing === 'fileEditor' ? PRIMARY : 'transparent', transition: 'background 0.15s ease', flexShrink: 0 }} onMouseEnter={(e) => { if (!isResizing) e.currentTarget.style.background = BORDER_LIGHT; }} onMouseLeave={(e) => { if (!isResizing) e.currentTarget.style.background = 'transparent'; }} />
      <div style={{ flex: 1, minWidth: 300, height: '100%', overflow: 'hidden' }}><CodeEditor height="100%" /></div>
      <div onMouseDown={() => handleResizeStart('editorPreview')} style={{ width: 4, cursor: 'col-resize', background: isResizing === 'editorPreview' ? PRIMARY : 'transparent', transition: 'background 0.15s ease', flexShrink: 0 }} onMouseEnter={(e) => { if (!isResizing) e.currentTarget.style.background = BORDER_LIGHT; }} onMouseLeave={(e) => { if (!isResizing) e.currentTarget.style.background = 'transparent'; }} />
      <div style={{ width: panelSizes.preview, minWidth: 200, maxWidth: 500, flexShrink: 0, height: '100%', overflow: 'hidden' }}><PreviewPanel /></div>
    </div>
  );
}
