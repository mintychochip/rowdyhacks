# Editable Markdown Resources Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable organizers to edit markdown content for track resources and create a global resources page with tabbed sections.

**Architecture:** Add ContentPage model for global pages, extend Track with resources_markdown, create CRUD API with organizer-only writes, build markdown renderer component and editor UI.

**Tech Stack:** FastAPI/SQLAlchemy backend, React/TypeScript frontend, markdown + bleach for rendering, react-markdown + react-syntax-highlighter for frontend.

---

## File Structure Overview

### Backend Files
- `backend/app/models.py` - Add ContentPage model, extend Track model
- `backend/app/routes/content.py` - New CRUD endpoints for content pages
- `backend/app/routes/tracks.py` - Update PUT to handle resources_markdown
- `backend/app/alembic/versions/` - Database migrations

### Frontend Files
- `frontend/src/components/MarkdownRenderer.tsx` - Reusable markdown display
- `frontend/src/pages/ResourcesPage.tsx` - Tabbed resources page
- `frontend/src/pages/ContentEditorPage.tsx` - Organizer editor
- `frontend/src/pages/TracksPage.tsx` - Update TrackCard for resources sub-tab
- `frontend/src/services/api.ts` - Add content API functions
- `frontend/src/App.tsx` - Add routes

---

## Chunk 1: Backend Database Models

### Task 1: Add ContentPage Model and Track Extension

**Files:**
- Modify: `backend/app/models.py`

**Context:**
Existing models use SQLAlchemy with custom `Guid`, `JsonType`, `DateTime` types. Follow the pattern of `Track` model for reference.

- [ ] **Step 1: Add ContentPage model before the assistant imports at end**

Add this before the assistant import line at the bottom of models.py:

```python
class ContentPage(Base):
    """Organizer-editable markdown content pages."""

    __tablename__ = "content_pages"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    tab_group = Column(String(50), nullable=False, default="resources")
    sort_order = Column(Integer, default=0, nullable=False)
    tab_group_order = Column(Integer, default=0, nullable=False)
    is_published = Column(Boolean, default=True, nullable=False)
    created_by = Column(Guid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC), nullable=True)

    __table_args__ = (
        Index("ix_content_pages_slug", "slug"),
        Index("ix_content_pages_tab_group", "tab_group", "sort_order"),
        Index("ix_content_pages_published", "is_published"),
    )
```

- [ ] **Step 2: Add resources_markdown to Track model**

Find the `Track` class and add after the `resources = Column(JsonType, nullable=True)` line:

```python
    resources_markdown = Column(Text, nullable=True)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add ContentPage model and Track.resources_markdown column"
```

---

## Chunk 2: Backend API Routes - Content Pages

### Task 2: Create Content Routes File

**Files:**
- Create: `backend/app/routes/content.py`
- Modify: `backend/app/routes/__init__.py`
- Modify: `backend/app/main.py`

**Context:** Follow the pattern in `tracks.py` for organizer auth and caching.

- [ ] **Step 1: Write content.py routes**

Create `backend/app/routes/content.py`:

```python
"""Content page management routes for organizer-editable markdown pages."""

import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi_limiter.depends import RateLimiter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.cache import cache_delete_pattern, cached
from app.database import get_db
from app.models import ContentPage, User, UserRole

router = APIRouter(prefix="/api/content", tags=["content"])

CONTENT_CACHE_TTL = 300  # 5 minutes
CACHE_PFX = "content"


def _slugify(title: str) -> str:
    """Convert title to URL-friendly slug."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")[:100]


def _get_current_user_payload(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    try:
        return decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def _require_organizer(db: AsyncSession, authorization: str | None) -> User:
    """Verify user is an organizer."""
    payload = _get_current_user_payload(authorization)
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role != UserRole.organizer:
        raise HTTPException(status_code=403, detail="Only organizers can manage content")
    return user


def _page_to_response(page: ContentPage) -> dict:
    return {
        "id": str(page.id),
        "slug": page.slug,
        "title": page.title,
        "content": page.content,
        "tab_group": page.tab_group,
        "sort_order": page.sort_order,
        "tab_group_order": page.tab_group_order,
        "is_published": page.is_published,
        "created_by": str(page.created_by),
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }


@router.get("/pages")
@cached(ttl_seconds=CONTENT_CACHE_TTL, key_prefix=CACHE_PFX)
async def list_pages(
    tab_group: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List content pages, optionally filtered by tab_group."""
    query = select(ContentPage).where(ContentPage.is_published == True)
    if tab_group:
        query = query.where(ContentPage.tab_group == tab_group)
    query = query.order_by(ContentPage.tab_group_order, ContentPage.sort_order)
    result = await db.execute(query)
    pages = result.scalars().all()
    return {
        "pages": [_page_to_response(p) for p in pages],
        "tab_groups": list(set(p.tab_group for p in pages)),
    }


@router.get("/pages/{slug}")
@cached(ttl_seconds=CONTENT_CACHE_TTL, key_prefix=CACHE_PFX)
async def get_page(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a single content page by slug."""
    result = await db.execute(
        select(ContentPage).where(ContentPage.slug == slug, ContentPage.is_published == True)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return _page_to_response(page)


@router.post(
    "/pages",
    status_code=201,
    dependencies=[Depends(RateLimiter(times=30, seconds=60))],
)
async def create_page(
    request: Request,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new content page (organizer only)."""
    user = await _require_organizer(db, authorization)

    # Validate slug or generate from title
    title = body.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title is required")

    slug = body.get("slug", "").strip()
    if not slug:
        slug = _slugify(title)
    if not re.match(r"^[a-z0-9-]+$", slug):
        raise HTTPException(status_code=422, detail="Slug must be lowercase alphanumeric with hyphens only")

    # Check for slug conflict
    existing = await db.execute(select(ContentPage).where(ContentPage.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Page with slug '{slug}' already exists")

    page = ContentPage(
        slug=slug,
        title=title,
        content=body.get("content", ""),
        tab_group=body.get("tab_group", "resources"),
        sort_order=body.get("sort_order", 0),
        tab_group_order=body.get("tab_group_order", 0),
        is_published=body.get("is_published", True),
        created_by=user.id,
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)

    await _bust_content_cache()
    return _page_to_response(page)


@router.put(
    "/pages/{slug}",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))],
)
async def update_page(
    request: Request,
    slug: str,
    body: dict,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Update a content page (organizer only)."""
    await _require_organizer(db, authorization)

    result = await db.execute(select(ContentPage).where(ContentPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Update fields
    if "title" in body:
        page.title = body["title"].strip()
    if "content" in body:
        page.content = body["content"]
    if "tab_group" in body:
        page.tab_group = body["tab_group"]
    if "sort_order" in body:
        page.sort_order = body["sort_order"]
    if "tab_group_order" in body:
        page.tab_group_order = body["tab_group_order"]
    if "is_published" in body:
        page.is_published = body["is_published"]

    page.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(page)

    # Invalidate caches
    await _bust_content_cache()
    await cache_delete_pattern(f"{CACHE_PFX}:get_page:{slug}")

    return _page_to_response(page)


@router.delete(
    "/pages/{slug}",
    status_code=200,
    dependencies=[Depends(RateLimiter(times=30, seconds=60))],
)
async def delete_page(
    request: Request,
    slug: str,
    authorization: str = Header(alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a content page (organizer only)."""
    await _require_organizer(db, authorization)

    result = await db.execute(select(ContentPage).where(ContentPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    await db.delete(page)
    await db.commit()

    # Invalidate caches
    await _bust_content_cache()
    await cache_delete_pattern(f"{CACHE_PFX}:get_page:{slug}")

    return {"detail": "ok"}


async def _bust_content_cache():
    """Invalidate all content page caches after mutations."""
    await cache_delete_pattern(f"{CACHE_PFX}:list_pages:*")
```

