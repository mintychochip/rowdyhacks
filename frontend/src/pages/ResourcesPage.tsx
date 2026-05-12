import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { getContentPages } from '../services/api';
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
}

interface GroupedPages {
  [tabGroup: string]: ContentPage[];
}

// Extract preview text from markdown content (first ~150 chars)
function getPreview(content: string, maxLength = 150): string {
  // Remove markdown syntax for preview
  const plainText = content
    .replace(/#+ /g, '') // Remove headers
    .replace(/\*\*/g, '') // Remove bold
    .replace(/\*/g, '') // Remove italic
    .replace(/`/g, '') // Remove inline code
    .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // Replace links with just text
    .replace(/\n/g, ' ') // Replace newlines with spaces
    .trim();

  if (plainText.length <= maxLength) return plainText;
  return plainText.substring(0, maxLength).trim() + '...';
}

// Calculate read time in minutes
function getReadTime(content: string): number {
  const wordsPerMinute = 200;
  const wordCount = content.trim().split(/\s+/).length;
  return Math.max(1, Math.ceil(wordCount / wordsPerMinute));
}

// Get category/tag from content based on keywords
function getCategory(title: string, content: string): string {
  const text = (title + ' ' + content).toLowerCase();
  if (text.includes('api') || text.includes('endpoint')) return 'API';
  if (text.includes('hardware') || text.includes('arduino') || text.includes('sensor')) return 'Hardware';
  if (text.includes('git') || text.includes('github') || text.includes('deploy')) return 'DevOps';
  if (text.includes('design') || text.includes('ui') || text.includes('figma')) return 'Design';
  if (text.includes('python') || text.includes('javascript') || text.includes('code')) return 'Code';
  return 'Guide';
}

// Icon for category
function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    'API': 'api',
    'Hardware': 'memory',
    'DevOps': 'terminal',
    'Design': 'palette',
    'Code': 'code',
    'Guide': 'book',
  };
  return icons[category] || 'article';
}

export default function ResourcesPage() {
  const { isMobile } = useMediaQuery();
  const navigate = useNavigate();
  const [pages, setPages] = useState<ContentPage[]>([]);
  const [groupedPages, setGroupedPages] = useState<GroupedPages>({});
  const [tabGroups, setTabGroups] = useState<string[]>([]);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
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
      // Expand first group by default
      if (sortedGroups.length > 0 && expandedGroups.size === 0) {
        setExpandedGroups(new Set([sortedGroups[0]]));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load resources');
    } finally {
      setLoading(false);
    }
  }, [expandedGroups.size]);

  useEffect(() => {
    loadPages();
  }, [loadPages]);

  const toggleGroup = (group: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(group)) {
        next.delete(group);
      } else {
        next.add(group);
      }
      return next;
    });
  };

  const expandAll = () => setExpandedGroups(new Set(tabGroups));
  const collapseAll = () => {
    setExpandedGroups(new Set());
  };

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
          {/* Expand/Collapse All Controls */}
          <div style={{
            display: 'flex',
            gap: SPACE.sm,
            marginBottom: SPACE.lg,
            justifyContent: 'flex-end',
          }}>
            <button
              onClick={expandAll}
              style={{
                padding: `${SPACE.xs}px ${SPACE.md}px`,
                background: 'transparent',
                border: '1px solid ' + BORDER,
                borderRadius: RADIUS.md,
                color: TEXT_SECONDARY,
                cursor: 'pointer',
                fontSize: 13,
                display: 'flex',
                alignItems: 'center',
                gap: SPACE.xs,
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>unfold_more</span>
              Expand All
            </button>
            <button
              onClick={collapseAll}
              style={{
                padding: `${SPACE.xs}px ${SPACE.md}px`,
                background: 'transparent',
                border: '1px solid ' + BORDER,
                borderRadius: RADIUS.md,
                color: TEXT_SECONDARY,
                cursor: 'pointer',
                fontSize: 13,
                display: 'flex',
                alignItems: 'center',
                gap: SPACE.xs,
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>unfold_less</span>
              Collapse All
            </button>
          </div>

          {/* Collapsible Groups */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.lg }}>
            {tabGroups.map((group) => {
              const isExpanded = expandedGroups.has(group);
              const groupPages = groupedPages[group] || [];
              const groupId = group.toLowerCase().replace(/\s+/g, '-');

              return (
                <div
                  key={group}
                  id={groupId}
                  style={{
                    background: CARD_BG,
                    border: '1px solid ' + BORDER,
                    borderRadius: RADIUS.lg,
                    overflow: 'hidden',
                    scrollMarginTop: '80px',
                  }}
                >
                  {/* Group Header - Click to expand/collapse */}
                  <button
                    onClick={() => toggleGroup(group)}
                    style={{
                      width: '100%',
                      padding: isMobile ? `${SPACE.lg}px ${SPACE.md}px` : `${SPACE.lg}px ${SPACE.xl}px`,
                      background: isExpanded ? PRIMARY + '10' : 'transparent',
                      border: 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      textAlign: 'left',
                      transition: 'background 0.2s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.md }}>
                      <span
                        className="material-symbols-outlined"
                        style={{
                          fontSize: 24,
                          color: isExpanded ? PRIMARY : TEXT_MUTED,
                          transition: 'transform 0.2s ease',
                          transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                        }}
                      >
                        chevron_right
                      </span>
                      <div>
                        <h2 style={{
                          ...TYPO.h3,
                          fontSize: isMobile ? 18 : 20,
                          color: TEXT_PRIMARY,
                          margin: 0,
                        }}>
                          {group}
                        </h2>
                        <span style={{ color: TEXT_MUTED, fontSize: 13 }}>
                          {groupPages.length} resource{groupPages.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>
                    <span style={{
                      background: isExpanded ? PRIMARY + '20' : BORDER,
                      color: isExpanded ? PRIMARY : TEXT_MUTED,
                      padding: '4px 12px',
                      borderRadius: RADIUS.full,
                      fontSize: 13,
                      fontWeight: 600,
                    }}>
                      {groupPages.length}
                    </span>
                  </button>

                  {/* Expandable Content */}
                  {isExpanded && (
                    <div style={{
                      borderTop: '1px solid ' + BORDER,
                      padding: isMobile ? SPACE.md : SPACE.lg + 'px ' + SPACE.xl + 'px',
                    }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.md }}>
                        {groupPages.map((page) => {
                          const preview = getPreview(page.content);
                          const readTime = getReadTime(page.content);
                          const category = getCategory(page.title, page.content);
                          const categoryIcon = getCategoryIcon(category);

                          return (
                            <div
                              key={page.id}
                              onClick={() => navigate('/resources/' + page.slug)}
                              style={{
                                background: 'transparent',
                                border: '1px solid ' + BORDER,
                                borderRadius: RADIUS.md,
                                overflow: 'hidden',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                              }}
                            >
                              <div style={{
                                padding: isMobile ? `${SPACE.md}px` : `${SPACE.lg}px`,
                                display: 'flex',
                                gap: SPACE.md,
                                alignItems: 'flex-start',
                              }}>
                                {/* Category Icon */}
                                <div style={{
                                  width: 44,
                                  height: 44,
                                  borderRadius: RADIUS.md,
                                  background: PRIMARY + '15',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  flexShrink: 0,
                                }}>
                                  <span className="material-symbols-outlined" style={{ color: PRIMARY, fontSize: 22 }}>
                                    {categoryIcon}
                                  </span>
                                </div>

                                {/* Title and Preview */}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                  <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: SPACE.sm,
                                    marginBottom: SPACE.xs,
                                    flexWrap: 'wrap',
                                  }}>
                                    <h3 style={{
                                      ...TYPO.h3,
                                      fontSize: isMobile ? 16 : 17,
                                      color: TEXT_PRIMARY,
                                      margin: 0,
                                      fontWeight: 600,
                                    }}>
                                      {page.title}
                                    </h3>
                                    <span style={{
                                      background: PRIMARY + '15',
                                      color: PRIMARY,
                                      padding: '2px 8px',
                                      borderRadius: RADIUS.sm,
                                      fontSize: 11,
                                      fontWeight: 600,
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.05em',
                                    }}>
                                      {category}
                                    </span>
                                  </div>

                                  {/* Preview text (truncated) */}
                                  <p style={{
                                    color: TEXT_SECONDARY,
                                    fontSize: 14,
                                    lineHeight: 1.5,
                                    margin: `0 0 ${SPACE.sm}px 0`,
                                  }}>
                                    {preview}
                                  </p>

                                  {/* Meta info */}
                                  <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: SPACE.md,
                                    color: TEXT_MUTED,
                                    fontSize: 12,
                                  }}>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                      <span className="material-symbols-outlined" style={{ fontSize: 14 }}>schedule</span>
                                      {readTime} min read
                                    </span>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                      <span className="material-symbols-outlined" style={{ fontSize: 14 }}>update</span>
                                      {new Date(page.updated_at).toLocaleDateString()}
                                    </span>
                                  </div>
                                </div>

                                {/* Open icon */}
                                <span
                                  className="material-symbols-outlined"
                                  style={{
                                    fontSize: 20,
                                    color: TEXT_MUTED,
                                    flexShrink: 0,
                                  }}
                                >
                                  open_in_new
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
