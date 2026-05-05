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

