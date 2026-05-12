# Floating Chat Bot + OpenAI-Compatible LLM Provider Implementation Plan

> **For agentic workers:** REQUIRED: Use @superpowers:subagent-driven-development or @superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the full-page `/assistant` route with a minimizable floating chat bot and make the LLM backend configurable to work with any OpenAI-compatible API endpoint.

**Architecture:** Backend: refactor `LLMClient` to accept configurable `base_url`/`api_key`/`model`, add `get_llm_client()` factory with precedence rules, update `POST /api/llm/chat` to use resolved model. Frontend: delete dead full-page assistant code, add `compact` prop to `LinearChatInput`, add `updateSystemPrompt`/`setMessages`/`stop` to `AgentLoop`, build `FloatingChatBot` component mounted inside `<Layout>`.

**Tech Stack:** FastAPI + Pydantic Settings, React + TypeScript + Vite, OpenAI-compatible chat completions

---

## Chunk 1: Backend LLM Provider Abstraction

### Task 1: Add generic LLM config fields

**Files:**
- Modify: `backend/app/config.py:50-83`

- [ ] **Step 1: Add `llm_base_url` and `llm_model` fields**

Insert after line 57 (`llm_api_key` description closing brace):

```python
    llm_base_url: str = Field(
        default="",
        description="Generic LLM API base URL (OpenAI-compatible). Falls back to poolside_api_url if not set.",
    )
    llm_model: str = Field(
        default="",
        description="Generic LLM model name. Falls back to assistant_model if not set.",
    )
```

- [ ] **Step 2: Add `get_llm_key()` method to Settings**

Insert after `get_poolside_key()` (line 202):

```python
    def get_llm_key(self) -> str:
        """Return the generic LLM API key, falling back to Poolside key.

        Behavior:
        1. Return llm_api_key if it is truthy.
        2. Otherwise, return poolside_api_key as the fallback.

        Raises: None
        Side Effects: None (read-only).
        Dependencies: None.
        Consumers: get_llm_client factory.
        """
        return self.llm_api_key or self.poolside_api_key
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat(config): add generic llm_base_url and llm_model settings"
```

---

### Task 2: Refactor LLMClient and add get_llm_client factory

**Files:**
- Modify: `backend/app/assistant/llm.py`

- [ ] **Step 1: Replace module-level constants and __init__**

Replace lines 14-42 with:

```python
# Default values from settings (for backward-compatible global singleton)
_DEFAULT_API_URL = settings.poolside_api_url
_DEFAULT_API_KEY = settings.get_poolside_key()
_DEFAULT_MODEL = settings.assistant_model


def get_llm_client(model: str | None = None) -> "LLMClient":
    """Factory that constructs an LLMClient with resolved settings.

    Precedence rules:
    1. llm_base_url if non-empty, else poolside_api_url.
    2. API key: llm_api_key if set, else poolside_api_key.
    3. Model: the passed `model` arg if provided; otherwise llm_model if non-empty, else assistant_model.
    """
    base_url = settings.llm_base_url or settings.poolside_api_url
    api_key = settings.get_llm_key()
    resolved_model = model or settings.llm_model or settings.assistant_model
    return LLMClient(base_url=base_url, api_key=api_key, model=resolved_model)


class LLMClient:
    """Client for OpenAI-compatible LLM chat completions and agentic tool-calling loops.

    Provides non-streaming and streaming chat completion methods, plus an
    iterative tool-calling loop that lets the model invoke registered
    tools until no more tool calls are requested.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
        """Initialize the LLM client with API endpoint, key, and default model.

        Behavior:
        1. Read the API URL, API key, and default model from parameters or application settings.
        2. Store them as instance attributes for subsequent requests.

        Raises: None
        Side Effects: None (read-only, no state mutation beyond self).
        Dependencies: app.config.settings.
        Consumers: LLMClient singleton instantiation.
        """
        self.api_url = base_url or _DEFAULT_API_URL
        self.api_key = api_key or _DEFAULT_API_KEY
        self.model = model or _DEFAULT_MODEL
```

