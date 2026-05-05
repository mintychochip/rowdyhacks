# AI Assistant Builder Mode Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the AI assistant from a Q&A chatbot into a hackathon project accelerator with Chat/Plan/Build modes, enabling teams to go from idea to running prototype within the 6-hour RowdyHacks timeline.

**Architecture:** Three-mode state machine (Chat → Plan → Build) with in-browser Monaco editor, live preview panel, and seamless AI-assisted code generation. Files stored in memory during session with ZIP export.

**Tech Stack:** React + TypeScript, Monaco Editor (@monaco-editor/react), JSZip (export), Zustand (state management), FastAPI backend with AI tool integration.

---

## Chunk 1: Mode State Management Foundation

**Files:**
- Create: `frontend/src/stores/builderStore.ts`
- Create: `frontend/src/types/builder.ts`
- Modify: `frontend/src/pages/AssistantPage.tsx`

### Task 1: Define Builder Types

**Create:** `frontend/src/types/builder.ts`

- [ ] **Step 1: Write type definitions**

```typescript
export type BuilderMode = 'chat' | 'plan' | 'build';

export type ProjectType = 'web' | 'arduino' | 'python' | 'other';

export interface ProjectFile {
  id: string;
  path: string;
  name: string;
  content: string;
  language: string;
  lastModified: Date;
  isDirty: boolean;
}

export interface ProjectPlan {
  id: string;
  name: string;
  description: string;
  targetTrack?: string;
  estimatedHours: number;
  techStack: string[];
  tasks: PlanTask[];
  stretchGoals: string[];
}

export interface PlanTask {
  id: string;
  description: string;
  estimatedMinutes: number;
  completed: boolean;
}

export interface Project {
  id: string;
  name: string;
  type: ProjectType;
  files: ProjectFile[];
  plan: ProjectPlan | null;
  createdAt: Date;
}

export interface BuilderState {
  mode: BuilderMode;
  project: Project | null;
  activeFileId: string | null;
  isTransitioning: boolean;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/builder.ts
git commit -m "feat(builder): add TypeScript types for builder mode"
```

### Task 2: Create Zustand Store

**Create:** `frontend/src/stores/builderStore.ts`

- [ ] **Step 3: Write store implementation**

```typescript
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { BuilderMode, Project, ProjectFile, BuilderState } from '../types/builder';

interface BuilderActions {
  setMode: (mode: BuilderMode) => void;
  startTransition: () => void;
  endTransition: () => void;
  createProject: (name: string, type: string) => void;
  setActiveFile: (fileId: string) => void;
  updateFile: (fileId: string, content: string) => void;
  addFile: (file: ProjectFile) => void;
  deleteFile: (fileId: string) => void;
  setPlan: (plan: Project['plan']) => void;
  reset: () => void;
}

const initialState: BuilderState = {
  mode: 'chat',
  project: null,
  activeFileId: null,
  isTransitioning: false,
};

export const useBuilderStore = create<BuilderState & BuilderActions>()(
  persist(
    (set, get) => ({
      ...initialState,

      setMode: (mode) => set({ mode }),

      startTransition: () => set({ isTransitioning: true }),
      endTransition: () => set({ isTransitioning: false }),

      createProject: (name, type) => {
        const project: Project = {
          id: `proj_${Date.now()}`,
          name,
          type: type as Project['type'],
          files: [],
          plan: null,
          createdAt: new Date(),
        };
        set({ project, mode: 'build' });
      },

      setActiveFile: (fileId) => set({ activeFileId: fileId }),

      updateFile: (fileId, content) => {
        const { project } = get();
        if (!project) return;

        const updatedFiles = project.files.map((f) =>
          f.id === fileId
            ? { ...f, content, lastModified: new Date(), isDirty: true }
            : f
        );
        set({ project: { ...project, files: updatedFiles } });
      },

      addFile: (file) => {
        const { project } = get();
        if (!project) return;
        set({
          project: { ...project, files: [...project.files, file] },
          activeFileId: file.id,
        });
      },

      deleteFile: (fileId) => {
        const { project, activeFileId } = get();
        if (!project) return;

        const updatedFiles = project.files.filter((f) => f.id !== fileId);
        set({
          project: { ...project, files: updatedFiles },
          activeFileId: activeFileId === fileId ? null : activeFileId,
        });
      },

      setPlan: (plan) => {
        const { project } = get();
        if (!project) return;
        set({ project: { ...project, plan } });
      },

      reset: () => set(initialState),
    }),
    {
      name: 'builder-storage',
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/builderStore.ts
git commit -m "feat(builder): add Zustand store for builder state management"
```

### Task 3: Create Mode Router Component

**Create:** `frontend/src/components/builder/ModeRouter.tsx`

- [ ] **Step 5: Write mode router**

