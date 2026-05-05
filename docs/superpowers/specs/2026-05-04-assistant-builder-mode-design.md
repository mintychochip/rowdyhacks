# AI Assistant Builder Mode Design

**Date:** 2026-05-04
**Feature:** AI Assistant with Chat/Plan/Build Modes
**Context:** 6-hour RowdyHacks hackathon

---

## 1. Overview

The AI Assistant evolves from a Q&A chatbot into a **hackathon project accelerator** with three distinct modes:

| Mode | Purpose | User Flow |
|------|---------|-----------|
| **💬 Chat** | Freeform discussion, hackathon Q&A, brainstorming | Start here, always available |
| **📋 Plan** | AI generates structured project roadmap | Triggered when build intent detected |
| **🔨 Build** | Full IDE with code editor, file explorer, live preview | Accept plan → start building |

**Key Innovation:** Seamless pivoting between modes. Users can chat about their project, switch to build mode, realize they need to replan, pivot back, then return to building - all without losing context.

---

## 2. Architecture

### 2.1 Mode State Machine

```
┌──────────┐
│   Chat   │◄────────────────────────┐
│  (start) │                         │
└────┬─────┘                         │
     │ detect "I want to build..."   │
     ▼                                │
┌──────────┐     Accept Plan         │
│   Plan   │────────────────►┌───────┴───┐
│  Mode    │                 │   Build   │
└────┬─────┘◄────────────────│   Mode    │
     │  Modify Plan          └───────────┘
     └───────────────────────►
```

**Rules:**
- Chat mode is always accessible from Plan/Build (back button)
- Plan mode can be re-entered from Build to adjust scope
- Build mode requires accepting or creating a plan first

### 2.2 Intent Detection (Chat → Plan Transition)

**Triggers (case-insensitive patterns):**
- "I want to build/create/make..."
- "Generate a prototype for..."
- "Help me code..."
- "I have an idea for..."
- User selects hackathon tracks + describes project
- "Can you help me with [tech stack]?"

**AI Response:**
```
I can help you build this! Want me to create a project plan first,
or jump straight into coding?

[ 📋 Create Plan ]  [ 🔨 Start Building ]  [ 💬 Keep Chatting ]
```

---

## 3. Mode Specifications

### 3.1 Chat Mode (Default)

**UI:** Current assistant UI - sidebar with conversations, main chat area.

**Features:**
- Normal Q&A about hackathon (tracks, rules, logistics)
- Brainstorming project ideas
- Tool calls available (web search, calculator, FAQ query)
- Intent detection for plan/build transitions

### 3.2 Plan Mode

**UI Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ 💬 Chat │ 📋 Plan Mode (active) │ 🔨 Build Mode        │
├───────────────────┬─────────────────────────────────────┤
│                   │  📋 PROJECT PLAN                      │
│ Chat continues    │                                       │
│ (can ask about    │  🎯 Project Summary                  │
│  the plan)        │  ─────────────────                    │
│                   │  Name: Smart Plant Monitor            │
│                   │  Target Track: Best Hardware Hack     │
│                   │  Est. Time: 4 hours                   │
│                   │                                       │
│                   │  📦 Tech Stack                        │
│                   │  • Arduino + DHT22 sensor             │
│                   │  • Python Flask backend               │
│                   │  • HTML/CSS/JS frontend               │
│                   │                                       │
│                   │  📝 MVP Tasks                         │
│                   │  ☐ Wire DHT22 → Arduino               │
│                   │  ☐ Read temperature/humidity          │
│                   │  ☐ Create dashboard UI                │
│                   │  ☐ Connect sensor → web display       │
│                   │                                       │
│                   │  🎁 Stretch Goals                     │
│                   │  • Email alerts when dry              │
│                   │  • Historical data graph              │
│                   │                                       │
│                   │  [ 🚀 Accept & Build ]                │
│                   │  [ ✏️ Edit Plan ]                     │
│                   │  [ 🔨 Skip to Build ]                 │
└───────────────────┴─────────────────────────────────────┘
```

**Plan Generation Prompt:**
The AI uses a structured prompt to generate plans:
- Project name (based on user description)
- Recommended prize tracks (from indexed hackathon data)
- Tech stack recommendation
- MVP task list (time-boxed for 6-hour hackathon)
- Stretch goals (if time permits)
- Judging criteria alignment

**Editable Fields:**
Users can click to edit any field before accepting the plan.

### 3.3 Build Mode

**UI Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ 💬 Chat │ 📋 Plan │ 🔨 Build Mode (active) │ ⬇️ Export │
├──────────┬──────────────────────────────┬─────────────┤
│          │                              │             │
│ 📁 FILES │   Monaco Editor              │ 🌐 Preview  │
│          │   (VS Code-style)            │ Panel       │
│ 📄 app   │                              │             │
│   .py    │   1 import flask             │ [Live web  │
│ 📄 index │   2 from sensor import read  │  preview   │
│   .html  │   3                          │  or        │
│ 📄 style │   4 app = Flask(__name__)    │  circuit   │
│   .css   │   5                          │  diagram]  │
│ 📄 README│   6 @app.route('/api/data')  │             │
│   .md    │   7 def get_data():          │             │
│          │   8     return read_sensor() │             │
│          │                              │             │
│ [+ New]  │  [💬 Ask AI to edit... ]    │ [🔄][🌐]   │
│          │                              │             │
├──────────┴──────────────────────────────┴─────────────┤
│ 💬 Chat continues below...                            │
│ User: "Add error handling to the sensor read"          │
│ AI: *edits app.py* ✅ Updated                         │
└─────────────────────────────────────────────────────────┘
```

