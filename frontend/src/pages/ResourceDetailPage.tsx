import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { getContentPage } from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';
import {
  PRIMARY, CYAN,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  CARD_BG, BORDER,
  TYPO, SPACE, RADIUS,
  ERROR, ERROR_BG10, ERROR_BORDER30,
} from '../theme';

interface ContentPage {
  id: string;
  title: string;
  slug: string;
  content: string;
  tab_group: string | null;
  tab_group_order: number;
  sort_order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
  author_name?: string;
}

export default function ResourceDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { isMobile } = useMediaQuery();
  const [page, setPage] = useState<ContentPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) {
      setError('No page slug provided');
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getContentPage(slug)
      .then((data) => {
        if (!cancelled) {
          setPage(data);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load page');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [slug]);

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      {/* Back link */}
      <button
        onClick={() => navigate('/resources')}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: SPACE.sm,
          padding: '8px 12px',
          background: 'transparent',
          border: '1px solid ' + BORDER,
          borderRadius: RADIUS.md,
          color: TEXT_SECONDARY,
          cursor: 'pointer',
          fontSize: 14,
          fontWeight: 500,
          marginBottom: SPACE.lg,
          transition: 'all 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = CARD_BG;
          e.currentTarget.style.color = TEXT_PRIMARY;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = TEXT_SECONDARY;
        }}
      >
        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>arrow_back</span>
        Back to Resources
      </button>

      {loading && (
        <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
          <div style={{
            width: 40,
            height: 40,
            border: '3px solid ' + BORDER,
            borderTop: '3px solid ' + PRIMARY,
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto',
            marginBottom: SPACE.md,
          }} />
          <style>{"@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }"}</style>
          <p>Loading page...</p>
        </div>
      )}

      {!loading && error && (
        <div style={{
          background: ERROR_BG10,
          border: `1px solid ${ERROR_BORDER30}`,
          borderRadius: RADIUS.lg,
          padding: SPACE.lg,
          textAlign: 'center',
          color: ERROR,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: SPACE.md }}>error_outline</span>
          <p>{error}</p>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: SPACE.md,
              padding: '10px 20px',
              background: PRIMARY,
              border: 'none',
              borderRadius: RADIUS.md,
              color: TEXT_PRIMARY,
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Try Again
          </button>
        </div>
      )}

      {!loading && !error && page && (
        <>
          {/* Page header */}
          <div style={{ marginBottom: isMobile ? SPACE.lg : SPACE.xl }}>
            {page.tab_group && (
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: SPACE.xs,
                padding: '4px 12px',
                background: PRIMARY + '15',
                borderRadius: RADIUS.full,
                color: PRIMARY,
                fontSize: 12,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: SPACE.md,
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>folder</span>
                {page.tab_group}
              </div>
            )}

            <h1 style={{
              ...TYPO.h1,
              fontSize: isMobile ? 26 : 32,
              marginBottom: SPACE.md,
              background: 'linear-gradient(135deg, ' + TEXT_PRIMARY + ' 0%, ' + CYAN + ' 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              {page.title}
            </h1>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: SPACE.md,
              color: TEXT_MUTED,
              fontSize: 13,
              flexWrap: 'wrap',
            }}>
              {page.author_name && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 14 }}>person</span>
                  {page.author_name}
                </span>
              )}
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>update</span>
                {new Date(page.updated_at).toLocaleDateString(undefined, {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </span>
            </div>
          </div>

          {/* Content */}
          <div style={{
            background: CARD_BG,
            border: '1px solid ' + BORDER,
            borderRadius: RADIUS.lg,
            padding: isMobile ? SPACE.lg : SPACE.xl,
          }}>
            <MarkdownRenderer content={page.content} />
          </div>
        </>
      )}
    </div>
  );
}