```typescript
import { useBuilderStore } from '../../stores/builderStore';
import ChatMode from './modes/ChatMode';
import PlanMode from './modes/PlanMode';
import BuildMode from './modes/BuildMode';

export default function ModeRouter() {
  const mode = useBuilderStore((state) => state.mode);

  switch (mode) {
    case 'chat':
      return <ChatMode />;
    case 'plan':
      return <PlanMode />;
    case 'build':
      return <BuildMode />;
    default:
      return <ChatMode />;
  }
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/builder/ModeRouter.tsx
git commit -m "feat(builder): add mode router component"
```

---

## Chunk 2: Chat Mode with Intent Detection

**Files:**
- Modify: `frontend/src/pages/AssistantPage.tsx`
- Create: `frontend/src/components/builder/modes/ChatMode.tsx`
- Modify: `backend/app/assistant/context_builder.py`

### Task 4: Create ChatMode Component

**Create:** `frontend/src/components/builder/modes/ChatMode.tsx`

- [ ] **Step 7: Write ChatMode component**

```typescript
import { useBuilderStore } from '../../../stores/builderStore';
import ChatInterface from '../chat/ChatInterface';
import ModeSwitcher from '../ModeSwitcher';

export default function ChatMode() {
  const { project, setMode } = useBuilderStore();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <ModeSwitcher currentMode="chat" />
      <div style={{ flex: 1, display: 'flex' }}>
        <ChatInterface
          showBuildButton={!project}
          onStartBuilding={() => setMode('plan')}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/builder/modes/ChatMode.tsx
git commit -m "feat(builder): add ChatMode component shell"
```

### Task 5: Extract Chat Interface

**Create:** `frontend/src/components/builder/chat/ChatInterface.tsx`

- [ ] **Step 9: Extract chat logic from AssistantPage**

Move the chat UI (messages, input, streaming) into this component. Keep all existing functionality.

```typescript
interface ChatInterfaceProps {
  showBuildButton?: boolean;
  onStartBuilding?: () => void;
}

export default function ChatInterface({ showBuildButton, onStartBuilding }: ChatInterfaceProps) {
  // Existing chat logic from AssistantPage
  // Plus build intent detection UI
}
```

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/builder/chat/ChatInterface.tsx
git commit -m "refactor(builder): extract ChatInterface from AssistantPage"
```

### Task 6: Backend Intent Detection

**Modify:** `backend/app/assistant/context_builder.py`

- [ ] **Step 11: Add build intent patterns**

```python
BUILD_INTENT_PATTERNS = [
    r'i want to build',
    r'i want to create',
    r'i want to make',
    r'generate a prototype',
    r'help me code',
    r'i have an idea for',
    r'can you help me with',
    r'how do i build',
    r'start a project',
]

def detect_build_intent(message: str) -> bool:
    """Detect if user wants to start building a project."""
    message_lower = message.lower()
    return any(re.search(pattern, message_lower) for pattern in BUILD_INTENT_PATTERNS)