**Components:**

1. **File Explorer (Left)**
   - Tree view of project files
   - Create new file/folder
   - Delete/rename files
   - Click to open in editor

2. **Monaco Editor (Center)**
   - VS Code's editor component
   - Syntax highlighting for all common languages
   - Auto-completion
   - Error highlighting
   - Multiple tabs for open files

3. **Preview Panel (Right)**
   - **Web projects:** Live iframe preview (auto-refreshes on save)
   - **Arduino projects:** Circuit wiring diagram + serial output sim
   - **Python scripts:** Terminal output simulation
   - **Other:** Rendered markdown README

4. **Chat Integration (Bottom)**
   - Persistent chat input
   - AI can read/write files based on chat commands
   - Shows file diffs when AI makes edits

---

## 4. File Management

### 4.1 Storage Strategy

**In-Memory + Session Storage (MVP):**
- Files stored in browser memory during session
- Session storage for recovery (if user refreshes)
- No backend persistence (keeps it simple for 6-hour hack)

**File Structure:**
```typescript
interface ProjectFile {
  id: string;
  path: string;           // "src/app.py" or "index.html"
  name: string;
  content: string;
  language: string;       // "python", "javascript", "html"
  lastModified: Date;
  isDirty: boolean;      // unsaved changes
}

interface Project {
  id: string;
  name: string;
  mode: 'web' | 'arduino' | 'python' | 'other';
  files: ProjectFile[];
  plan: ProjectPlan;     // Reference to accepted plan
  createdAt: Date;
}
```

### 4.2 Project Types & Templates

**Auto-detected from conversation context:**

| Type | File Templates | Preview |
|------|---------------|---------|
| **Web App** | index.html, style.css, script.js | Live iframe |
| **Web + Backend** | index.html, style.css, app.py (Flask) | Split: terminal + web |
| **Arduino** | sketch.ino, wiring.txt, README.md | Circuit diagram view |
| **Chrome Extension** | manifest.json, popup.html, popup.js | Mock popup UI |
| **Discord Bot** | bot.py, .env.example, README.md | Message flow diagram |
| **Data Viz** | analysis.py, data.csv, chart.html | Chart preview |
| **Game (Phaser)** | index.html, game.js, assets/ | Game canvas |

---

## 5. AI Integration in Build Mode

### 5.1 Chat-to-Code Commands

Users can chat naturally, AI understands file operations:

| User Says | AI Action |
|-----------|-----------|
| "Add a navbar" | Creates/edits HTML/CSS for navbar |
| "Make this responsive" | Adds media queries to CSS |
| "Connect the sensor to the backend" | Edits both Arduino and Python files |
| "Why isn't this working?" | Explains code, suggests fix |
| "Add error handling" | Wraps code in try/catch |
| "What's next?" | Suggests next task from plan |

### 5.2 File Edit Flow

```
User: "Add a dark mode toggle"
         ↓
AI analyzes: needs JS toggle + CSS variables
         ↓
AI shows: [Proposed Changes]
         • index.html: +button element
         • style.css: +dark mode variables
         • script.js: +toggle function
         ↓
User clicks: [✅ Accept] [❌ Reject] [✏️ Modify]
         ↓
Files updated → Preview refreshes → Confirmation shown
```

### 5.3 Context Awareness

AI maintains context across modes:
- Remembers plan goals when editing code
- Knows which prize tracks user is targeting
- Understands time constraints (6-hour hackathon)
- References indexed hackathon data (tracks, criteria)

---

## 6. Export & Delivery

### 6.1 Export Options

**Primary:** ZIP Download
- Packages all project files
- Includes README.md with setup instructions
- Flat or structured folder format

