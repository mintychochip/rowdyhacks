// ============================================================
// Build Mode - 3-column layout: FileExplorer | CodeEditor | PreviewPanel
// ============================================================

import { useState } from 'react';
import { useBuilderStore } from '../../../stores/builderStore';
import FileExplorer from '../files/FileExplorer';
import CodeEditor from '../editor/CodeEditor';
import PreviewPanel from '../preview/PreviewPanel';
import ExportButton from '../export/ExportButton';
import {
  CARD_BG,
  PRIMARY,
  RADIUS,
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER_LIGHT,
} from '../../../theme';

export default function BuildMode() {
  const { project, currentFileId } = useBuilderStore();
  const [panelSizes, setPanelSizes] = useState({
    filePanel: 240,
    editor: 500,
    preview: 400,
  });
  const [isResizing, setIsResizing] = useState<string | null>(null);

  // Handle resize start
  const handleResizeStart = (panel: string) => {
    setIsResizing(panel);
  };

  // Handle resize end
  const handleResizeEnd = () => {
    setIsResizing(null);
  };

  // Handle mouse move for resizing
  const handleMouseMove = (e: React.MouseEvent, direction: 'horizontal') => {
    if (!isResizing) return;

    if (isResizing === 'fileEditor' && direction === 'horizontal') {
      const newSize = Math.max(180, Math.min(400, e.clientX - 16));
      setPanelSizes((prev) => ({ ...prev, filePanel: newSize }));
    } else if (isResizing === 'editorPreview' && direction === 'horizontal') {
      // This would need the container ref to calculate properly
      // For now, simplified behavior
    }
  };

  if (!project) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          padding: SPACE.lg,
          gap: SPACE.md,
        }}
      >
        <span style={{ fontSize: 64 }}>🔨</span>
        <div style={{ textAlign: 'center' }}>
          <div
            style={{ color: TEXT_PRIMARY, fontSize: 20, fontWeight: 600, marginBottom: SPACE.sm }}
          >
            Build Mode
          </div>
          <div style={{ color: TEXT_SECONDARY, fontSize: 14 }}>
            Create a project to start building
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        height: '100%',
        overflow: 'hidden',
      }}
      onMouseMove={(e) => handleMouseMove(e, 'horizontal')}
      onMouseUp={handleResizeEnd}
      onMouseLeave={handleResizeEnd}
    >
      {/* File Explorer Panel */}
      <div
        style={{
          width: panelSizes.filePanel,
          minWidth: 180,
          maxWidth: 400,
          flexShrink: 0,
          height: '100%',
          overflow: 'hidden',
        }}
      >
        <FileExplorer />
      </div>

      {/* Resizer between FileExplorer and Editor */}
      <div
        onMouseDown={() => handleResizeStart('fileEditor')}
        style={{
          width: 4,
          cursor: 'col-resize',
          background: isResizing === 'fileEditor' ? PRIMARY : 'transparent',
          transition: 'background 0.15s ease',
          flexShrink: 0,
        }}
        onMouseEnter={(e) => {
          if (!isResizing) e.currentTarget.style.background = BORDER_LIGHT;
        }}
        onMouseLeave={(e) => {
          if (!isResizing) e.currentTarget.style.background = 'transparent';
        }}
      />

      {/* Code Editor Panel */}
      <div
        style={{
          flex: 1,
          minWidth: 300,
          height: '100%',
          overflow: 'hidden',
        }}
      >
        <CodeEditor height="100%" />
      </div>

      {/* Resizer between Editor and Preview */}
      <div
        onMouseDown={() => handleResizeStart('editorPreview')}
        style={{
          width: 4,
          cursor: 'col-resize',
          background: isResizing === 'editorPreview' ? PRIMARY : 'transparent',
          transition: 'background 0.15s ease',
          flexShrink: 0,
        }}
        onMouseEnter={(e) => {
          if (!isResizing) e.currentTarget.style.background = BORDER_LIGHT;
        }}
        onMouseLeave={(e) => {
          if (!isResizing) e.currentTarget.style.background = 'transparent';
        }}
      />

      {/* Preview Panel */}
      <div
        style={{
          width: panelSizes.preview,
          minWidth: 200,
          maxWidth: 600,
          flexShrink: 0,
          height: '100%',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Project Header with Export */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: `${SPACE.sm}px ${SPACE.md}px`,
            background: CARD_BG,
            borderBottom: `1px solid ${BORDER_LIGHT}`,
            borderLeft: `1px solid ${BORDER_LIGHT}`,
            gap: SPACE.md,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: TEXT_PRIMARY,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
              title={project.name}
            >
              {project.name}
            </div>
            <div style={{ fontSize: 11, color: TEXT_MUTED, textTransform: 'capitalize' }}>
              {project.projectType.replace('-', ' ')}
            </div>
          </div>
          <ExportButton variant="primary" size="small" />
        </div>
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <PreviewPanel />
        </div>
      </div>
    </div>
  );
}