```

- [ ] **Step 12: Update system prompt to mention builder mode**

```python
parts.append("\n=== BUILDER MODE ===")
parts.append("If the user wants to build a project, suggest using Plan mode to create a roadmap first.")
parts.append("You can help them generate code, create files, and build prototypes.")
```

- [ ] **Step 13: Commit**

```bash
git add backend/app/assistant/context_builder.py
git commit -m "feat(builder): add build intent detection to AI assistant"
```

---

## Chunk 3: Plan Mode

**Files:**
- Create: `frontend/src/components/builder/modes/PlanMode.tsx`
- Create: `frontend/src/components/builder/plan/PlanDisplay.tsx`
- Modify: `backend/app/routes/assistant.py`

### Task 7: Backend Plan Generation

**Modify:** `backend/app/routes/assistant.py`

- [ ] **Step 14: Add plan generation endpoint**

```python
@router.post("/generate-plan")
async def generate_plan(
    description: str,
    hackathon_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a project plan from user description."""
    # Get hackathon info for context
    hackathon = None
    if hackathon_id:
        result = await db.execute(
            select(Hackathon).where(Hackathon.id == hackathon_id)
        )
        hackathon = result.scalar_one_or_none()

    # Build context for plan generation
    builder = ContextBuilder(db)
    system_prompt = await builder.build_plan_system_prompt(
        hackathon=hackathon,
        user_role=current_user.role,
    )

    # Generate plan using LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Create a project plan for: {description}"},
    ]

    plan_json = await llm_client.generate_structured_output(
        messages=messages,
        output_schema=ProjectPlanSchema,
    )

    return {"plan": plan_json}
```

- [ ] **Step 15: Add plan generation prompt**

```python
async def build_plan_system_prompt(self, hackathon, user_role):
    parts = []
    parts.append("You are creating a hackathon project plan. Generate a structured JSON plan.")
    parts.append("The plan should be achievable in 4-5 hours (MVP) with 1-2 hours of stretch goals.")

    if hackathon:
        parts.append(f"\nHackathon: {hackathon.name}")
        parts.append(f"Duration: 6 hours")
        # Include available tracks
        tracks = await self._get_tracks(hackathon.id)
        if tracks:
            parts.append("\nAvailable Prize Tracks:")
            for track in tracks:
                parts.append(f"- {track['name']}: {track['criteria'][:100]}...")

    parts.append("\nGenerate a JSON plan with:")
    parts.append("- name: Project name (concise)")
    parts.append("- description: One sentence summary")
    parts.append("- targetTrack: Best fitting prize track name")
    parts.append("- estimatedHours: Number (4-5 for MVP)")
    parts.append("- techStack: Array of technologies")
    parts.append("- tasks: Array of {description, estimatedMinutes, completed: false}")
    parts.append("- stretchGoals: Array of strings")

    return "\n".join(parts)
```

- [ ] **Step 16: Commit**

```bash
git add backend/app/routes/assistant.py
git commit -m "feat(builder): add backend plan generation endpoint"
```

### Task 8: PlanMode Component

**Create:** `frontend/src/components/builder/modes/PlanMode.tsx`

- [ ] **Step 17: Write PlanMode shell**

```typescript
import { useState } from 'react';
import { useBuilderStore } from '../../../stores/builderStore';
import ModeSwitcher from '../ModeSwitcher';
import PlanDisplay from '../plan/PlanDisplay';
import PlanGenerator from '../plan/PlanGenerator';

export default function PlanMode() {
  const { project, setMode, setPlan } = useBuilderStore();
  const [isGenerating, setIsGenerating] = useState(false);

  const handleAcceptPlan = (plan: ProjectPlan) => {
    setPlan(plan);
    setMode('build');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <ModeSwitcher currentMode="plan" />
      <div style={{ flex: 1, padding: '20px', overflow: 'auto' }}>
        {!project?.plan ? (
          <PlanGenerator
            onPlanGenerated={setPlan}
            isGenerating={isGenerating}
            setIsGenerating={setIsGenerating}
          />
        ) : (
          <PlanDisplay
            plan={project.plan}
            onAccept={() => handleAcceptPlan(project.plan)}
            onEdit={() => {/* Enable editing */}}
            onBack={() => setMode('chat')}
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 18: Commit**

```bash
git add frontend/src/components/builder/modes/PlanMode.tsx
git commit -m "feat(builder): add PlanMode component shell"
```

### Task 9: Plan Display UI

**Create:** `frontend/src/components/builder/plan/PlanDisplay.tsx`

- [ ] **Step 19: Write plan display component**

```typescript
import { CARD_BG, PRIMARY, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY } from '../../../theme';
import type { ProjectPlan } from '../../../types/builder';

interface PlanDisplayProps {
  plan: ProjectPlan;
  onAccept: () => void;
  onEdit: () => void;
  onBack: () => void;
}

export default function PlanDisplay({ plan, onAccept, onEdit, onBack }: PlanDisplayProps) {
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ color: TEXT_PRIMARY, marginBottom: SPACE.md }}>{plan.name}</h1>
      <p style={{ color: TEXT_SECONDARY, marginBottom: SPACE.lg }}>{plan.description}</p>

      {/* Target Track */}
      <div style={{
        background: CARD_BG,
        padding: SPACE.md,
        borderRadius: RADIUS.md,
        marginBottom: SPACE.md
      }}>
        <h3 style={{ color: PRIMARY }}>🎯 Target Track</h3>
        <p style={{ color: TEXT_PRIMARY }}>{plan.targetTrack || 'Not specified'}</p>
        <p style={{ color: TEXT_SECONDARY }}>Est. time: {plan.estimatedHours} hours</p>
      </div>

      {/* Tech Stack */}
      <div style={{ marginBottom: SPACE.md }}>
        <h3 style={{ color: TEXT_PRIMARY }}>📦 Tech Stack</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: SPACE.sm }}>
          {plan.techStack.map((tech) => (
            <span key={tech} style={{
              padding: `${SPACE.xs}px ${SPACE.sm}px`,
              background: 'rgba(6, 182, 212, 0.2)',
              borderRadius: RADIUS.sm,
              color: '#06b6d4',
            }}>
              {tech}
            </span>
          ))}
        </div>
      </div>

      {/* Tasks */}
      <div style={{ marginBottom: SPACE.md }}>
        <h3 style={{ color: TEXT_PRIMARY }}>📝 MVP Tasks</h3>
        {plan.tasks.map((task, i) => (
          <div key={task.id} style={{
            display: 'flex',
            alignItems: 'center',
            gap: SPACE.sm,
            padding: SPACE.sm,
            background: CARD_BG,
            borderRadius: RADIUS.sm,
            marginBottom: SPACE.xs,
          }}>
            <span style={{ color: TEXT_SECONDARY }}>{i + 1}.</span>
            <span style={{ color: TEXT_PRIMARY, flex: 1 }}>{task.description}</span>
            <span style={{ color: TEXT_SECONDARY, fontSize: 12 }}>
              {task.estimatedMinutes}min
            </span>
          </div>
        ))}
      </div>

      {/* Stretch Goals */}
      {plan.stretchGoals.length > 0 && (
        <div style={{ marginBottom: SPACE.lg }}>
          <h3 style={{ color: TEXT_PRIMARY }}>🎁 Stretch Goals</h3>
          <ul style={{ color: TEXT_SECONDARY }}>
            {plan.stretchGoals.map((goal, i) => (
              <li key={i}>{goal}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: SPACE.md }}>
        <button onClick={onAccept} style={{
          padding: `${SPACE.sm}px ${SPACE.lg}px`,
          background: PRIMARY,
          border: 'none',
          borderRadius: RADIUS.md,
          color: '#fff',
          cursor: 'pointer',
        }}>
          🚀 Accept & Start Building
        </button>
        <button onClick={onEdit} style={{
          padding: `${SPACE.sm}px ${SPACE.lg}px`,
          background: 'transparent',
          border: `1px solid ${PRIMARY}`,
          borderRadius: RADIUS.md,
          color: PRIMARY,
          cursor: 'pointer',
        }}>
          ✏️ Edit Plan
        </button>
        <button onClick={onBack} style={{
          padding: `${SPACE.sm}px ${SPACE.lg}px`,
          background: 'transparent',
          border: 'none',
          color: TEXT_SECONDARY,
          cursor: 'pointer',
        }}>
          💬 Back to Chat
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 20: Commit**

```bash
git add frontend/src/components/builder/plan/PlanDisplay.tsx
git commit -m "feat(builder): add PlanDisplay UI component"
```

---

## Chunk 4: Build Mode - File Explorer & Editor

**Files:**
- Create: `frontend/src/components/builder/modes/BuildMode.tsx`
- Create: `frontend/src/components/builder/files/FileExplorer.tsx`
- Create: `frontend/src/components/builder/editor/CodeEditor.tsx`
- Install: `@monaco-editor/react`, `monaco-editor`

### Task 10: Install Monaco Editor

- [ ] **Step 21: Install dependencies**

```bash
cd frontend
npm install @monaco-editor/react monaco-editor jszip
```

- [ ] **Step 22: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(deps): add Monaco editor and JSZip for builder mode"
```

### Task 11: File Explorer Component

**Create:** `frontend/src/components/builder/files/FileExplorer.tsx`

- [ ] **Step 23: Write file explorer**

```typescript
import { useState } from 'react';
import { useBuilderStore } from '../../../stores/builderStore';
import { CARD_BG, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY } from '../../../theme';
import type { ProjectFile } from '../../../types/builder';

const FILE_ICONS: Record<string, string> = {
  html: '🌐',
  css: '🎨',
  js: '📜',
  ts: '📘',
  py: '🐍',
  json: '📋',
  md: '📝',
  ino: '🔌',
  default: '📄',
};

function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  return FILE_ICONS[ext] || FILE_ICONS.default;
}

export default function FileExplorer() {
  const { project, activeFileId, setActiveFile, addFile, deleteFile } = useBuilderStore();
  const [isCreating, setIsCreating] = useState(false);
  const [newFileName, setNewFileName] = useState('');

  if (!project) return null;

  const handleCreateFile = () => {
    if (!newFileName.trim()) return;

    const newFile: ProjectFile = {
      id: `file_${Date.now()}`,
      path: newFileName,
      name: newFileName,
      content: '',
      language: newFileName.split('.').pop() || 'text',
      lastModified: new Date(),
      isDirty: false,
    };

    addFile(newFile);
    setIsCreating(false);
    setNewFileName('');
  };

  return (
    <div style={{
      width: '250px',
      background: CARD_BG,
      borderRight: '1px solid rgba(255,255,255,0.1)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        padding: SPACE.md,
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ color: TEXT_PRIMARY, fontWeight: 600 }}>📁 Files</span>
        <button
          onClick={() => setIsCreating(true)}
          style={{
            background: 'transparent',
            border: 'none',
            color: TEXT_SECONDARY,
            cursor: 'pointer',
            fontSize: 18,
          }}
        >
          +
        </button>
      </div>

      {isCreating && (
        <div style={{ padding: SPACE.sm }}>
          <input
            type="text"
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreateFile()}
            placeholder="filename.ext"
            style={{
              width: '100%',
              padding: SPACE.xs,
              background: 'rgba(255,255,255,0.1)',
              border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: RADIUS.sm,
              color: TEXT_PRIMARY,
            }}
          />
        </div>
      )}

      <div style={{ flex: 1, overflow: 'auto' }}>
        {project.files.map((file) => (
          <div
            key={file.id}
            onClick={() => setActiveFile(file.id)}
            style={{
              padding: `${SPACE.sm}px ${SPACE.md}px`,
              display: 'flex',
              alignItems: 'center',
              gap: SPACE.sm,
              cursor: 'pointer',
              background: activeFileId === file.id ? 'rgba(37, 99, 235, 0.2)' : 'transparent',
              borderLeft: activeFileId === file.id ? `3px solid ${PRIMARY}` : '3px solid transparent',
            }}
          >
            <span>{getFileIcon(file.name)}</span>
            <span style={{
              color: activeFileId === file.id ? TEXT_PRIMARY : TEXT_SECONDARY,
              flex: 1,
            }}>
              {file.name}
              {file.isDirty && ' •'}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                deleteFile(file.id);
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: TEXT_SECONDARY,
                cursor: 'pointer',
                opacity: 0,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = '0')}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 24: Commit**

```bash
git add frontend/src/components/builder/files/FileExplorer.tsx
git commit -m "feat(builder): add FileExplorer component"
```

### Task 12: Code Editor Component

**Create:** `frontend/src/components/builder/editor/CodeEditor.tsx`

- [ ] **Step 25: Write Monaco editor wrapper**

```typescript
import Editor from '@monaco-editor/react';
import { useBuilderStore } from '../../../stores/builderStore';
import { PRIMARY } from '../../../theme';

export default function CodeEditor() {
  const { project, activeFileId, updateFile } = useBuilderStore();

  const activeFile = project?.files.find((f) => f.id === activeFileId);

  if (!activeFile) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'rgba(255,255,255,0.5)',
      }}>
        Select a file to edit
      </div>
    );
  }

  const getLanguage = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    const langMap: Record<string, string> = {
      js: 'javascript',
      ts: 'typescript',
      jsx: 'javascript',
      tsx: 'typescript',
      html: 'html',
      css: 'css',
      py: 'python',
      json: 'json',
      md: 'markdown',
      ino: 'cpp',  // Arduino uses C++ syntax
    };
    return langMap[ext] || 'plaintext';
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <div style={{
        padding: '8px 16px',
        background: 'rgba(0,0,0,0.3)',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ color: '#fff' }}>{activeFile.name}</span>
        {activeFile.isDirty && (
          <span style={{ color: PRIMARY, fontSize: 12 }}>Modified</span>
        )}
      </div>
      <Editor
        height="100%"
        language={getLanguage(activeFile.name)}
        value={activeFile.content}
        onChange={(value) => {
          if (value !== undefined) {
            updateFile(activeFile.id, value);
          }
        }}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          automaticLayout: true,
          scrollBeyondLastLine: false,
        }}
      />
    </div>
  );
}
```

- [ ] **Step 26: Commit**

```bash
git add frontend/src/components/builder/editor/CodeEditor.tsx
git commit -m "feat(builder): add Monaco CodeEditor component"
```

### Task 13: BuildMode Assembly

**Create:** `frontend/src/components/builder/modes/BuildMode.tsx`

- [ ] **Step 27: Assemble BuildMode layout**

```typescript
import { useBuilderStore } from '../../../stores/builderStore';
import ModeSwitcher from '../ModeSwitcher';
import FileExplorer from '../files/FileExplorer';
import CodeEditor from '../editor/CodeEditor';
import PreviewPanel from '../preview/PreviewPanel';
import ExportButton from '../export/ExportButton';

export default function BuildMode() {
  const { project } = useBuilderStore();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <ModeSwitcher currentMode="build" />
      <div style={{
        flex: 1,
        display: 'flex',
        overflow: 'hidden',
      }}>
        <FileExplorer />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <CodeEditor />
        </div>
        <PreviewPanel />
      </div>
      <div style={{
        padding: '12px 20px',
        background: 'rgba(0,0,0,0.3)',
        borderTop: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ color: 'rgba(255,255,255,0.5)' }}>
          {project?.name} • {project?.files.length} files
        </span>
        <ExportButton />
      </div>
    </div>
  );
}
```

- [ ] **Step 28: Commit**

```bash
git add frontend/src/components/builder/modes/BuildMode.tsx
git commit -m "feat(builder): add BuildMode component with file explorer and editor"
```

---

## Chunk 5: Preview Panel & Export

**Files:**
- Create: `frontend/src/components/builder/preview/PreviewPanel.tsx`
- Create: `frontend/src/components/builder/export/ExportButton.tsx`

### Task 14: Preview Panel Component

**Create:** `frontend/src/components/builder/preview/PreviewPanel.tsx`

- [ ] **Step 29: Write preview panel**

```typescript
import { useBuilderStore } from '../../../stores/builderStore';
import { CARD_BG, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY } from '../../../theme';
import { useMemo } from 'react';

export default function PreviewPanel() {
  const { project, activeFileId } = useBuilderStore();

  const previewUrl = useMemo(() => {
    if (!project || project.type !== 'web') return null;

    // Find HTML file to preview
    const htmlFile = project.files.find((f) => f.name.endsWith('.html'));
    if (!htmlFile) return null;

    // Create blob URL from HTML content
    // For embedded resources (CSS/JS), we'd need to inline them or use a service worker
    // MVP: Just show the HTML file content directly
    const blob = new Blob([htmlFile.content], { type: 'text/html' });
    return URL.createObjectURL(blob);
  }, [project]);

  const isWebProject = project?.type === 'web';

  return (
    <div style={{
      width: '400px',
      background: CARD_BG,
      borderLeft: '1px solid rgba(255,255,255,0.1)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        padding: SPACE.md,
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <span style={{ color: TEXT_PRIMARY, fontWeight: 600 }}>
          {isWebProject ? '🌐 Preview' : '📋 Output'}
        </span>
        {previewUrl && (
          <button
            onClick={() => window.open(previewUrl, '_blank')}
            style={{
              background: 'transparent',
              border: 'none',
              color: TEXT_SECONDARY,
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            Open ↗
          </button>
        )}
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: SPACE.md }}>
        {!isWebProject && (
          <div style={{ color: TEXT_SECONDARY }}>
            <p>Preview available for web projects only.</p>
            <p style={{ marginTop: SPACE.md }}>
              For {project?.type} projects, export and run locally.
            </p>
          </div>
        )}

        {isWebProject && !previewUrl && (
          <div style={{ color: TEXT_SECONDARY }}>
            Create an HTML file to see preview.
          </div>
        )}

        {previewUrl && (
          <iframe
            src={previewUrl}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              borderRadius: RADIUS.sm,
              background: '#fff',
            }}
            sandbox="allow-scripts"
            title="Preview"
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 30: Commit**

```bash
git add frontend/src/components/builder/preview/PreviewPanel.tsx
git commit -m "feat(builder): add PreviewPanel with live iframe for web projects"
```

### Task 15: Export Button

**Create:** `frontend/src/components/builder/export/ExportButton.tsx`

- [ ] **Step 31: Write export functionality**

```typescript
import { useState } from 'react';
import JSZip from 'jszip';
import { useBuilderStore } from '../../../stores/builderStore';
import { PRIMARY, RADIUS, SPACE } from '../../../theme';

export default function ExportButton() {
  const { project } = useBuilderStore();
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    if (!project) return;

    setIsExporting(true);

    try {
      const zip = new JSZip();

      // Add all project files
      project.files.forEach((file) => {
        zip.file(file.path, file.content);
      });

      // Generate README
      const readme = generateReadme(project);
      zip.file('README.md', readme);

      // Generate and download
      const blob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.href = url;
      link.download = `${project.name.replace(/\s+/g, '_')}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const generateReadme = (project: Project): string => {
    const plan = project.plan;
    return `# ${project.name}

Generated with RowdyHacks AI Assistant
${plan ? `Target Track: ${plan.targetTrack || 'TBD'}` : ''}

## Files

${project.files.map((f) => `- ${f.name}`).join('\n')}

${plan ? `
## Project Plan

**Estimated Time:** ${plan.estimatedHours} hours

**Tech Stack:** ${plan.techStack.join(', ')}

**Tasks:**
${plan.tasks.map((t) => `- [${t.completed ? 'x' : ' '}] ${t.description} (${t.estimatedMinutes}min)`).join('\n')}
` : ''}

## Getting Started

${getSetupInstructions(project.type)}

---
*Built at RowdyHacks 2026*
`;
  };

  const getSetupInstructions = (type: string): string => {
    switch (type) {
      case 'web':
        return 'Open `index.html` in your browser, or run a local server:\n\n```bash\npython -m http.server 8000\n```';
      case 'python':
        return '```bash\npip install -r requirements.txt\npython app.py\n```';
      case 'arduino':
        return '1. Open `.ino` file in Arduino IDE\n2. Select your board and port\n3. Upload to Arduino';
      default:
        return 'See individual file comments for setup instructions.';
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={isExporting || !project}
      style={{
        padding: `${SPACE.sm}px ${SPACE.lg}px`,
        background: PRIMARY,
        border: 'none',
        borderRadius: RADIUS.md,
        color: '#fff',
        cursor: project ? 'pointer' : 'not-allowed',
        opacity: project ? 1 : 0.5,
      }}
    >
      {isExporting ? '⏳ Exporting...' : '⬇️ Export Project'}
    </button>
  );
}
```

- [ ] **Step 32: Commit**

```bash
git add frontend/src/components/builder/export/ExportButton.tsx
git commit -m "feat(builder): add ExportButton with ZIP generation and README"
```

---

## Chunk 6: Mode Switcher & Integration

**Files:**
- Create: `frontend/src/components/builder/ModeSwitcher.tsx`
- Modify: `frontend/src/pages/AssistantPage.tsx`

### Task 16: Mode Switcher Component

**Create:** `frontend/src/components/builder/ModeSwitcher.tsx`

- [ ] **Step 33: Write mode switcher**

```typescript
import { useBuilderStore } from '../../stores/builderStore';
import type { BuilderMode } from '../../types/builder';

interface ModeSwitcherProps {
  currentMode: BuilderMode;
}

export default function ModeSwitcher({ currentMode }: ModeSwitcherProps) {
  const { setMode, project, reset } = useBuilderStore();

  const modes: { id: BuilderMode; label: string; icon: string }[] = [
    { id: 'chat', label: 'Chat', icon: '💬' },
    { id: 'plan', label: 'Plan', icon: '📋' },
    { id: 'build', label: 'Build', icon: '🔨' },
  ];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '12px 20px',
        background: 'rgba(0,0,0,0.3)',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        gap: '8px',
      }}
    >
      {modes.map((mode) => {
        const isActive = mode.id === currentMode;
        const isDisabled = mode.id === 'build' && !project;
        const isPlanDisabled = mode.id === 'plan' && !project;

        return (
          <button
            key={mode.id}
            onClick={() => !isDisabled && !isPlanDisabled && setMode(mode.id)}
            disabled={isDisabled || isPlanDisabled}
            style={{
              padding: '8px 16px',
              background: isActive ? '#2563eb' : 'transparent',
              border: isActive ? 'none' : '1px solid rgba(255,255,255,0.2)',
              borderRadius: '6px',
              color: isActive ? '#fff' : isDisabled || isPlanDisabled ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.7)',
              cursor: isDisabled || isPlanDisabled ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>{mode.icon}</span>
            <span>{mode.label}</span>
          </button>
        );
      })}

      {project && (
        <button
          onClick={() => {
            if (confirm('Start over? This will clear your project.')) {
              reset();
            }
          }}
          style={{
            marginLeft: 'auto',
            padding: '8px 16px',
            background: 'transparent',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: '6px',
            color: 'rgba(255,255,255,0.5)',
            cursor: 'pointer',
          }}
        >
          🗑️ Clear Project
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 34: Commit**

```bash
git add frontend/src/components/builder/ModeSwitcher.tsx
git commit -m "feat(builder): add ModeSwitcher component"
```

### Task 17: Integrate with AssistantPage

**Modify:** `frontend/src/pages/AssistantPage.tsx`

- [ ] **Step 35: Replace with ModeRouter**

```typescript
// Replace the entire AssistantPage content with ModeRouter
import ModeRouter from '../components/builder/ModeRouter';

export default function AssistantPage() {
  return (
    <div style={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}>
      <ModeRouter />
    </div>
  );
}
```

- [ ] **Step 36: Update imports and remove old code**

Remove the old chat logic that's now in ChatInterface component.

- [ ] **Step 37: Commit**

```bash
git add frontend/src/pages/AssistantPage.tsx
git commit -m "refactor(builder): integrate ModeRouter into AssistantPage"
```

---

## Chunk 7: Backend - Project Generation

**Files:**
- Create: `backend/app/schemas/builder.py`
- Modify: `backend/app/routes/assistant.py`

### Task 18: Pydantic Schemas

**Create:** `backend/app/schemas/builder.py`

- [ ] **Step 38: Write builder schemas**

```python
from pydantic import BaseModel
from typing import List, Optional


class PlanTaskSchema(BaseModel):
    id: str
    description: str
    estimatedMinutes: int
    completed: bool = False


class ProjectPlanSchema(BaseModel):
    id: str
    name: str
    description: str
    targetTrack: Optional[str] = None
    estimatedHours: float
    techStack: List[str]
    tasks: List[PlanTaskSchema]
    stretchGoals: List[str]


class GeneratedFileSchema(BaseModel):
    path: str
    name: str
    content: str
    language: str


class GenerateProjectRequest(BaseModel):
    plan: ProjectPlanSchema
    projectType: str = "web"


class GenerateProjectResponse(BaseModel):
    files: List[GeneratedFileSchema]
    readme: str
```

- [ ] **Step 39: Commit**

```bash
git add backend/app/schemas/builder.py
git commit -m "feat(builder): add Pydantic schemas for builder API"
```

### Task 19: Project Generation Endpoint

**Modify:** `backend/app/routes/assistant.py`

- [ ] **Step 40: Add generate-project endpoint**

```python
from app.schemas.builder import GenerateProjectRequest, GenerateProjectResponse, GeneratedFileSchema

@router.post("/generate-project", response_model=GenerateProjectResponse)
async def generate_project(
    request: GenerateProjectRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate starter files for a project based on plan."""

    # Build prompt for code generation
    system_prompt = f"""You are a code generator for hackathon projects.
Generate starter files for this project:

Name: {request.plan.name}
Description: {request.plan.description}
Tech Stack: {', '.join(request.plan.techStack)}

Generate files that provide a working MVP foundation.
Return as JSON with file list including path, name, content, and language."""

    # Generate with LLM
    files_json = await llm_client.generate_structured_output(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Generate the starter files."},
        ],
        output_schema=GenerateProjectResponse,
    )

    return files_json