- [ ] **Step 2: Update debug logging in chat_completion_stream**

In `chat_completion_stream`, replace the debug prints (lines 138-142 in original) with:

```python
        print(f"[DEBUG LLM] API URL: {self.api_url}")
        print(f"[DEBUG LLM] Model: {self.model}")
        print(f"[DEBUG LLM] Messages count: {len(messages)}")
        print(f"[DEBUG LLM] Tools count: {len(tools) if tools else 0}")
        print(f"[DEBUG LLM] Payload preview: {json.dumps(payload, indent=2)[:500]}")
```

- [ ] **Step 3: Update error yield in chat_completion_stream**

Replace line 156 (original) with:

```python
                        yield json.dumps({"error": f"LLM API error {response.status_code}: {error_text[:200]}"})
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/assistant/llm.py
git commit -m "feat(llm): refactor LLMClient to accept configurable base_url, api_key, model; add get_llm_client factory"
```

---

### Task 3: Update POST /api/llm/chat to use resolved model

**Files:**
- Modify: `backend/app/routes/assistant.py`

- [ ] **Step 1: Update imports**

Add `from app.config import settings` at the top-level imports (if not already present). Also replace:

```python
from app.assistant.llm import llm_client
```

with:

```python
from app.assistant.llm import llm_client, get_llm_client
```

- [ ] **Step 2: Replace model hardcoding in llm_chat_proxy**

Find lines 1056-1062 (approximately) in `llm_chat_proxy`:

```python
    model = "poolside/m.1" if request.model == "thinking" else "poolside/laguna-xs.2"

    try:
        response = await llm_client.chat_completion(
```

Replace with:

```python
    if request.model == "fast":
        model = settings.assistant_fast_model or settings.llm_model
    elif request.model == "thinking":
        model = settings.assistant_thinking_model or settings.llm_model
    else:
        model = settings.llm_model

    if not model:
        raise HTTPException(status_code=500, detail="LLM provider not configured.")

    client = get_llm_client(model)

    try:
        response = await client.chat_completion(
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/assistant.py
git commit -m "feat(assistant): use resolved model and get_llm_client in llm_chat_proxy"
```

---

### Task 4: Add backend unit tests

**Files:**
- Create: `backend/tests/test_llm_client.py`

- [ ] **Step 1: Write test file**

```python
import pytest
from unittest.mock import patch

from app.assistant.llm import LLMClient, get_llm_client
from app.config import settings


class TestGetLlmClient:
    """Test the get_llm_client factory and its precedence rules."""

    def test_get_llm_client_uses_passed_model(self):
        """When a model is passed, it should be used directly."""
        client = get_llm_client(model="gpt-4")
        assert client.model == "gpt-4"

    def test_get_llm_client_resolves_base_url(self):
        """llm_base_url should take precedence over poolside_api_url."""
        with patch.object(settings, "llm_base_url", "https://custom.api/v1"):
            with patch.object(settings, "poolside_api_url", "https://poolside.ai/v1"):
                client = get_llm_client()
                assert client.api_url == "https://custom.api/v1"

    def test_get_llm_client_falls_back_to_poolside_url(self):
        """When llm_base_url is empty, fall back to poolside_api_url."""
        with patch.object(settings, "llm_base_url", ""):
            with patch.object(settings, "poolside_api_url", "https://poolside.ai/v1"):
                client = get_llm_client()
                assert client.api_url == "https://poolside.ai/v1"

    def test_get_llm_client_resolves_api_key(self):
        """llm_api_key should take precedence over poolside_api_key."""
        with patch.object(settings, "llm_api_key", "custom-key"):
            with patch.object(settings, "poolside_api_key", "poolside-key"):
                client = get_llm_client()
                assert client.api_key == "custom-key"

    def test_get_llm_client_falls_back_to_poolside_key(self):
        """When llm_api_key is empty, fall back to poolside_api_key."""
        with patch.object(settings, "llm_api_key", ""):
            with patch.object(settings, "poolside_api_key", "poolside-key"):
                client = get_llm_client()
                assert client.api_key == "poolside-key"

    def test_get_llm_client_resolves_model_from_llm_model(self):
        """When no model arg is passed, use llm_model if set."""
        with patch.object(settings, "llm_model", "gpt-3.5-turbo"):
            with patch.object(settings, "assistant_model", "old-model"):
                client = get_llm_client()
                assert client.model == "gpt-3.5-turbo"

    def test_get_llm_client_falls_back_to_assistant_model(self):
        """When llm_model is empty, fall back to assistant_model."""
        with patch.object(settings, "llm_model", ""):
            with patch.object(settings, "assistant_model", "fallback-model"):
                client = get_llm_client()
                assert client.model == "fallback-model"


class TestLLMClientConstruction:
    """Test that LLMClient uses passed parameters correctly."""

    def test_llm_client_uses_passed_params(self):
        client = LLMClient(base_url="https://custom.api", api_key="custom-key", model="custom-model")
        assert client.api_url == "https://custom.api"
        assert client.api_key == "custom-key"
        assert client.model == "custom-model"

    def test_llm_client_falls_back_to_defaults(self):
        client = LLMClient()
        assert client.api_url == settings.poolside_api_url
        assert client.api_key == settings.get_poolside_key()
        assert client.model == settings.assistant_model
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_llm_client.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_llm_client.py
git commit -m "test(llm): add unit tests for get_llm_client and LLMClient construction"
```