- [ ] **Step 2: Add import to routes __init__.py**

Modify `backend/app/routes/__init__.py` to add:

```python
from app.routes.content import router as content_router
```

- [ ] **Step 3: Register router in main.py**

Modify `backend/app/main.py` - find where other routers are included and add:

```python
from app.routes import content_router

# ... later where routers are included ...
app.include_router(content_router)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes/content.py backend/app/routes/__init__.py backend/app/main.py
git commit -m "feat: add content page CRUD API routes"
```

---

## Chunk 3: Backend - Update Track Resources Endpoint

### Task 3: Extend Track PUT to Handle resources_markdown

**Files:**
- Modify: `backend/app/routes/tracks.py`

- [ ] **Step 1: Update PUT endpoint to accept resources_markdown**

Find the `update_track` function in `backend/app/routes/tracks.py` and update the field loop to include `resources_markdown`:

```python
    for field in ("name", "description", "challenge", "icon", "color", "prize", "track_type", "criteria", "resources", "resources_markdown"):
        if field in body:
            setattr(track, field, body[field])
```

- [ ] **Step 2: Update _track_to_response to include resources_markdown**

Add to the `_track_to_response` function:

```python
        "resources_markdown": t.resources_markdown,
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/tracks.py
git commit -m "feat: add resources_markdown to track update endpoint"
```

---

## Chunk 4: Frontend - Markdown Renderer Component

### Task 4: Create MarkdownRenderer Component

**Files:**
- Create: `frontend/src/components/MarkdownRenderer.tsx`

- [ ] **Step 1: Install frontend dependencies**

```bash
cd frontend
npm install react-markdown react-syntax-highlighter
```

- [ ] **Step 2: Write MarkdownRenderer component**

Create `frontend/src/components/MarkdownRenderer.tsx`:

```tsx
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY, CYAN, CARD_BG, BORDER } from '../theme';

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div style={{
      color: TEXT_PRIMARY,
      lineHeight: 1.7,
      fontSize: 15,
    }}>
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1 style={{
              fontSize: 28,
              fontWeight: 700,
              margin: '24px 0 16px',
              color: TEXT_PRIMARY,
              borderBottom: `1px solid ${BORDER}`,
              paddingBottom: 8,
            }}>{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 style={{
              fontSize: 22,
              fontWeight: 600,
              margin: '20px 0 12px',
              color: PRIMARY,
            }}>{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 style={{
              fontSize: 18,
              fontWeight: 600,
              margin: '16px 0 8px',
              color: CYAN,
            }}>{children}</h3>
          ),
          p: ({ children }) => (
            <p style={{ margin: '12px 0', color: TEXT_SECONDARY }}>{children}</p>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: PRIMARY,
                textDecoration: 'none',
                borderBottom: `1px solid ${PRIMARY}40`,
              }}
            >{children}</a>
          ),
          ul: ({ children }) => (
            <ul style={{ margin: '12px 0', paddingLeft: 24, color: TEXT_SECONDARY }}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol style={{ margin: '12px 0', paddingLeft: 24, color: TEXT_SECONDARY }}>{children}</ol>
          ),
          li: ({ children }) => (
            <li style={{ margin: '4px 0' }}>{children}</li>
          ),
          code: ({ children, className }) => {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = !match && !className;

            if (isInline) {
              return (
                <code style={{
                  background: `${CARD_BG}`,
                  padding: '2px 6px',
                  borderRadius: 4,
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 13,
                  color: CYAN,
                }}>{children}</code>
              );
            }

            return (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match ? match[1] : 'text'}
                PreTag="div"
                customStyle={{
                  borderRadius: 8,
                  margin: '16px 0',
                  fontSize: 13,
                }}
              >{String(children).replace(/\n$/, '')}</SyntaxHighlighter>
            );
          },
          blockquote: ({ children }) => (
            <blockquote style={{
              borderLeft: `3px solid ${PRIMARY}`,
              margin: '16px 0',
              padding: '8px 16px',
              background: `${CARD_BG}`,
              borderRadius: '0 8px 8px 0',
            }}>{children}</blockquote>
          ),
          table: ({ children }) => (
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              margin: '16px 0',
              fontSize: 14,
            }}>{children}</table>
          ),
          thead: ({ children }) => <thead style={{ background: CARD_BG }}>{children}</thead>,
          th: ({ children }) => (
            <th style={{
              padding: '10px 12px',
              textAlign: 'left',
              fontWeight: 600,
              color: TEXT_PRIMARY,
              borderBottom: `1px solid ${BORDER}`,
            }}>{children}</th>
          ),
          td: ({ children }) => (
            <td style={{
              padding: '8px 12px',
              color: TEXT_SECONDARY,
              borderBottom: `1px solid ${BORDER}`,
            }}>{children}</td>
          ),
          hr: () => (
            <hr style={{
              border: 'none',
              borderTop: `1px solid ${BORDER}`,
              margin: '24px 0',
            }} />
          ),
        }}
      >{content}</ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MarkdownRenderer.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: add MarkdownRenderer component with syntax highlighting"
```