```

- [ ] **Step 41: Commit**

```bash
git add backend/app/routes/assistant.py
git commit -m "feat(builder): add project generation endpoint"
```

---

## Chunk 8: Frontend Integration & Polish

### Task 20: Frontend Service Functions

**Create:** `frontend/src/services/builder.ts`

- [ ] **Step 42: Write builder API functions**

```typescript
import type { ProjectPlan, ProjectFile } from '../types/builder';

const BASE = import.meta.env.VITE_API_URL || '/api';

export async function generatePlan(description: string): Promise<{ plan: ProjectPlan }> {
  const res = await fetch(`${BASE}/assistant/generate-plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
    body: JSON.stringify({ description }),
  });

  if (!res.ok) throw new Error('Failed to generate plan');
  return res.json();
}

export async function generateProject(plan: ProjectPlan): Promise<{ files: ProjectFile[]; readme: string }> {
  const res = await fetch(`${BASE}/assistant/generate-project`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
    body: JSON.stringify({ plan, projectType: 'web' }),
  });

  if (!res.ok) throw new Error('Failed to generate project');
  return res.json();
}
```

- [ ] **Step 43: Commit**

```bash
git add frontend/src/services/builder.ts
git commit -m "feat(builder): add builder API service functions"
```

### Task 21: Connect Plan to Project Generation

**Modify:** `frontend/src/components/builder/plan/PlanDisplay.tsx` and store

- [ ] **Step 44: Update store to handle generated files**

```typescript
// Add to builderStore.ts
setProjectFiles: (files: ProjectFile[]) => {
  const { project } = get();
  if (!project) return;
  set({ project: { ...project, files } });
},
```

- [ ] **Step 45: Update PlanDisplay to generate files**

```typescript
import { generateProject } from '../../../services/builder';

const handleAcceptPlan = async (plan: ProjectPlan) => {
  setIsGenerating(true);
  try {
    const { files, readme } = await generateProject(plan);
    // Add README to files
    const readmeFile: ProjectFile = {
      id: `file_readme`,
      path: 'README.md',
      name: 'README.md',
      content: readme,
      language: 'markdown',
      lastModified: new Date(),
      isDirty: false,
    };
    setProjectFiles([...files, readmeFile]);
    setMode('build');
  } catch (error) {
    alert('Failed to generate project. Please try again.');
  } finally {
    setIsGenerating(false);
  }
};
```

- [ ] **Step 46: Commit**

```bash
git add frontend/src/stores/builderStore.ts frontend/src/components/builder/plan/PlanDisplay.tsx
git commit -m "feat(builder): connect plan acceptance to project generation"
```

---

## Chunk 9: Testing & Validation

### Task 22: Manual Testing Checklist

- [ ] **Step 47: Test mode transitions**

Test cases:
1. Start in Chat mode ✓
2. Type "I want to build a weather app" → See build intent detection ✓
3. Click "Create Plan" → Enter Plan mode ✓
4. See generated plan with tasks ✓
5. Click "Accept & Build" → Enter Build mode with files ✓
6. Click "Chat" tab → Return to Chat mode, project preserved ✓
7. Click "Build" tab → Back to Build mode with files intact ✓
8. Click "Clear Project" → Reset to empty state ✓

- [ ] **Step 48: Test file operations**

Test cases:
1. Click file in explorer → Opens in editor ✓
2. Edit file → Shows "Modified" indicator ✓
3. Create new file → Appears in explorer ✓
4. Delete file → Removed from explorer ✓
5. Preview updates when HTML changes ✓

- [ ] **Step 49: Test export**

Test cases:
1. Click Export → Downloads ZIP ✓
2. ZIP contains all files ✓
3. README.md is generated ✓
4. File names correct ✓

- [ ] **Step 50: Final commit**

```bash
git commit -m "feat(builder): complete builder mode implementation

- Chat/Plan/Build three-mode system
- Intent detection for build transitions
- Monaco editor with file explorer
- Live preview for web projects
- ZIP export with README generation
- Session persistence with Zustand"
```

---

## Appendix: Quick Reference

### File Structure

```
frontend/src/
├── types/builder.ts              # TypeScript types
├── stores/builderStore.ts        # Zustand store
├── services/builder.ts           # API calls
├── components/builder/
│   ├── ModeRouter.tsx            # Route between modes
│   ├── ModeSwitcher.tsx          # Mode toggle UI
│   ├── modes/
│   │   ├── ChatMode.tsx          # Chat mode wrapper
│   │   ├── PlanMode.tsx          # Plan mode wrapper
│   │   └── BuildMode.tsx         # Build mode (IDE)
│   ├── chat/
│   │   └── ChatInterface.tsx     # Chat UI + intent detection
│   ├── plan/
│   │   ├── PlanDisplay.tsx       # Plan viewer
│   │   └── PlanGenerator.tsx     # Plan creation UI
│   ├── files/
│   │   └── FileExplorer.tsx      # File tree
│   ├── editor/
│   │   └── CodeEditor.tsx        # Monaco wrapper
│   ├── preview/
│   │   └── PreviewPanel.tsx      # Live preview
│   └── export/
│       └── ExportButton.tsx      # ZIP export

backend/app/
├── schemas/builder.py            # Pydantic schemas
├── routes/assistant.py           # New endpoints
└── assistant/context_builder.py  # Intent detection
```

### Environment Variables

No new env vars needed. Uses existing:
- `VITE_API_URL` for frontend
- `HACKVERIFY_POOLSIDE_API_KEY` for LLM

### Dependencies

```bash
# Frontend
npm install @monaco-editor/react monaco-editor jszip zustand

# Backend (already have)
# fastapi, pydantic, etc.
```

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-04-assistant-builder-mode.md`. Ready to execute?**
