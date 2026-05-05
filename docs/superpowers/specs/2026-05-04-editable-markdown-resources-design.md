# Editable Markdown Resources Design

## Overview
Enable organizers to edit resource content using Markdown for both track-specific resources and a global resources page.

## Goals
- Allow organizers to customize track "Starter Resources" beyond just links
- Create a global /resources page with tabbed sections for hackers
- Provide a simple markdown editing interface for organizers

## Architecture

### Data Models

#### 1. ContentPage (Global Resources)
```python
class ContentPage(Base):
    __tablename__ = "content_pages"

    id = Column(Guid, primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False)  # URL identifier
    title = Column(String(200), nullable=False)              # Display title
    content = Column(Text, nullable=False)                  # Markdown content
    tab_group = Column(String(50), nullable=False)         # "resources", "faq", etc.
    sort_order = Column(Integer, default=0, nullable=False)  # Ordering within tab group
tab_group_order = Column(Integer, default=0, nullable=False)  # Ordering of tab groups (e.g., Getting Started before Hardware)
    is_published = Column(Boolean, default=True, nullable=False)
    created_by = Column(Guid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC))
```

#### 2. Track Resources Enhancement
Extend existing `Track` model:
- Keep `resources` JSON field for quick links
- Add `resources_markdown` Text field for rich content/guides

### API Endpoints

#### Content Pages (Organizer only for writes)
```
GET  /api/content/pages?tab_group=resources     # List pages for a tab group
GET  /api/content/pages/:slug                  # Get single page (public)
POST /api/content/pages                          # Create page (organizer only)
PUT  /api/content/pages/:slug                     # Update page (organizer only)
DELETE /api/content/pages/:slug                 # Delete page (organizer only)
```

**Error Responses:**
- `403 Forbidden` - User is not an organizer
- `404 Not Found` - Page or track not found
- `409 Conflict` - Slug already exists (on POST)
- `422 Unprocessable` - Invalid slug format or missing required fields

#### Track Resources (Organizer only)
```
PUT /api/hackathons/:id/tracks/:track_id/resources
Body: {
  "resources": [...],           # Existing JSON links array
  "resources_markdown": "..."   # New markdown content
}
```

### Frontend Components

#### 1. ResourcesPage (`/resources`)
- Tab navigation at top (Getting Started, APIs, Hardware, Tutorials)
- Active tab content rendered as markdown
- Styled with existing theme (PAGE_BG, PRIMARY, CYAN colors)

#### 2. TrackCard Enhancement
- Show "Resources" tab if track has either resources array OR resources_markdown content
- Two sub-views:
  - "Quick Links" - existing resource links list (hidden if empty)
  - "Guides" - rendered markdown from `resources_markdown` (hidden if empty)

#### 3. ContentEditorPage (`/admin/content`)
- List all content pages grouped by tab_group
- Create/Edit form with:
  - Title input
  - Slug input (auto-generated from title on create, then editable to avoid breaking URLs)
  - Tab group selector
  - Sort order number
  - Markdown textarea with live preview side-by-side
  - Publish toggle
- Delete confirmation

#### 4. MarkdownRenderer Component
- Reusable component for rendering markdown
- Syntax highlighting for code blocks
- Custom styling matching theme (no default browser styles)

### Navigation
- Add "Resources" to main nav between "Tracks" and "Assistant"
- Static nav item; if no published pages exist, show placeholder message: "No resources available yet. Check back soon!"

### Permissions
- Only `organizer` role can create/edit/delete content pages
- All users can view published pages
- Track resources editable by hackathon organizers only

### Default Content
Seed on first organizer setup:
- `/resources/getting-started` - "Getting Started" tab
- `/resources/apis` - "APIs & Tools" tab
- `/resources/hardware` - "Hardware" tab

### Markdown Features Supported
- Headers (H1-H4)
- Paragraphs and line breaks
- Bold, italic, strikethrough
- Links (external open in new tab)
- Lists (ordered/unordered)
- Code blocks with syntax highlighting
- Blockquotes
- Tables
- Horizontal rules

## UI/UX

### Resources Page Layout
```
[Header: Resources]
[Tab Bar: Getting Started | APIs | Hardware | Tutorials]
[Content Area: Rendered Markdown]
```

### Track Resources Layout
```
[Track Card Expanded]
  [Tab: Challenge | Judging | Resources]
    [Sub-tab: Quick Links | Guides]
```

### Editor Layout
```
[Header: Content Management]
[Left Panel: List of pages by tab group]
[Right Panel: Editor]
  [Top: Title, Slug, Tab Group, Order inputs]
  [Middle: Split view - Markdown | Preview]
  [Bottom: Save, Publish toggle, Delete]
```

## Implementation Notes

### Backend
- Use `markdown` library with `fenced_code` and `tables` extensions
- Sanitize HTML with bleach to prevent XSS
- Cache rendered markdown for performance (cache key: `markdown:{page_id}`, invalidate on PUT/DELETE)

### Frontend
- Use `react-markdown` for rendering
- Use `react-syntax-highlighter` for code blocks
- Theme-aware styling using existing color tokens

### Database Migration
1. Create `content_pages` table
2. Add `resources_markdown` column to `tracks` table

## Security
- Sanitize all markdown output using bleach
- Verify organizer permissions on all write endpoints
- Slug validation (alphanumeric, hyphens only)
- Rate limit: 30 requests/minute for write endpoints (POST/PUT/DELETE)

## Future Enhancements
- Image upload for markdown content
- Revision history
- Draft/published state scheduling
- Per-hackathon content pages (in addition to global)