---

## Chunk 5: Frontend - Layout Navigation Update

### Task 5: Add Resources to Navigation

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

**Context:** The nav items are in the `rawNav` array. Add Resources between Tracks and Assistant.

- [ ] **Step 1: Add Resources nav item**

In `frontend/src/components/Layout.tsx`, find the `rawNav` array and add after the Tracks entry:

```typescript
  { to: '/resources', icon: 'menu_book', label: 'Resources' },
```

The order should be: Tracks → Resources → Assistant

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat: add Resources link to main navigation"
```

---

## Chunk 6: Frontend - Resources Page

### Task 6: Create ResourcesPage

**Files:**
- Create: `frontend/src/pages/ResourcesPage.tsx`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add API functions to api.ts**

Add to `frontend/src/services/api.ts` before the export block:

```typescript
// Content Pages
export async function getContentPages(tabGroup?: string) {
  const params = tabGroup ? `?tab_group=${tabGroup}` : '';
  const res = await fetch(`${API_BASE}/content/pages${params}`);
  if (!res.ok) throw new Error('Failed to load content pages');
  return res.json();
}

export async function getContentPage(slug: string) {
  const res = await fetch(`${API_BASE}/content/pages/${slug}`);
  if (!res.ok) throw new Error('Failed to load content page');
  return res.json();
}

