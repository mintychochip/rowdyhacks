import { useState, useEffect, useCallback } from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { getContentPages } from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';
import {
  PRIMARY, CYAN,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  CARD_BG, BORDER,
  TYPO, SPACE, RADIUS,
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
}

interface GroupedPages {
  [tabGroup: string]: ContentPage[];
}

export default function ResourcesPage() {
  const { isMobile } = useMediaQuery();
  const [pages, setPages] = useState<ContentPage[]>([]);
  const [groupedPages, setGroupedPages] = useState<GroupedPages>({});
  const [tabGroups, setTabGroups] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPages = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getContentPages();
      const publishedPages = (data.pages || []).filter((p: ContentPage) => p.is_published);
      setPages(publishedPages);

      const grouped: GroupedPages = {};
      publishedPages.forEach((page: ContentPage) => {
        const group = page.tab_group || 'General';
        if (!grouped[group]) {
          grouped[group] = [];
        }
        grouped[group].push(page);
      });

      Object.keys(grouped).forEach((group) => {
        grouped[group].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
      });

      const sortedGroups = Object.keys(grouped).sort((a, b) => {
        const aOrder = grouped[a][0]?.tab_group_order || 0;
        const bOrder = grouped[b][0]?.tab_group_order || 0;
        return aOrder - bOrder;
      });

      setGroupedPages(grouped);
      setTabGroups(sortedGroups);
      if (sortedGroups.length > 0 && !activeTab) {
        setActiveTab(sortedGroups[0]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load resources');
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    loadPages();
  }, [loadPages]);

  const currentPages = activeTab ? groupedPages[activeTab] || [] : [];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      <div style={{ textAlign: 'center', marginBottom: isMobile ? SPACE.xl : 56 }}>
        <div style={{
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, ' + PRIMARY + '20 0%, ' + CYAN + '20 100%)',
          border: '2px solid ' + PRIMARY + '40',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto',
          marginBottom: SPACE.lg,
          boxShadow: '0 8px 32px ' + PRIMARY + '30, 0 0 0 1px ' + PRIMARY + '20',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 40, color: PRIMARY }}>menu_book</span>
        </div>

        <h1 style={{
          ...TYPO.h1,
          fontSize: isMobile ? 28 : 36,
          marginBottom: SPACE.md,
          background: 'linear-gradient(135deg, ' + TEXT_PRIMARY + ' 0%, ' + CYAN + ' 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
        }}>
          Resources
        </h1>

        <p style={{
          color: TEXT_SECONDARY,
          fontSize: isMobile ? 15 : 17,
          maxWidth: 560,
          margin: '0 auto',
          lineHeight: 1.6,
        }}>
          Hacker resources, guides, and reference materials for the event.
        </p>
      </div>

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
          <p>Loading resources...</p>
        </div>
      )}

      {!loading && error && (
        <div style={{
          background: '#ff444420',
          border: '1px solid #ff444440',
          borderRadius: RADIUS.lg,
          padding: SPACE.lg,
          textAlign: 'center',
          color: '#ff6b6b',
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: SPACE.md }}>error_outline</span>
          <p>{error}</p>
          <button
            onClick={loadPages}
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

      {!loading && !error && pages.length === 0 && (
        <div style={{ textAlign: 'center', padding: SPACE.xl + ' ' + SPACE.md, color: TEXT_MUTED }}>
          <span className="material-symbols-outlined" style={{ fontSize: 64, marginBottom: SPACE.md, opacity: 0.5 }}>folder_open</span>
          <p style={{ fontSize: 16 }}>No resources available yet.</p>
          <p style={{ fontSize: 14, marginTop: SPACE.sm }}>Check back soon for guides and reference materials!</p>
        </div>
      )}

      {!loading && !error && pages.length > 0 && (
        <>
          {tabGroups.length > 1 && (
            <div style={{
              display: 'flex',
              gap: SPACE.sm,
              marginBottom: SPACE.lg,
              flexWrap: 'wrap',
              borderBottom: '1px solid ' + BORDER,
              paddingBottom: SPACE.md,
            }}>
              {tabGroups.map((group) => (
                <button
                  key={group}
                  onClick={() => setActiveTab(group)}
                  style={{
                    padding: SPACE.sm + 'px ' + SPACE.md + 'px',
                    background: activeTab === group ? PRIMARY + '20' : 'transparent',
                    border: '1px solid ' + (activeTab === group ? PRIMARY : BORDER),
                    borderRadius: RADIUS.md,
                    color: activeTab === group ? PRIMARY : TEXT_SECONDARY,
                    cursor: 'pointer',
                    fontWeight: activeTab === group ? 600 : 500,
                    fontSize: 14,
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: SPACE.sm,
                  }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                    {group === 'General' ? 'article' : 'folder'}
                  </span>
                  {group}
                  <span style={{
                    background: activeTab === group ? PRIMARY : BORDER,
                    color: activeTab === group ? TEXT_PRIMARY : TEXT_MUTED,
                    padding: '2px 8px',
                    borderRadius: RADIUS.full,
                    fontSize: 12,
                    fontWeight: 700,
                  }}>
                    {groupedPages[group]?.length || 0}
                  </span>
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.lg }}>
            {currentPages.map((page) => (
              <div
                key={page.id}
                style={{
                  background: CARD_BG,
                  border: '1px solid ' + BORDER,
                  borderRadius: RADIUS.lg,
                  padding: isMobile ? SPACE.lg : SPACE.lg + 'px ' + SPACE.xl + 'px',
                }}
              >
                <h2 style={{
                  ...TYPO.h2,
                  fontSize: isMobile ? 20 : 24,
                  marginBottom: SPACE.lg,
                  color: TEXT_PRIMARY,
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.sm,
                }}>
                  <span className="material-symbols-outlined" style={{ color: CYAN }}>description</span>
                  {page.title}
                </h2>

                <MarkdownRenderer content={page.content} />

                <div style={{
                  marginTop: SPACE.lg,
                  paddingTop: SPACE.md,
                  borderTop: '1px solid ' + BORDER,
                  fontSize: 12,
                  color: TEXT_MUTED,
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.sm,
                }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 14 }}>schedule</span>
                  Last updated: {new Date(page.updated_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
