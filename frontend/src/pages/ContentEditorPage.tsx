import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';
import { Editor } from '@toast-ui/react-editor';
import {
  Card, Table, TableHeader, TableHeadCell, TableRow, TableCell, Button,
} from '../components/Primitives';
import {
  PRIMARY, ERROR, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
  INPUT_BG, INPUT_BORDER, BORDER,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface Resource {
  id: string;
  slug: string;
  title: string;
  content: string;
  tab_group: string;
  sort_order: number;
  tab_group_order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

const EMPTY_RESOURCE: Resource = {
  id: '',
  slug: '',
  title: '',
  content: '',
  tab_group: 'General',
  sort_order: 0,
  tab_group_order: 0,
  is_published: true,
  created_at: '',
  updated_at: '',
};

export default function ContentEditorPage() {
  const { user } = useAuth();
  const { isMobile } = useMediaQuery();
  const [resources, setResources] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Resource | null | undefined>(undefined);
  const [formKey, setFormKey] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewMarkdown, setPreviewMarkdown] = useState('');
  const editorRef = useRef<any>(null);

  const loadResources = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getContentPages();
      setResources(data.pages || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load resources');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadResources();
  }, [loadResources]);

  const startCreate = () => {
    setError(null);
    setFormKey(k => k + 1);
    setEditing({ ...EMPTY_RESOURCE });
    setPreviewMarkdown('');
  };

  const startEdit = (resource: Resource) => {
    setError(null);
    setFormKey(k => k + 1);
    setEditing({ ...resource });
    setPreviewMarkdown(resource.content || '');
  };

  const cancelEdit = () => {
    setEditing(undefined);
    setError(null);
    setPreviewMarkdown('');
  };

  const handleSave = async () => {
    if (!editing) return;

    const slug = (editing.slug || '').trim();
    const title = (editing.title || '').trim();
    const content = editorRef.current?.getInstance()?.getMarkdown() || '';

    if (!slug) {
      setError('Slug is required');
      return;
    }
    if (!/^[a-z0-9-]+$/.test(slug)) {
      setError('Slug must be lowercase alphanumeric with hyphens only');
      return;
    }
    if (!title) {
      setError('Title is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (editing.id) {
        await api.updateResource(slug, {
          title,
          content,
          tab_group: editing.tab_group || undefined,
          sort_order: editing.sort_order,
          tab_group_order: editing.tab_group_order,
        });
      } else {
        await api.createResource({
          slug,
          title,
          content,
          tab_group: editing.tab_group || undefined,
          sort_order: editing.sort_order,
          tab_group_order: editing.tab_group_order,
        });
      }
      setEditing(undefined);
      setPreviewMarkdown('');
      loadResources();
    } catch (e: any) {
      setError(e.message || 'Save failed');
    }
    setSaving(false);
  };

  const handleDelete = async (slug: string) => {
    if (!confirm('Are you sure you want to delete this resource?')) return;
    try {
      await api.deleteResource(slug);
      loadResources();
    } catch (e: any) {
      setError(e.message || 'Delete failed');
    }
  };

  // Bind editor change event for live preview
  useEffect(() => {
    if (editing === undefined) return;
    const timer = setTimeout(() => {
      const editor = editorRef.current?.getInstance();
      if (!editor) return;

      const handleChange = () => {
        setPreviewMarkdown(editor.getMarkdown());
      };

      editor.on('change', handleChange);
      handleChange();

      return () => {
        try {
          editor.off('change', handleChange);
        } catch {
          // ignore
        }
      };
    }, 0);

    return () => clearTimeout(timer);
  }, [formKey]);

  if (user?.role !== 'organizer') {
    return (
      <div style={{ maxWidth: 900, margin: '0 auto', padding: SPACE.xl, textAlign: 'center', color: TEXT_MUTED }}>
        Organizer access only.
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ maxWidth: 900, margin: '0 auto', padding: SPACE.xl, textAlign: 'center', color: TEXT_MUTED }}>
        Loading resources...
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: SPACE.lg }}>
        <div>
          <Link to="/resources" style={{ color: TEXT_MUTED, fontSize: 13, textDecoration: 'none' }}>
            &larr; View Resources
          </Link>
          <h1 style={{ ...TYPO.h1, marginTop: SPACE.xs }}>Content Editor</h1>
        </div>
        <Button onClick={startCreate}>+ Add Resource</Button>
      </div>

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.12)',
          border: `1px solid ${ERROR}`,
          borderRadius: RADIUS.md,
          padding: '10px 16px',
          marginBottom: SPACE.md,
          color: ERROR,
          fontSize: 14,
        }}>
          {error}
        </div>
      )}

      {/* List section */}
      <Card style={{ marginBottom: SPACE.xl }}>
        <Table>
          <TableHeader>
            <TableHeadCell>Title</TableHeadCell>
            <TableHeadCell>Slug</TableHeadCell>
            <TableHeadCell>Tab Group</TableHeadCell>
            <TableHeadCell align="right">Sort Order</TableHeadCell>
            <TableHeadCell align="right">Actions</TableHeadCell>
          </TableHeader>
          <tbody>
            {resources.map(r => (
              <TableRow key={r.id}>
                <TableCell>
                  <div style={{ fontWeight: 600, color: TEXT_PRIMARY }}>{r.title}</div>
                </TableCell>
                <TableCell>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: TEXT_MUTED }}>
                    {r.slug}
                  </span>
                </TableCell>
                <TableCell>{r.tab_group}</TableCell>
                <TableCell align="right">{r.sort_order}</TableCell>
                <TableCell align="right">
                  <div style={{ display: 'flex', gap: SPACE.sm, justifyContent: 'flex-end' }}>
                    <Button variant="secondary" onClick={() => startEdit(r)}>Edit</Button>
                    <Button variant="ghost" onClick={() => handleDelete(r.slug)}>Delete</Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {resources.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} style={{ textAlign: 'center', color: TEXT_MUTED, padding: SPACE.xl }}>
                  No resources yet. Add your first resource above.
                </TableCell>
              </TableRow>
            )}
          </tbody>
        </Table>
      </Card>

      {/* Editor section */}
      {editing !== undefined && (
        <Card>
          <h2 style={{ ...TYPO.h2, marginBottom: SPACE.lg }}>
            {editing?.id ? 'Edit Resource' : 'New Resource'}
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: SPACE.md, marginBottom: SPACE.md }}>
            <div>
              <label style={fieldLabel}>Slug</label>
              <input
                value={editing?.slug || ''}
                onChange={e => setEditing(prev => {
                  if (prev === undefined) return undefined;
                  return { ...(prev || EMPTY_RESOURCE), slug: e.target.value };
                })}
                disabled={!!editing?.id}
                style={{ ...fieldStyle, opacity: editing?.id ? 0.6 : 1 }}
              />
            </div>
            <div>
              <label style={fieldLabel}>Title</label>
              <input
                value={editing?.title || ''}
                onChange={e => setEditing(prev => {
                  if (prev === undefined) return undefined;
                  return { ...(prev || EMPTY_RESOURCE), title: e.target.value };
                })}
                style={fieldStyle}
              />
            </div>
            <div>
              <label style={fieldLabel}>Tab Group</label>
              <input
                value={editing?.tab_group || ''}
                onChange={e => setEditing(prev => {
                  if (prev === undefined) return undefined;
                  return { ...(prev || EMPTY_RESOURCE), tab_group: e.target.value };
                })}
                style={fieldStyle}
              />
            </div>
            <div style={{ display: 'flex', gap: SPACE.md }}>
              <div style={{ flex: 1 }}>
                <label style={fieldLabel}>Sort Order</label>
                <input
                  type="number"
                  value={editing?.sort_order ?? 0}
                  onChange={e => setEditing(prev => {
                    if (prev === undefined) return undefined;
                    return { ...(prev || EMPTY_RESOURCE), sort_order: parseInt(e.target.value, 10) || 0 };
                  })}
                  style={fieldStyle}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={fieldLabel}>Tab Group Order</label>
                <input
                  type="number"
                  value={editing?.tab_group_order ?? 0}
                  onChange={e => setEditing(prev => {
                    if (prev === undefined) return undefined;
                    return { ...(prev || EMPTY_RESOURCE), tab_group_order: parseInt(e.target.value, 10) || 0 };
                  })}
                  style={fieldStyle}
                />
              </div>
            </div>
          </div>

          <div style={{ marginBottom: SPACE.md }}>
            <label style={fieldLabel}>Content</label>
            <div style={{ border: `1px solid ${INPUT_BORDER}`, borderRadius: RADIUS.md, overflow: 'hidden' }}>
              <Editor
                key={formKey}
                ref={editorRef}
                initialValue={editing?.content || ''}
                previewStyle="tab"
                height="400px"
                initialEditType="wysiwyg"
                useCommandShortcut={true}
              />
            </div>
          </div>

          {/* Live Preview */}
          <div style={{ marginBottom: SPACE.md }}>
            <div style={{ ...TYPO.h3, marginBottom: SPACE.sm, color: TEXT_SECONDARY }}>Preview</div>
            <div style={{
              background: INPUT_BG,
              border: `1px solid ${INPUT_BORDER}`,
              borderRadius: RADIUS.md,
              padding: SPACE.md,
              maxHeight: 400,
              overflow: 'auto',
            }}>
              <MarkdownRenderer content={previewMarkdown} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: SPACE.md, justifyContent: 'flex-end' }}>
            <Button variant="secondary" onClick={cancelEdit}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save Resource'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

const fieldLabel: React.CSSProperties = {
  display: 'block',
  fontSize: 13,
  color: TEXT_MUTED,
  marginBottom: 4,
};

const fieldStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 12px',
  background: INPUT_BG,
  border: `1px solid ${INPUT_BORDER}`,
  borderRadius: 6,
  color: TEXT_PRIMARY,
  fontSize: 14,
  boxSizing: 'border-box',
};