export async function createContentPage(data: {
  title: string;
  slug?: string;
  content: string;
  tab_group?: string;
  sort_order?: number;
  tab_group_order?: number;
  is_published?: boolean;
}, token: string) {
  const res = await fetch(`${API_BASE}/content/pages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create content page');
  return res.json();
}

export async function updateContentPage(
  slug: string,
  data: Partial<{
    title: string;
    content: string;
    tab_group: string;
    sort_order: number;
    tab_group_order: number;
    is_published: boolean;
  }>,
  token: string
) {
  const res = await fetch(`${API_BASE}/content/pages/${slug}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update content page');
  return res.json();
}

export async function deleteContentPage(slug: string, token: string) {
  const res = await fetch(`${API_BASE}/content/pages/${slug}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!res.ok) throw new Error('Failed to delete content page');
  return res.json();
}
```

- [ ] **Step 2: Write ResourcesPage component**

Create `frontend/src/pages/ResourcesPage.tsx`:

```tsx
import { useState, useEffect } from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';
import {
  PRIMARY, CYAN, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  CARD_BG, BORDER, TYPO, SPACE, RADIUS,
} from '../theme';

interface ContentPage {
  id: string;
  slug: string;
  title: string;
  content: string;
  tab_group: string;
  sort_order: number;
  tab_group_order: number;
  is_published: boolean;
}

export default function ResourcesPage() {
  const { isMobile } = useMediaQuery();
  const [pages, setPages] = useState<ContentPage[]>([]);
  const [tabGroups, setTabGroups] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPages();
  }, []);

  const loadPages = async () => {
    try {
      setLoading(true);
      const data = await api.getContentPages();
      setPages(data.pages || []);
      setTabGroups(data.tab_groups || []);
      if (data.tab_groups?.length > 0) {
        setActiveTab(data.tab_groups[0]);
      }
    } catch (e) {
      setError('Failed to load resources');
    } finally {
      setLoading(false);
    }
  };

  const activePage = pages.find(p => p.tab_group === activeTab);

  // Sort pages by tab_group_order for tab display, then sort_order within group
  const sortedTabGroups = [...tabGroups].sort((a, b) => {
    const aPage = pages.find(p => p.tab_group === a);
    const bPage = pages.find(p => p.tab_group === b);
    return (aPage?.tab_group_order || 0) - (bPage?.tab_group_order || 0);
  });

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: isMobile ? SPACE.xl : 48 }}>
        <div style={{
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: `linear-gradient(135deg, ${PRIMARY}20 0%, ${CYAN}20 100%)`,
          border: `2px solid ${PRIMARY}40`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto',
          marginBottom: SPACE.lg,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 40, color: PRIMARY }}>menu_book</span>
        </div>

        <h1 style={{
          ...TYPO.h1,
          fontSize: isMobile ? 28 : 36,
          marginBottom: SPACE.md,
          background: `linear-gradient(135deg, ${TEXT_PRIMARY} 0%, ${CYAN} 100%)`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          Resources
        </h1>

        <p style={{
          color: TEXT_SECONDARY,
          fontSize: isMobile ? 15 : 17,
          maxWidth: 560,
          margin: '0 auto',
        }}>
          Guides, APIs, tutorials, and everything you need to build amazing projects.
        </p>
      </div>

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: SPACE.xl, color: TEXT_MUTED }}>
          Loading resources...
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div style={{
          textAlign: 'center',
          padding: SPACE.xl,
          color: '#ef4444',
          background: 'rgba(239, 68, 68, 0.1)',
          borderRadius: RADIUS.lg,
        }}>
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && pages.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: `${SPACE.xl * 2}px ${SPACE.xl}`,
          color: TEXT_MUTED,
          background: CARD_BG,
          borderRadius: RADIUS.lg,
          border: `1px solid ${BORDER}`,
        }}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: SPACE.md, color: PRIMARY }}>construction</span>
          <h3 style={{ ...TYPO.h3, marginBottom: SPACE.sm, color: TEXT_SECONDARY }}>Coming Soon</h3>
          <p>Resources are being prepared. Check back soon!</p>
        </div>
      )}

      {/* Content with Tabs */}
      {!loading && !error && pages.length > 0 && (
        <>
          {/* Tab Navigation */}
          <div style={{
            display: 'flex',
            gap: SPACE.xs,
            marginBottom: SPACE.lg,
            borderBottom: `1px solid ${BORDER}`,
            overflowX: 'auto',
            paddingBottom: 1,
          }}>
            {sortedTabGroups.map((group) => (
              <button
                key={group}
                onClick={() => setActiveTab(group)}
                style={{
                  padding: `${SPACE.md}px ${SPACE.lg}px`,
                  background: activeTab === group ? `${PRIMARY}15` : 'transparent',
                  border: 'none',
                  borderBottom: `2px solid ${activeTab === group ? PRIMARY : 'transparent'}`,
                  color: activeTab === group ? PRIMARY : TEXT_SECONDARY,
                  fontSize: 15,
                  fontWeight: activeTab === group ? 600 : 500,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  textTransform: 'capitalize',
                }}
              >
                {group.replace(/-/g, ' ')}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div style={{
            background: CARD_BG,
            borderRadius: RADIUS.lg,
            padding: isMobile ? SPACE.lg : SPACE.xl,
            border: `1px solid ${BORDER}`,
          }}>
            {activePage ? (
              <>
                <h2 style={{
                  ...TYPO.h2,
                  marginBottom: SPACE.lg,
                  color: TEXT_PRIMARY,
                }}>{activePage.title}</h2>
                <MarkdownRenderer content={activePage.content} />
              </>
            ) : (
              <p style={{ color: TEXT_MUTED }}>No content available for this section.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add routes to App.tsx**

Modify `frontend/src/App.tsx`:

Add import:
```typescript
import ResourcesPage from './pages/ResourcesPage';
```

Add route inside the Layout Route:
```typescript
<Route path="/resources" element={<ResourcesPage />} />
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ResourcesPage.tsx frontend/src/services/api.ts frontend/src/App.tsx
git commit -m "feat: add ResourcesPage with tabbed navigation"
```

---

## Chunk 7: Frontend - TrackCard Resources Enhancement

### Task 7: Update TrackCard with Resources Sub-tab

**Files:**
- Modify: `frontend/src/pages/TracksPage.tsx`

- [ ] **Step 1: Update Track interface**

Add to the Track interface:
```typescript
  resources_markdown?: string;
```

- [ ] **Step 2: Update TrackDetails to show Resources sub-tab**

Replace the TrackDetails component with an enhanced version that includes Resources sub-tab. The component should:
1. Add a "Resources" main section alongside Challenge/Judging
2. Within Resources, show "Quick Links" and "Guides" sub-tabs
3. Only show Resources tab if track has resources OR resources_markdown
4. Only show sub-tabs if they have content

```tsx
interface TrackDetailsProps {
  track: Track;
  hackathonId: string | undefined;
  isMobile: boolean;
}

function TrackDetails({ track, hackathonId, isMobile }: TrackDetailsProps) {
  const [activeSection, setActiveSection] = useState<'challenge' | 'judging' | 'resources'>('challenge');
  const [resourcesView, setResourcesView] = useState<'links' | 'guides'>('links');

  const hasQuickLinks = track.resources && track.resources.length > 0;
  const hasGuides = track.resources_markdown && track.resources_markdown.trim().length > 0;
  const hasResources = hasQuickLinks || hasGuides;

  return (
    <div>
      {/* Section Tabs */}
      <div style={{
        display: 'flex',
        gap: SPACE.xs,
        marginBottom: SPACE.lg,
        borderBottom: `1px solid ${BORDER}`,
      }}>
        {['challenge', 'judging', hasResources && 'resources'].filter(Boolean).map((section) => (
          <button
            key={section}
            onClick={() => setActiveSection(section as any)}
            style={{
              padding: `${SPACE.sm}px ${SPACE.md}px`,
              background: activeSection === section ? `${track.color}15` : 'transparent',
              border: 'none',
              borderBottom: `2px solid ${activeSection === section ? track.color : 'transparent'}`,
              color: activeSection === section ? track.color : TEXT_SECONDARY,
              fontSize: 14,
              fontWeight: activeSection === section ? 600 : 500,
              cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {section}
          </button>
        ))}
      </div>

      {/* Challenge Section */}
      {activeSection === 'challenge' && (
        <div style={{
          background: `linear-gradient(135deg, ${track.color}12 0%, ${track.color}05 100%)`,
          border: `1px solid ${track.color}25`,
          borderRadius: RADIUS.lg,
          padding: isMobile ? SPACE.lg : `${SPACE.lg}px ${SPACE.xl}px`,
          whiteSpace: 'pre-line',
          fontSize: 15,
          color: TEXT_PRIMARY,
        }}>
          {track.challenge || track.description}
        </div>
      )}

      {/* Judging Section */}
      {activeSection === 'judging' && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
          gap: SPACE.xl,
        }}>
          {/* Judging Criteria */}
          <div>
            <h4 style={{
              ...TYPO['label-caps'],
              color: track.color,
              marginBottom: SPACE.md,
            }}>Judging Criteria</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACE.sm }}>
              {(track.criteria || []).map((criterion, idx) => (
                <span key={idx} style={{
                  padding: '8px 14px',
                  borderRadius: RADIUS.md,
                  background: `${track.color}12`,
                  color: track.color,
                  fontSize: 13,
                  fontWeight: 600,
                }}>{criterion}</span>
              ))}
            </div>
          </div>

          {/* Prize */}
          <div>
            <h4 style={{
              ...TYPO['label-caps'],
              color: track.color,
              marginBottom: SPACE.md,
            }}>Prize</h4>
            <div style={{
              padding: SPACE.lg,
              borderRadius: RADIUS.lg,
              background: `linear-gradient(135deg, ${track.color}15 0%, ${track.color}08 100%)`,
              border: `1px solid ${track.color}30`,
              textAlign: 'center',
              color: track.color,
              fontSize: 20,
              fontWeight: 800,
            }}>
              {track.prize || 'Prize TBA'}
            </div>
          </div>
        </div>
      )}

      {/* Resources Section */}
      {activeSection === 'resources' && hasResources && (
        <div>
          {/* Resources Sub-tabs */}
          {(hasQuickLinks && hasGuides) && (
            <div style={{
              display: 'flex',
              gap: SPACE.xs,
              marginBottom: SPACE.lg,
            }}>
              {hasQuickLinks && (
                <button
                  onClick={() => setResourcesView('links')}
                  style={{
                    padding: `${SPACE.sm}px ${SPACE.md}px`,
                    background: resourcesView === 'links' ? `${track.color}15` : 'transparent',
                    border: `1px solid ${resourcesView === 'links' ? track.color : BORDER}`,
                    borderRadius: RADIUS.md,
                    color: resourcesView === 'links' ? track.color : TEXT_SECONDARY,
                    fontSize: 13,
                    fontWeight: resourcesView === 'links' ? 600 : 500,
                    cursor: 'pointer',
                  }}
                >
                  Quick Links
                </button>
              )}
              {hasGuides && (
                <button
                  onClick={() => setResourcesView('guides')}
                  style={{
                    padding: `${SPACE.sm}px ${SPACE.md}px`,
                    background: resourcesView === 'guides' ? `${track.color}15` : 'transparent',
                    border: `1px solid ${resourcesView === 'guides' ? track.color : BORDER}`,
                    borderRadius: RADIUS.md,
                    color: resourcesView === 'guides' ? track.color : TEXT_SECONDARY,
                    fontSize: 13,
                    fontWeight: resourcesView === 'guides' ? 600 : 500,
                    cursor: 'pointer',
                  }}
                >
                  Guides
                </button>
              )}
            </div>
          )}

          {/* Quick Links View */}
          {(resourcesView === 'links' || (!hasGuides && hasQuickLinks)) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE.sm }}>
              {track.resources?.map((resource, idx) => (
                <a
                  key={idx}
                  href={resource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: SPACE.md,
                    padding: '12px 16px',
                    borderRadius: RADIUS.md,
                    background: CARD_BG,
                    color: TEXT_PRIMARY,
                    textDecoration: 'none',
                    fontSize: 14,
                    border: `1px solid ${BORDER}`,
                  }}
                >
                  <span className="material-symbols-outlined" style={{ color: track.color }}>link</span>
                  <span style={{ flex: 1 }}>{resource.name}</span>
                  <span className="material-symbols-outlined" style={{ fontSize: 16, color: TEXT_MUTED }}>open_in_new</span>
                </a>
              ))}
            </div>
          )}

          {/* Guides View */}
          {(resourcesView === 'guides' || (!hasQuickLinks && hasGuides)) && (
            <div style={{
              background: CARD_BG,
              borderRadius: RADIUS.lg,
              padding: SPACE.lg,
              border: `1px solid ${BORDER}`,
            }}>
              <MarkdownRenderer content={track.resources_markdown || ''} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add import for MarkdownRenderer and useState**

Add imports at top:
```typescript
import MarkdownRenderer from '../components/MarkdownRenderer';
```

Make sure useState is imported from react (should already be there).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/TracksPage.tsx
git commit -m "feat: add Resources sub-tab to TrackCard with Quick Links and Guides"
```

---

## Chunk 8: Frontend - Content Editor Page

### Task 8: Create ContentEditorPage for Organizers

**Files:**
- Create: `frontend/src/pages/ContentEditorPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write ContentEditorPage component**

Create `frontend/src/pages/ContentEditorPage.tsx`:

```tsx
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useToast } from '../contexts/ToastContext';
import * as api from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';
import {
  PRIMARY, CYAN, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, BORDER, TYPO, SPACE, RADIUS,
} from '../theme';

interface ContentPage {
  id: string;
  slug: string;
  title: string;
  content: string;
  tab_group: string;
  sort_order: number;
  tab_group_order: number;
  is_published: boolean;
}

const DEFAULT_PAGE = {
  slug: '',
  title: '',
  content: '',
  tab_group: 'resources',
  sort_order: 0,
  tab_group_order: 0,
  is_published: true,
};

export default function ContentEditorPage() {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const { isMobile } = useMediaQuery();
  const { showToast } = useToast();
  const [pages, setPages] = useState<ContentPage[]>([]);
  const [selectedPage, setSelectedPage] = useState<ContentPage | null>(null);
  const [form, setForm] = useState(DEFAULT_PAGE);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadPages = useCallback(async () => {
    try {
      const data = await api.getContentPages();
      setPages(data.pages || []);
    } catch (e) {
      showToast('Failed to load pages', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadPages();
  }, [loadPages]);

  // Redirect non-organizers
  useEffect(() => {
    if (user && user.role !== 'organizer') {
      navigate('/');
    }
  }, [user, navigate]);

  const handleSelectPage = (page: ContentPage) => {
    setSelectedPage(page);
    setForm({
      slug: page.slug,
      title: page.title,
      content: page.content,
      tab_group: page.tab_group,
      sort_order: page.sort_order,
      tab_group_order: page.tab_group_order,
      is_published: page.is_published,
    });
    setIsEditing(true);
  };

  const handleNewPage = () => {
    setSelectedPage(null);
    setForm(DEFAULT_PAGE);
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (!token) return;
    if (!form.title.trim()) {
      showToast('Title is required', 'error');
      return;
    }

    setSaving(true);
    try {
      if (selectedPage) {
        // Update existing
        await api.updateContentPage(selectedPage.slug, {
          title: form.title,
          content: form.content,
          tab_group: form.tab_group,
          sort_order: form.sort_order,
          tab_group_order: form.tab_group_order,
          is_published: form.is_published,
        }, token);
        showToast('Page updated successfully', 'success');
      } else {
        // Create new
        await api.createContentPage({
          title: form.title,
          slug: form.slug || undefined,
          content: form.content,
          tab_group: form.tab_group,
          sort_order: form.sort_order,
          tab_group_order: form.tab_group_order,
          is_published: form.is_published,
        }, token);
        showToast('Page created successfully', 'success');
      }
      await loadPages();
      setIsEditing(false);
    } catch (e: any) {
      showToast(e.message || 'Failed to save page', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!token || !selectedPage) return;
    if (!confirm('Are you sure you want to delete this page?')) return;

    try {
      await api.deleteContentPage(selectedPage.slug, token);
      showToast('Page deleted', 'success');
      await loadPages();
      setIsEditing(false);
      setSelectedPage(null);
      setForm(DEFAULT_PAGE);
    } catch (e: any) {
      showToast(e.message || 'Failed to delete page', 'error');
    }
  };

  if (loading) {
    return <div style={{ padding: SPACE.xl, color: TEXT_MUTED }}>Loading...</div>;
  }

  // Group pages by tab_group
  const pagesByGroup = pages.reduce((acc, page) => {
    if (!acc[page.tab_group]) acc[page.tab_group] = [];
    acc[page.tab_group].push(page);
    return acc;
  }, {} as Record<string, ContentPage[]>);

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: isMobile ? SPACE.md : SPACE.xl }}>
      {/* Header */}
      <div style={{ marginBottom: SPACE.xl }}>
        <h1 style={{ ...TYPO.h1, marginBottom: SPACE.sm }}>Content Management</h1>
        <p style={{ color: TEXT_SECONDARY }}>Create and edit markdown pages for Resources, FAQ, and more.</p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '300px 1fr',
        gap: SPACE.xl,
      }}>
        {/* Left Panel - Page List */}
        <div style={{
          background: CARD_BG,
          borderRadius: RADIUS.lg,
          border: `1px solid ${BORDER}`,
          padding: SPACE.lg,
        }}>
          <button
            onClick={handleNewPage}
            style={{
              width: '100%',
              padding: `${SPACE.md}px ${SPACE.lg}px`,
              background: PRIMARY,
              color: TEXT_WHITE,
              border: 'none',
              borderRadius: RADIUS.md,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
              marginBottom: SPACE.lg,
            }}
          >
            + New Page
          </button>

          {Object.entries(pagesByGroup).map(([group, groupPages]) => (
            <div key={group} style={{ marginBottom: SPACE.lg }}>
              <h4 style={{
                ...TYPO['label-caps'],
                color: TEXT_MUTED,
                marginBottom: SPACE.sm,
                textTransform: 'capitalize',
              }}>{group}</h4>
              {groupPages.map(page => (
                <button
                  key={page.id}
                  onClick={() => handleSelectPage(page)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: `${SPACE.sm}px ${SPACE.md}px`,
                    background: selectedPage?.id === page.id ? `${PRIMARY}15` : 'transparent',
                    border: 'none',
                    borderRadius: RADIUS.md,
                    color: selectedPage?.id === page.id ? PRIMARY : TEXT_PRIMARY,
                    fontSize: 14,
                    cursor: 'pointer',
                    marginBottom: 2,
                    opacity: page.is_published ? 1 : 0.5,
                  }}
                >
                  {page.title}
                  {!page.is_published && <span style={{ color: TEXT_MUTED, marginLeft: 8 }}>(draft)</span>}
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* Right Panel - Editor */}
        <div style={{
          background: CARD_BG,
          borderRadius: RADIUS.lg,
          border: `1px solid ${BORDER}`,
          padding: SPACE.lg,
        }}>
          {!isEditing ? (
            <div style={{
              textAlign: 'center',
              padding: `${SPACE.xl * 2}px`,
              color: TEXT_MUTED,
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: SPACE.md }}>edit_note</span>
              <p>Select a page to edit or create a new one</p>
            </div>
          ) : (
            <>
              {/* Form Fields */}
              <div style={{ marginBottom: SPACE.lg }}>
                <div style={{ marginBottom: SPACE.md }}>
                  <label style={{ display: 'block', color: TEXT_SECONDARY, fontSize: 13, marginBottom: SPACE.xs }}>Title</label>
                  <input
                    type="text"
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    placeholder="Page Title"
                    style={{
                      width: '100%',
                      padding: `${SPACE.md}px`,
                      background: INPUT_BG,
                      border: `1px solid ${BORDER}`,
                      borderRadius: RADIUS.md,
                      color: TEXT_PRIMARY,
                      fontSize: 15,
                    }}
                  />
                </div>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr 1fr',
                  gap: SPACE.md,
                }}>
                  <div>
                    <label style={{ display: 'block', color: TEXT_SECONDARY, fontSize: 13, marginBottom: SPACE.xs }}>Slug</label>
                    <input
                      type="text"
                      value={form.slug}
                      onChange={(e) => setForm({ ...form, slug: e.target.value })}
                      placeholder="page-slug"
                      disabled={!!selectedPage}
                      style={{
                        width: '100%',
                        padding: `${SPACE.sm}px ${SPACE.md}px`,
                        background: INPUT_BG,
                        border: `1px solid ${BORDER}`,
                        borderRadius: RADIUS.md,
                        color: TEXT_PRIMARY,
                        fontSize: 14,
                        opacity: selectedPage ? 0.6 : 1,
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: TEXT_SECONDARY, fontSize: 13, marginBottom: SPACE.xs }}>Tab Group</label>
                    <input
                      type="text"
                      value={form.tab_group}
                      onChange={(e) => setForm({ ...form, tab_group: e.target.value })}
                      placeholder="resources"
                      style={{
                        width: '100%',
                        padding: `${SPACE.sm}px ${SPACE.md}px`,
                        background: INPUT_BG,
                        border: `1px solid ${BORDER}`,
                        borderRadius: RADIUS.md,
                        color: TEXT_PRIMARY,
                        fontSize: 14,
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: TEXT_SECONDARY, fontSize: 13, marginBottom: SPACE.xs }}>Order</label>
                    <input
                      type="number"
                      value={form.sort_order}
                      onChange={(e) => setForm({ ...form, sort_order: parseInt(e.target.value) || 0 })}
                      style={{
                        width: '100%',
                        padding: `${SPACE.sm}px ${SPACE.md}px`,
                        background: INPUT_BG,
                        border: `1px solid ${BORDER}`,
                        borderRadius: RADIUS.md,
                        color: TEXT_PRIMARY,
                        fontSize: 14,
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', color: TEXT_SECONDARY, fontSize: 13, marginBottom: SPACE.xs }}>Group Order</label>
                    <input
                      type="number"
                      value={form.tab_group_order}
                      onChange={(e) => setForm({ ...form, tab_group_order: parseInt(e.target.value) || 0 })}
                      style={{
                        width: '100%',
                        padding: `${SPACE.sm}px ${SPACE.md}px`,
                        background: INPUT_BG,
                        border: `1px solid ${BORDER}`,
                        borderRadius: RADIUS.md,
                        color: TEXT_PRIMARY,
                        fontSize: 14,
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Markdown Editor with Preview */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
                gap: SPACE.md,
                marginBottom: SPACE.lg,
              }}>
                <div>
                  <label style={{ display: 'block', color: TEXT_SECONDARY, fontSize: 13, marginBottom: SPACE.xs }}>Markdown</label>
                  <textarea
                    value={form.content}
                    onChange={(e) => setForm({ ...form, content: e.target.value })}
                    placeholder="# Your markdown content here..."
                    style={{
                      width: '100%',
                      height: 400,
                      padding: SPACE.md,
                      background: INPUT_BG,
                      border: `1px solid ${BORDER}`,
                      borderRadius: RADIUS.md,
                      color: TEXT_PRIMARY,
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 13,
                      lineHeight: 1.6,
                      resize: 'vertical',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', color: TEXT_SECONDARY, fontSize: 13, marginBottom: SPACE.xs }}>Preview</label>
                  <div style={{
                    height: 400,
                    padding: SPACE.md,
                    background: INPUT_BG,
                    border: `1px solid ${BORDER}`,
                    borderRadius: RADIUS.md,
                    overflow: 'auto',
                  }}>
                    <MarkdownRenderer content={form.content} />
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div style={{
                display: 'flex',
                gap: SPACE.md,
                alignItems: 'center',
                borderTop: `1px solid ${BORDER}`,
                paddingTop: SPACE.lg,
              }}>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  style={{
                    padding: `${SPACE.md}px ${SPACE.xl}px`,
                    background: PRIMARY,
                    color: TEXT_WHITE,
                    border: 'none',
                    borderRadius: RADIUS.md,
                    fontSize: 14,
                    fontWeight: 600,
                    cursor: saving ? 'not-allowed' : 'pointer',
                    opacity: saving ? 0.7 : 1,
                  }}
                >
                  {saving ? 'Saving...' : (selectedPage ? 'Update Page' : 'Create Page')}
                </button>

                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: SPACE.sm,
                  cursor: 'pointer',
                }}>
                  <input
                    type="checkbox"
                    checked={form.is_published}
                    onChange={(e) => setForm({ ...form, is_published: e.target.checked })}
                  />
                  <span style={{ color: TEXT_SECONDARY, fontSize: 14 }}>Published</span>
                </label>

                {selectedPage && (
                  <button
                    onClick={handleDelete}
                    style={{
                      marginLeft: 'auto',
                      padding: `${SPACE.md}px ${SPACE.xl}px`,
                      background: 'transparent',
                      color: '#ef4444',
                      border: `1px solid #ef4444`,
                      borderRadius: RADIUS.md,
                      fontSize: 14,
                      cursor: 'pointer',
                    }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add route to App.tsx**

Add import:
```typescript
import ContentEditorPage from './pages/ContentEditorPage';
```

Add route:
```typescript
<Route path="/admin/content" element={<ContentEditorPage />} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ContentEditorPage.tsx frontend/src/App.tsx
git commit -m "feat: add ContentEditorPage for organizer markdown editing"
```

---

## Chunk 9: Backend - Default Content Seeding

### Task 9: Create Default Content Pages

**Files:**
- Create: `backend/app/seed_content.py`
- Modify: `backend/app/main.py` (optional - call on startup)

**Context:** The spec requires default pages: getting-started, apis, hardware. These will be created if they don't exist.

- [ ] **Step 1: Create seed_content.py**

Create `backend/app/seed_content.py`:

```python
"""Seed default content pages for new hackathons."""

from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentPage, User, UserRole

DEFAULT_PAGES = [
    {
        "slug": "getting-started",
        "title": "Getting Started",
        "content": """# Getting Started

Welcome to the hackathon! Here's everything you need to know to get started.

## Prerequisites

- Laptop with your development environment set up
- GitHub account
- Basic knowledge of programming

## Quick Links

- [Hackathon Discord](#) - Join the community
- [Devpost Submission](#) - Submit your project
- [Code of Conduct](#) - Read our guidelines

## Schedule Overview

| Time | Event |
|------|-------|
| Day 1, 9:00 AM | Opening Ceremony |
| Day 1, 10:00 AM | Hacking Begins |
| Day 2, 12:00 PM | Project Submissions Due |
| Day 2, 2:00 PM | Closing Ceremony |

## Need Help?

Ask questions in Discord or visit the Help Desk!""",
        "tab_group": "resources",
        "sort_order": 0,
        "tab_group_order": 0,
    },
    {
        "slug": "apis",
        "title": "APIs & Tools",
        "content": """# APIs & Tools

A curated list of free APIs and tools perfect for hackathon projects.

## Popular APIs

### AI/ML
- **OpenAI API** - GPT-4, DALL-E, embeddings
- **Hugging Face** - Free tier for ML models
- **Claude API** - Anthropic's AI assistant

### Data Sources
- **Data.gov** - US government open data
- **OpenWeatherMap** - Weather data
- **NewsAPI** - News headlines

### Communication
- **Twilio** - SMS, voice, video
- **SendGrid** - Email delivery
- **Stream** - Chat and activity feeds

## Development Tools

- **GitHub Copilot** - AI pair programming
- **Vercel** - Frontend deployment
- **Railway/Render** - Backend deployment
- **MongoDB Atlas** - Free database hosting

## Tutorials

Check the Getting Started tab for tutorials on using these APIs!""",
        "tab_group": "resources",
        "sort_order": 1,
        "tab_group_order": 1,
    },
    {
        "slug": "hardware",
        "title": "Hardware",
        "content": """# Hardware

Information about available hardware and equipment.

## Available Hardware

Check with organizers for available hardware:
- Arduino kits
- Raspberry Pi
- Sensors and actuators
- VR headsets
- Microcontrollers

## Getting Started with Hardware

### Arduino
```cpp
void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);
  delay(1000);
  digitalWrite(LED_BUILTIN, LOW);
  delay(1000);
}
```

### Raspberry Pi
```python
from gpiozero import LED
from time import sleep