---

## Chunk 2: Frontend AgentLoop Additions

### Task 5: Add updateSystemPrompt and setMessages to AgentLoop

**Files:**
- Modify: `frontend/src/agent/AgentLoop.ts`

- [ ] **Step 1: Add methods after constructor**

Insert after the `constructor` block (after line 16), before `send()`:

```typescript
  /** Update the system prompt dynamically (e.g., for per-message RAG context) */
  updateSystemPrompt(prompt: string): void {
    this.config.systemPrompt = prompt;
  }

  /** Replace the internal message list (e.g., after loading history) */
  setMessages(messages: AgentMessage[]): void {
    this.messages = [...messages];
  }
```

- [ ] **Step 2: Verify `stop()` method already exists**

The `stop()` method is already present at lines 115-119. No changes needed.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/agent/AgentLoop.ts
git commit -m "feat(agent): add updateSystemPrompt and setMessages to AgentLoop"
```

---

## Chunk 3: Frontend Cleanup

### Task 6: Remove /assistant route and dead code

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Delete: `frontend/src/pages/AssistantPage.tsx`
- Delete: `frontend/src/components/assistant/ConversationSidebar.tsx`
- Delete: `frontend/src/components/assistant/StandaloneEditor.tsx`
- Delete: `frontend/src/components/assistant/NewFileDialog.tsx`

- [ ] **Step 1: Remove AssistantPage import and route from App.tsx**

In `frontend/src/App.tsx`, remove:
- Line 10: `import AssistantPage from './pages/AssistantPage';`
- Line 62: `<Route path="/assistant" element={<AssistantPage />} />`

- [ ] **Step 2: Remove "AI Assistant" nav item from Layout.tsx**

In `frontend/src/components/Layout.tsx`:
- Remove lines 40-48: The `SparklesIcon` component definition (the entire `const SparklesIcon = () => (...)` block).
- Remove line 149: `'AI Assistant': <SparklesIcon />,` from `NAV_ICONS`
- Remove line 210: `{ to: '/assistant', label: 'AI Assistant', roles: ['organizer', 'participant', 'judge'] },` from `rawNav`

- [ ] **Step 3: Delete dead code files**

```bash
rm frontend/src/pages/AssistantPage.tsx
rm frontend/src/components/assistant/ConversationSidebar.tsx
rm frontend/src/components/assistant/StandaloneEditor.tsx
rm frontend/src/components/assistant/NewFileDialog.tsx
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx
git rm frontend/src/pages/AssistantPage.tsx frontend/src/components/assistant/ConversationSidebar.tsx frontend/src/components/assistant/StandaloneEditor.tsx frontend/src/components/assistant/NewFileDialog.tsx
git commit -m "refactor(assistant): remove full-page /assistant route and dead components"
```

---

## Chunk 4: Frontend Floating Bot

### Task 7: Add `compact` prop to LinearChatInput

**Files:**
- Modify: `frontend/src/components/assistant/LinearChatInput.tsx`

- [ ] **Step 1: Update interface and component signature**

Replace the interface and default export:

```typescript
interface LinearChatInputProps {
  onSend: (message: string, model: ModelType) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
  compact?: boolean;
}

