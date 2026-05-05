// ============================================================
// Preview Panel - Live preview for web projects using iframe
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';
import { useBuilderStore } from '../../../stores/builderStore';
import type { ProjectFile } from '../../../types/builder';
import {
  CARD_BG,
  INPUT_BG,
  PRIMARY,
  RADIUS,
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER_LIGHT,
  ERROR,
} from '../../../theme';

// Web project types that can be previewed
const WEB_PREVIEWABLE_TYPES = ['web-app', 'landing-page', 'component'];

// Check if a project can be previewed
const canPreviewProject = (projectType: string): boolean => {
  return WEB_PREVIEWABLE_TYPES.includes(projectType);
};

// Build complete HTML document from project files
const buildPreviewDocument = (files: ProjectFile[]): string | null => {
  // Find HTML entry point
  const htmlFile = files.find(
    (f) => f.path.toLowerCase().endsWith('index.html') || f.path.toLowerCase().endsWith('.html')
  );

  if (!htmlFile) return null;

  let htmlContent = htmlFile.content;

  // Find all CSS files
  const cssFiles = files.filter((f) => f.path.toLowerCase().endsWith('.css'));

  // Find all JS files
  const jsFiles = files.filter((f) =>
    f.path.toLowerCase().endsWith('.js') || f.path.toLowerCase().endsWith('.jsx')
  );

  // Inject CSS files into head
  if (cssFiles.length > 0) {
    const styleTags = cssFiles
      .map(
        (css) => `<style data-file="${css.path}">
/* ${css.path} */
${css.content}
</style>`
      )
      .join('\n');

    if (htmlContent.includes('</head>')) {
      htmlContent = htmlContent.replace('</head>', `${styleTags}\n</head>`);
    } else if (htmlContent.includes('<body')) {
      htmlContent = htmlContent.replace(/<body/, `${styleTags}\n<body`);
    } else {
      htmlContent = `<head>${styleTags}</head>\n${htmlContent}`;
    }
  }

  // Inject JS files at end of body
  if (jsFiles.length > 0) {
    const scriptTags = jsFiles
      .map(
        (js) => `<script data-file="${js.path}">
// ${js.path}
${js.content}
</script>`
      )
      .join('\n');

    if (htmlContent.includes('</body>')) {
      htmlContent = htmlContent.replace('</body>', `${scriptTags}\n</body>`);
    } else {
      htmlContent += `\n${scriptTags}`;
    }
  }

  return htmlContent;
};

// Get non-web project message
const getNonWebProjectMessage = (projectType: string): { icon: string; title: string; description: string } => {
  switch (projectType) {
    case 'api':
      return {
        icon: '🔌',
        title: 'API Project',
        description: 'API projects cannot be previewed in-browser. Export to test locally.',
      };
    case 'script':
      return {
        icon: '📜',
        title: 'Script Project',
        description: 'Script projects run in a terminal. Export to execute locally.',
      };
    case 'mobile-app':
      return {
        icon: '📱',
        title: 'Mobile App',
        description: 'Mobile apps require a simulator or device. Export to build locally.',
      };
    default:
      return {
        icon: '🔧',
        title: 'Non-Web Project',
        description: 'This project type cannot be previewed in the browser. Export to run locally.',
      };
  }
};