led = LED(17)

while True:
    led.on()
    sleep(1)
    led.off()
    sleep(1)
```

## Project Ideas

- IoT weather station
- Smart home controller
- Motion-activated camera
- Wearable fitness tracker

## Safety Guidelines

- Always power off before wiring
- Check voltage requirements
- Ask mentors for help with complex setups""",
        "tab_group": "resources",
        "sort_order": 2,
        "tab_group_order": 2,
    },
]


async def seed_default_content(db: AsyncSession, organizer_id: str):
    """Create default content pages if they don't exist."""
    for page_data in DEFAULT_PAGES:
        # Check if page exists
        result = await db.execute(
            select(ContentPage).where(ContentPage.slug == page_data["slug"])
        )
        if result.scalar_one_or_none():
            continue  # Skip if exists

        page = ContentPage(
            slug=page_data["slug"],
            title=page_data["title"],
            content=page_data["content"],
            tab_group=page_data["tab_group"],
            sort_order=page_data["sort_order"],
            tab_group_order=page_data["tab_group_order"],
            is_published=True,
            created_by=organizer_id,
            created_at=datetime.now(UTC),
        )
        db.add(page)

    await db.commit()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/seed_content.py
git commit -m "feat: add default content pages seeding"
```

---

## Chunk 10: Backend - Database Migration