export default function LinearChatInput({
  onSend,
  onStop,
  disabled,
  isStreaming,
  placeholder = 'Type a message...',
  compact = false,
}: LinearChatInputProps) {
```

- [ ] **Step 2: Update container styles for compact mode**

Replace the outer container div (lines 69-76) with:

```tsx
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: compact ? undefined : 720,
        margin: '0 auto',
      }}
    >
```

- [ ] **Step 3: Hide model selector and hint when compact**

Wrap the model selector section (lines 130-194) with a conditional:

```tsx
          {/* Left: Model Selector */}
          {!compact && (
            <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.xs }}>
              ...existing model selector buttons...
            </div>
          )}
          {compact && <div />}
```

- [ ] **Step 4: Update textarea maxHeight and auto-resize for compact**

In the textarea style, change `maxHeight`:

```tsx
            maxHeight: compact ? 80 : 200,
```

In the auto-resize `useEffect` (lines 44-49), change:

```tsx
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, compact ? 80 : 200)}px`;
    }
  }, [message, compact]);
```

- [ ] **Step 5: Hide bottom hint when compact**

Wrap the bottom hint div (lines 274-306) with a conditional:

```tsx
      {!compact && (
        <div
          style={{
            textAlign: 'center',
            marginTop: SPACE.sm,
            fontSize: 12,
            color: TEXT_MUTED,
            height: 18,
            lineHeight: '18px',
            letterSpacing: '-0.01em',
          }}
        >
          ...existing hint content...
        </div>
      )}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/assistant/LinearChatInput.tsx
git commit -m "feat(ui): add compact prop to LinearChatInput for floating bot"
```

---

### Task 8: Update chatLog to return conversation_id

**Files:**
- Modify: `frontend/src/services/assistant.ts`

- [ ] **Step 1: Change chatLog return type and body**

Replace the `chatLog` function with:

```typescript
export async function chatLog(
  messages: Array<{ role: string; content: string }>,
  conversationId?: string
): Promise<{ conversation_id?: string }> {
  const res = await fetch(`${BASE}/assistant/chat-log`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TOKEN()}`,
    },
    body: JSON.stringify({ messages, conversation_id: conversationId }),
  });

  if (!res.ok) throw new Error('Failed to sync chat log');
  return res.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/assistant.ts
git commit -m "feat(api): update chatLog to return conversation_id"
```

---

### Task 9: Build FloatingChatBot component

**Dependencies:** Task 5 (AgentLoop additions), Task 7 (LinearChatInput compact), Task 8 (chatLog returns conversation_id)

**Files:**
- Create: `frontend/src/components/assistant/FloatingChatBot.tsx`

- [ ] **Step 1: Write the component**

```tsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { AgentLoop } from '../../agent/AgentLoop';
import { buildSystemPrompt } from '../../agent/context';
import type { AgentMessage, AgentEvent } from '../../agent/types';
import {
  getConversations,
  getConversation,
  getAvailableTools,
  chatLog,
  unwrapTool,
} from '../../services/assistant';
import ChatMessage from './ChatMessage';
import LinearChatInput from './LinearChatInput';

interface UIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  status?: 'pending' | 'streaming' | 'completed' | 'error';
  toolCalls?: any[];
  created_at: string;
}