export default function PreviewPanel() {
  const { project } = useBuilderStore();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [key, setKey] = useState(0); // Used to force iframe refresh

  // Generate preview blob URL
  const generatePreview = useCallback(() => {
    if (!project || !canPreviewProject(project.projectType)) {
      setBlobUrl(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const htmlContent = buildPreviewDocument(project.files);

      if (!htmlContent) {
        setError('No HTML file found. Add an index.html file to preview.');
        setBlobUrl(null);
        setIsLoading(false);
        return;
      }

      // Revoke old blob URL to prevent memory leaks
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }

      const blob = new Blob([htmlContent], { type: 'text/html' });
      const newUrl = URL.createObjectURL(blob);
      setBlobUrl(newUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate preview');
    } finally {
      setIsLoading(false);
    }
  }, [project, blobUrl]);

  // Initial preview generation
  useEffect(() => {
    generatePreview();
  }, [project?.id, project?.projectType]);

  // Regenerate when files change
  useEffect(() => {
    if (!project) return;

    const hasModifiedFiles = project.files.some((f) => f.isModified);
    if (hasModifiedFiles) {
      // Debounce regeneration
      const timeout = setTimeout(() => {
        generatePreview();
      }, 500);
      return () => clearTimeout(timeout);
    }
  }, [project?.files, generatePreview]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [blobUrl]);

  // Refresh preview
  const handleRefresh = () => {
    setKey((prev) => prev + 1); // Force iframe re-render
    generatePreview();
  };

  // Open preview in new tab
  const handleOpenNewTab = () => {
    if (blobUrl) {
      window.open(blobUrl, '_blank');
    }
  };

  if (!project) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          background: CARD_BG,
          borderLeft: `1px solid ${BORDER_LIGHT}`,
        }}
      >
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: SPACE.lg,
            gap: SPACE.md,
          }}
        >
          <span style={{ fontSize: 48 }}>👁️</span>
          <span style={{ color: TEXT_MUTED, fontSize: 14 }}>No project loaded</span>
        </div>
      </div>
    );
  }

  // Non-web projects show message
  if (!canPreviewProject(project.projectType)) {
    const { icon, title, description } = getNonWebProjectMessage(project.projectType);

    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          background: CARD_BG,
          borderLeft: `1px solid ${BORDER_LIGHT}`,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: `${SPACE.sm}px ${SPACE.md}px`,
            borderBottom: `1px solid ${BORDER_LIGHT}`,
          }}
        >
          <span
            style={{
              fontSize: 12,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: 1,
              color: TEXT_MUTED,
            }}
          >
            Preview
          </span>
        </div>

        {/* Non-web project message */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: SPACE.lg,
            gap: SPACE.md,
            textAlign: 'center',
          }}
        >
          <span style={{ fontSize: 64 }}>{icon}</span>
          <div>
            <div
              style={{
                color: TEXT_PRIMARY,
                fontWeight: 600,
                fontSize: 18,
                marginBottom: SPACE.sm,
              }}
            >
              {title}
            </div>
            <div style={{ color: TEXT_SECONDARY, fontSize: 14, maxWidth: 280 }}>
              {description}
            </div>
          </div>
          <div
            style={{
              padding: `${SPACE.sm}px ${SPACE.md}px`,
              background: INPUT_BG,
              borderRadius: RADIUS.md,
              fontSize: 12,
              color: TEXT_MUTED,
            }}
          >
            Project type: <strong>{project.projectType}</strong>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: CARD_BG,
        borderLeft: `1px solid ${BORDER_LIGHT}`,
        width: 400,
        minWidth: 200,
        maxWidth: 600,
      }}
    >
      {/* Preview header with controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: `${SPACE.sm}px ${SPACE.md}px`,
          borderBottom: `1px solid ${BORDER_LIGHT}`,
        }}
      >
        <span
          style={{
            fontSize: 12,
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: 1,
            color: TEXT_MUTED,
          }}
        >
          Live Preview
        </span>
        <div style={{ display: 'flex', gap: SPACE.xs }}>
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            title="Refresh preview"
            style={{
              padding: `${SPACE.xs}px`,
              borderRadius: RADIUS.sm,
              border: 'none',
              background: 'transparent',
              color: TEXT_MUTED,
              fontSize: 14,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.5 : 1,
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (!isLoading) {
                e.currentTarget.style.background = INPUT_BG;
                e.currentTarget.style.color = TEXT_PRIMARY;
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = TEXT_MUTED;
            }}
          >
            🔄
          </button>
          <button
            onClick={handleOpenNewTab}
            disabled={!blobUrl || isLoading}
            title="Open in new tab"
            style={{
              padding: `${SPACE.xs}px`,
              borderRadius: RADIUS.sm,
              border: 'none',
              background: 'transparent',
              color: TEXT_MUTED,
              fontSize: 14,
              cursor: !blobUrl || isLoading ? 'not-allowed' : 'pointer',
              opacity: !blobUrl || isLoading ? 0.5 : 1,
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (blobUrl && !isLoading) {
                e.currentTarget.style.background = INPUT_BG;
                e.currentTarget.style.color = TEXT_PRIMARY;
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = TEXT_MUTED;
            }}
          >
            🔗
          </button>
        </div>
      </div>

      {/* Preview content */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          overflow: 'hidden',
          background: '#ffffff',
        }}
      >
        {isLoading && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: CARD_BG,
              zIndex: 1,
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  border: `3px solid ${BORDER_LIGHT}`,
                  borderTopColor: PRIMARY,
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite',
                  margin: '0 auto',
                }}
              />
              <style>{`
                @keyframes spin {
                  to { transform: rotate(360deg); }
                }
              `}</style>
              <span
                style={{
                  display: 'block',
                  marginTop: SPACE.md,
                  color: TEXT_MUTED,
                  fontSize: 13,
                }}
              >
                Building preview...
              </span>
            </div>
          </div>
        )}

        {error && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: SPACE.lg,
              gap: SPACE.md,
              background: CARD_BG,
            }}
          >
            <span style={{ fontSize: 48 }}>⚠️</span>
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  color: ERROR,
                  fontWeight: 500,
                  fontSize: 14,
                  marginBottom: SPACE.xs,
                }}
              >
                Preview Error
              </div>
              <div style={{ color: TEXT_SECONDARY, fontSize: 13 }}>{error}</div>
            </div>
            <button
              onClick={handleRefresh}
              style={{
                padding: `${SPACE.sm}px ${SPACE.md}px`,
                background: PRIMARY,
                color: '#fff',
                border: 'none',
                borderRadius: RADIUS.md,
                fontSize: 13,
                cursor: 'pointer',
                fontWeight: 500,
              }}
            >
              Try Again
            </button>
          </div>
        )}

        {blobUrl && !error && (
          <iframe
            key={key}
            ref={iframeRef}
            src={blobUrl}
            title="Preview"
            sandbox="allow-scripts allow-same-origin"
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              background: '#ffffff',
            }}
          />
        )}

        {!blobUrl && !error && !isLoading && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: SPACE.lg,
              gap: SPACE.md,
            }}
          >
            <span style={{ fontSize: 48 }}>🌐</span>
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  color: TEXT_PRIMARY,
                  fontWeight: 500,
                  fontSize: 14,
                  marginBottom: SPACE.xs,
                }}
              >
                No Preview Available
              </div>
              <div style={{ color: TEXT_SECONDARY, fontSize: 13 }}>
                Add an HTML file to see a live preview
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer with info */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: `${SPACE.xs}px ${SPACE.md}px`,
          borderTop: `1px solid ${BORDER_LIGHT}`,
          fontSize: 11,
          color: TEXT_MUTED,
          background: INPUT_BG,
        }}
      >
        <span>{project.files.length} files</span>
        <span>{project.projectType}</span>
      </div>
    </div>
  );
}