### Task 10: Create Alembic Migration

**Files:**
- Create: `backend/app/alembic/versions/XXX_add_content_pages_and_track_resources_markdown.py`

- [ ] **Step 1: Generate migration**

```bash
cd backend
alembic revision --autogenerate -m "add content_pages table and track resources_markdown"
```

- [ ] **Step 2: Verify migration**

Check the generated migration file includes:
1. `content_pages` table creation
2. `resources_markdown` column added to `tracks` table
3. All indexes defined in the model

- [ ] **Step 3: Run migration locally**

```bash
cd backend
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/alembic/versions/
git commit -m "feat: add database migration for content pages and track resources"
```

---

## Chunk 11: Backend - Dependencies

### Task 11: Add Backend Dependencies

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/pyproject.toml` (if exists)

- [ ] **Step 1: Add dependencies**

Add to `backend/requirements.txt`:
```
markdown>=3.5
bleach>=6.1
```

- [ ] **Step 2: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add markdown and bleach dependencies"
```

---

## Chunk 12: Integration Testing

### Task 12: Manual Testing Checklist

- [ ] **Test Content Pages API:**
  - POST /api/content/pages - create page as organizer
  - GET /api/content/pages - list pages
  - GET /api/content/pages/{slug} - get single page
  - PUT /api/content/pages/{slug} - update page
  - DELETE /api/content/pages/{slug} - delete page
  - Verify 403 for non-organizer attempts

- [ ] **Test Track Resources:**
  - PUT /api/hackathons/{id}/tracks/{track_id} with resources_markdown
  - Verify GET returns resources_markdown

- [ ] **Test Frontend Pages:**
  - Navigate to /resources - see tabs and content
  - Navigate to /admin/content as organizer - CRUD operations
  - Navigate to /tracks - expand track, see Resources tab

- [ ] **Commit after testing**

```bash
git commit --allow-empty -m "test: manual testing completed for editable markdown resources"
```

---

## Summary

This plan implements:
1. **Backend**: ContentPage model, CRUD API, track resources_markdown extension
2. **Frontend**: MarkdownRenderer, ResourcesPage with tabs, TrackCard enhancement, ContentEditorPage
3. **Database**: Migration for content_pages table and track column
4. **Navigation**: Resources link in main nav, /admin/content route

All features follow existing codebase patterns and are implemented with TDD principles.