**Secondary (Future):**
- GitHub: Push to new repo (requires auth)
- CodeSandbox: Open project there (API integration)
- Vercel: Deploy instantly (requires auth)

### 6.2 README Generation

Auto-generated README.md for exported projects:
```markdown
# [Project Name]

Generated for RowdyHacks 2026
Target Track: [Track Name]

## Quick Start

[Setup instructions specific to project type]

## Files

- index.html - Main frontend
- app.py - Flask backend
- ...

## Judging Criteria Alignment

This project targets [criteria X] by [explanation]
```

---

## 7. Technical Implementation

### 7.1 Frontend Components

| Component | Library/Approach |
|-----------|-----------------|
| Code Editor | Monaco Editor (VS Code's editor) |
| File Tree | Custom React component |
| Preview Panel | iframe (web) / canvas (circuit) |
| State Management | Zustand or React Context |
| Styling | Existing theme.ts colors |

### 7.2 Backend Changes

**New API Endpoints:**
- `POST /assistant/generate-plan` - Create project plan from chat
- `POST /assistant/generate-project` - Generate starter files
- `POST /assistant/edit-file` - AI edits based on chat command

**Modified Endpoints:**
- `POST /assistant/chat` - Add intent detection
- `GET /assistant/stream/{id}` - Support file generation streaming

### 7.3 AI Prompting Strategy

**Plan Generation Prompt:**
```
You are creating a hackathon project plan. Given the user's idea,
generate a structured plan that fits a 6-hour timeline.

Include:
1. Concise project name
2. Recommended prize tracks (from available tracks)
3. Tech stack recommendation
4. MVP task list (4-5 tasks, 4 hours total)
5. Stretch goals (2-3 ideas, 1-2 hours)
6. Judging criteria alignment

Format as structured JSON for the UI.
```

**File Edit Prompt:**
```
User wants to modify their project. Current files: [list]
Requested change: "{user message}"

Generate the exact file changes needed.
Return as: {file_path: string, new_content: string}[]
```

---

## 8. Error Handling

### 8.1 Graceful Degradation

| Scenario | Fallback |
|----------|----------|
| Monaco Editor fails to load | Plain textarea with syntax highlighting |
| Preview iframe errors | Show error message + console output |
| AI generation fails | Show partial results + retry button |
| Session storage full | Warn user + offer export |
| File too large | Warn + offer split into multiple files |

### 8.2 Recovery

- Auto-save to session storage every 30 seconds
- "Recover session" option if browser crashes
- Version history (last 5 edits per file)

---

## 9. Testing Strategy

### 9.1 Test Cases

**Mode Transitions:**
- [ ] Chat → Plan transition on intent detection
- [ ] Plan → Build transition on accept
- [ ] Build → Chat transition (back button)
- [ ] Build → Plan transition (modify plan)
- [ ] Plan → Chat transition

**File Operations:**
- [ ] Create new file
- [ ] Edit file content
- [ ] Delete file
- [ ] Rename file
- [ ] Auto-save works
- [ ] Export generates valid ZIP

**AI Integration:**
- [ ] AI generates plan from chat
- [ ] AI edits file from chat command
- [ ] AI reads current files for context
- [ ] Preview updates after AI edit

**Project Types:**
- [ ] Web project preview works
- [ ] Arduino project shows wiring guide
- [ ] Python project shows terminal output

---

## 10. MVP Scope (For Initial Release)

### Included (Phase 1)
- ✅ Chat mode with intent detection
- ✅ Plan mode with structured roadmap
- ✅ Build mode with file explorer + Monaco editor
- ✅ Web project type (HTML/CSS/JS)
- ✅ Live preview for web projects
- ✅ ZIP export
- ✅ Chat-to-code AI integration

### Excluded (Future Phases)
- ⏸ Arduino circuit diagram viewer (show code + text guide instead)
- ⏸ Python terminal simulation
- ⏸ GitHub/Vercel/CodeSandbox integration
- ⏸ Real-time collaboration (multiple users)
- ⏸ Version control (git history)

---

## 11. Success Criteria

The feature is successful if:
1. Users can go from "I have an idea" to "running prototype" in under 2 hours
2. 80% of users who start a plan complete the export
3. Average chat-to-build transition time < 5 minutes
4. Users can successfully demo their project at judging
5. Teams report the assistant "actually helped build something" vs just "answered questions"

---

## 12. Open Questions

1. Should we support multiple projects per conversation, or one project per conversation?
2. How do we handle dependencies (npm packages, Python requirements)?
3. Should we include a "deploy" button for instant hosting, or keep it local-only?
4. How do we prevent users from generating malicious code in the preview iframe?

---

**Next Step:** Implementation planning once design is approved.