export default function FloatingChatBot() {
  const { isAuthenticated, isLoading } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>();
  const [backendReady, setBackendReady] = useState(true);
  const activeConversationIdRef = useRef<string | undefined>();
  const agentRef = useRef<AgentLoop | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Keep ref in sync with state
  useEffect(() => {
    activeConversationIdRef.current = activeConversationId;
  }, [activeConversationId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize agent on mount
  useEffect(() => {
    if (!isAuthenticated) return;

    const init = async () => {
      try {
        const { tools } = await getAvailableTools();
        const systemPrompt = await buildSystemPrompt(tools);
        const agent = new AgentLoop({
          model: 'fast',
          systemPrompt,
          tools: tools.map((t) => {
            const unwrapped = unwrapTool(t);
            return {
              ...unwrapped,
              execute: async (params: Record<string, unknown>) => {
                const name = (t as any).function?.name ?? (t as any).name;
                const token = localStorage.getItem('auth_token') || '';
                const res = await fetch(`/api/assistant/execute-tool`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                  },
                  body: JSON.stringify({ tool: name, parameters: params }),
                });
                if (!res.ok) throw new Error(`Tool ${name} failed`);
                return res.text();
              },
            };
          }),
          maxIterations: 5,
          onEvent: (event: AgentEvent) => {
            switch (event.type) {
              case 'content':
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.role === 'assistant' && last.status === 'streaming') {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + event.text,
                    };
                    return updated;
                  }
                  return [
                    ...prev,
                    {
                      id: crypto.randomUUID(),
                      role: 'assistant',
                      content: event.text,
                      status: 'streaming',
                      created_at: new Date().toISOString(),
                    } as UIMessage,
                  ];
                });
                break;
              case 'done':
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last && last.role === 'assistant') {
                    last.status = 'completed';
                  }
                  return updated;
                });
                setIsStreaming(false);
                persistMessages();
                break;
              case 'error':
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.role === 'assistant' && last.status === 'streaming') {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...last,
                      status: 'error',
                    };
                    return updated;
                  }
                  return [
                    ...prev,
                    {
                      id: crypto.randomUUID(),
                      role: 'assistant',
                      content: event.message,
                      status: 'error',
                      created_at: new Date().toISOString(),
                    } as UIMessage,
                  ];
                });
                setIsStreaming(false);
                break;
            }
          },
        });
        agentRef.current = agent;
      } catch {
        setBackendReady(false);
      }
    };

    init();
  }, [isAuthenticated]);

  // Load most recent conversation when opened (only on first open, not on re-open after new chat)
  const hasLoadedHistory = useRef(false);
  useEffect(() => {
    if (!isOpen || !isAuthenticated || hasLoadedHistory.current) return;

    const load = async () => {
      try {
        const { conversations } = await getConversations();
        if (conversations && conversations.length > 0) {
          const conv = conversations[0];
          setActiveConversationId(conv.id);
          activeConversationIdRef.current = conv.id;

          // Load full conversation with messages
          try {
            const fullConv = await getConversation(conv.id);
            if (fullConv.messages && fullConv.messages.length > 0) {
              const loadedMessages: UIMessage[] = fullConv.messages.map((m) => ({
                id: m.id,
                role: m.role as any,
                content: m.content,
                status: 'completed',
                created_at: m.created_at,
              }));
              setMessages(loadedMessages);

              // Hydrate AgentLoop with loaded messages
              const agentMsgs: AgentMessage[] = fullConv.messages.map((m) => ({
                id: m.id,
                role: m.role as any,
                content: m.content,
                createdAt: m.created_at,
              }));
              agentRef.current?.setMessages(agentMsgs);
            }
          } catch {
            // Silently ignore message load failure
          }
        }
        hasLoadedHistory.current = true;
      } catch {
        // Silently start fresh
        hasLoadedHistory.current = true;
      }
    };

    load();
  }, [isOpen, isAuthenticated]);

  const persistMessages = useCallback(async () => {
    if (!agentRef.current) return;
    const allMessages = agentRef.current.getMessages();
    const payload = allMessages
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const result = await chatLog(payload, activeConversationIdRef.current);
      if (result.conversation_id && !activeConversationIdRef.current) {
        setActiveConversationId(result.conversation_id);
      }
    } catch {
      // Silently ignore persistence failure
    }
  }, []);

  const handleSend = async (text: string, _model: 'fast' | 'thinking') => {
    if (!agentRef.current || isStreaming) return;

    setIsStreaming(true);

    // Add user message to UI
    const userMsg: UIMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      status: 'completed',
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Build system prompt with RAG context
    try {
      const { tools } = await getAvailableTools();
      const systemPrompt = await buildSystemPrompt(tools, text);
      agentRef.current.updateSystemPrompt(systemPrompt);
    } catch {
      // RAG failure is non-fatal; continue with existing system prompt
    }

    await agentRef.current.send(text);
  };

  const handleRetry = async () => {
    // Find the last user message
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMsg && agentRef.current) {
      // Remove the error/assistant messages after the last user message
      const lastUserIndex = messages.findIndex((m) => m.id === lastUserMsg.id);
      setMessages((prev) => prev.slice(0, lastUserIndex + 1));
      // Also clear AgentLoop messages after the last user
      const agentMsgs = agentRef.current.getMessages();
      const agentLastUserIndex = agentMsgs.findIndex((m) => m.id === lastUserMsg.id);
      agentRef.current.setMessages(agentMsgs.slice(0, agentLastUserIndex + 1));

      setIsStreaming(true);
      await agentRef.current.send(lastUserMsg.content);
    }
  };

  const handleClearChat = () => {
    if (isStreaming && agentRef.current) {
      agentRef.current.stop();
    }
    setMessages([]);
    setActiveConversationId(undefined);
    activeConversationIdRef.current = undefined;
    // NOTE: do NOT reset hasLoadedHistory here. If the user minimizes
    // and reopens after new chat, we don't want to reload the old
    // backend conversation. hasLoadedHistory only resets on full page refresh.
    if (agentRef.current) {
      agentRef.current.clear();
    }
  };

  if (!isAuthenticated || isLoading) return null;

  return (
    <>
      {/* Minimized button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            position: 'fixed',
            right: 24,
            bottom: 24,
            width: 48,
            height: 48,
            borderRadius: '50%',
            background: '#5e6ad2',
            border: 'none',
            cursor: 'pointer',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            transition: 'transform 150ms ease',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.05)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round">
            <path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z"/>
            <path d="M9 10h.01"/><path d="M15 10h.01"/><path d="M9.5 15a3.5 3.5 0 0 0 5 0"/>
          </svg>
        </button>
      )}

      {/* Open chat card */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            right: 24,
            bottom: 80,
            width: 'clamp(300px, 380px, calc(100vw - 32px))',
            height: 'clamp(400px, 500px, 80vh)',
            maxHeight: '80vh',
            background: '#0f1011',
            borderRadius: 12,
            border: '1px solid rgba(255,255,255,0.08)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {isStreaming && (
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: '#27a644',
                    animation: 'pulse 1.5s infinite',
                  }}
                />
              )}
              <span style={{ color: '#f7f8f8', fontSize: 14, fontWeight: 600 }}>
                AI Assistant
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleClearChat}
                title="New chat"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#62666d',
                  cursor: 'pointer',
                  fontSize: 16,
                  padding: 4,
                }}
              >
                &#x21bb;
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Minimize"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#62666d',
                  cursor: 'pointer',
                  fontSize: 16,
                  padding: 4,
                }}
              >
                &#x2013;
              </button>
            </div>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', marginTop: 40, color: '#62666d' }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#5e6ad2" strokeWidth="1.5" strokeLinecap="round">
                    <path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z"/>
                    <path d="M9 10h.01"/><path d="M15 10h.01"/><path d="M9.5 15a3.5 3.5 0 0 0 5 0"/>
                  </svg>
                </div>
                <p style={{ fontSize: 14, fontWeight: 500, color: '#d0d6e0' }}>
                  How can I help?
                </p>
              </div>
            )}
            {messages.map((msg) => (
              <div key={msg.id}>
                <ChatMessage
                  role={msg.role}
                  content={msg.content}
                  isStreaming={msg.status === 'streaming'}
                  toolCalls={msg.toolCalls}
                />
                {msg.status === 'error' && (
                  <button
                    onClick={handleRetry}
                    style={{
                      marginTop: 4,
                      padding: '4px 12px',
                      background: 'rgba(239, 68, 68, 0.15)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: 6,
                      color: '#ef4444',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                  >
                    Retry
                  </button>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div
            style={{
              padding: '8px 12px',
              borderTop: '1px solid rgba(255,255,255,0.06)',
              background: '#0a0b0c',
            }}
          >
            <LinearChatInput
              onSend={handleSend}
              onStop={() => agentRef.current?.stop()}
              disabled={false}
              isStreaming={isStreaming}
              placeholder="Ask anything..."
              compact
            />
          </div>
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/assistant/FloatingChatBot.tsx
git commit -m "feat(assistant): add FloatingChatBot component"
```

---

### Task 10: Mount FloatingChatBot inside Layout

**Files:**
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Add import and mount**

In `frontend/src/components/Layout.tsx`, add the import near the top:

```typescript
import FloatingChatBot from './assistant/FloatingChatBot';
```

And add `<FloatingChatBot />` at the end of the Layout component's return JSX (before the closing fragment or div of the main layout).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Layout.tsx
git commit -m "feat(assistant): mount FloatingChatBot inside Layout"
```

---

## Chunk 5: Verification

### Task 11: Build and test

- [ ] **Step 1: Verify backend builds**

```bash
cd backend && python -m py_compile app/assistant/llm.py app/routes/assistant.py app/config.py
```

Expected: No errors.

- [ ] **Step 2: Run backend tests**

```bash
cd backend && pytest tests/test_llm_client.py -v
```

Expected: All 9 tests PASS.

- [ ] **Step 3: Verify frontend builds**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No TypeScript errors introduced by our changes (pre-existing errors are okay).

- [ ] **Step 4: Build frontend for production**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 5: Run frontend dev server and manually verify**

```bash
cd frontend && npm run dev
```

Checklist:
- [ ] Floating bot button appears in bottom-right when logged in
- [ ] Button is hidden on auth page / when logged out
- [ ] Clicking button opens the chat card (~380x500px)
- [ ] Clicking minimize closes the card
- [ ] Sending a message shows loading indicator
- [ ] Response appears in the chat
- [ ] New chat button clears the conversation
- [ ] Error states display inline with Retry button
- [ ] Closing and reopening the bot after new chat does NOT re-load the old conversation

- [ ] **Step 6: Commit any final fixes**

```bash
git commit -m "fix(assistant): address review feedback from floating bot implementation"
```

---

## Summary of Files Changed

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/config.py` | Modify | Add `llm_base_url`, `llm_model`, `get_llm_key()` |
| `backend/app/assistant/llm.py` | Modify | Refactor `LLMClient`, add `get_llm_client()` factory |
| `backend/app/routes/assistant.py` | Modify | Use resolved model + `get_llm_client()` in `llm_chat_proxy` |
| `backend/tests/test_llm_client.py` | Create | Unit tests for config precedence and client construction |
| `frontend/src/agent/AgentLoop.ts` | Modify | Add `updateSystemPrompt()` and `setMessages()` |
| `frontend/src/services/assistant.ts` | Modify | Update `chatLog()` to return `conversation_id` |
| `frontend/src/App.tsx` | Modify | Remove `/assistant` route and `AssistantPage` import |
| `frontend/src/components/Layout.tsx` | Modify | Remove "AI Assistant" nav, mount `FloatingChatBot` |
| `frontend/src/components/assistant/LinearChatInput.tsx` | Modify | Add `compact` prop |
| `frontend/src/components/assistant/FloatingChatBot.tsx` | Create | New floating chat bot component |
| `frontend/src/pages/AssistantPage.tsx` | Delete | Dead full-page assistant code |
| `frontend/src/components/assistant/ConversationSidebar.tsx` | Delete | Dead sidebar code |
| `frontend/src/components/assistant/StandaloneEditor.tsx` | Delete | Dead editor code |
| `frontend/src/components/assistant/NewFileDialog.tsx` | Delete | Dead dialog code |
