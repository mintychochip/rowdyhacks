# Design: Floating AI Chat Bot + OpenAI-Compatible LLM Provider

## Goal
Replace the full-page `/assistant` route with a minimizable floating chat bot anchored to the bottom-right of the screen, and make the LLM backend configurable to work with any OpenAI-compatible API endpoint instead of being hardcoded to Poolside.

## Frontend Architecture

### Route & Navigation Cleanup
- Remove `/assistant` from `frontend/src/App.tsx`.
- Remove "AI Assistant" from the main sidebar nav in `Layout.tsx`.
- Delete the following dead code since the full-page assistant is removed:
  - `frontend/src/pages/AssistantPage.tsx`
  - `frontend/src/components/assistant/ConversationSidebar.tsx`
  - `frontend/src/components/assistant/StandaloneEditor.tsx`
  - `frontend/src/components/assistant/NewFileDialog.tsx`
- Keep `ChatMessage.tsx`, `LinearChatInput.tsx`, and the `AgentLoop` logic — they are reused by the floating bot.
- `LinearChatInput` gets a new optional `compact` prop (default `false`). When `compact={true}`:
  - The model toggle pills (Fast/Thinking) are hidden.
  - The container `maxWidth` is removed so it fits inside the ~380px floating card.
  - The textarea is capped at 2 rows.
- Remove the `AssistantPage` import from `frontend/src/App.tsx` in addition to deleting the route.

### New Component: `FloatingChatBot`
- Mounted once inside `<Layout>` in `frontend/src/App.tsx`, so it is present on every authenticated page.
- Uses `useAuth()` hook to determine visibility: only renders when `isAuthenticated` is `true`. Hidden while auth state is loading. Not visible on the login page or when the user is logged out.
- **Minimized state:** A 48px circular button fixed to the bottom-right (`position: fixed; right: 24px; bottom: 24px; z-index: 1000`). Uses the existing assistant icon. Subtle shadow + hover scale.
- **Open state:** A card (~380px wide, 500px tall max) anchored above the button. Dark background (`#0f1011`), rounded 12px, 1px border, shadow. On mobile viewports (< 640px), the card goes full-width (100vw - 32px) and full-height (80vh).
- **State persistence across routes:** The `isOpen` state is local to `FloatingChatBot`. It stays open/closed while the user navigates within the authenticated app (no URL sync needed).
- Card layout:
  - Header row: "AI Assistant" title + minimize (`_`) and clear-chat (`↺`) buttons.
  - Scrollable message area: Reuses `ChatMessage` component. Max bubble width ~340px. Same loading indicator (a pulsing dot shown while the agent is working, not SSE streaming of content chunks).
  - Compact input bar: Single-line textarea (2 rows max) + send button. No model toggle pills. Uses `position: sticky; bottom: 0` inside the scrollable area for mobile virtual keyboard handling.
- **Loading guard:** While a message is being sent/processed, the send button is disabled and shows a loading spinner. The textarea is also disabled. The bot header shows a pulsing dot (green/pulse indicator) when a response is in progress. Spamming Enter is prevented by the disabled state.
- **Retry UI:** If an LLM request fails (network error, 500, timeout), the error message appears inline as an assistant message bubble with a red "Retry" button beneath it. Clicking Retry resends the last user message (and its full conversation context) through the same `AgentLoop` instance.
- **New chat:** The clear-chat button in the header clears local messages and creates a new empty conversation. It does NOT call `chat-log` with an empty body. Instead, it simply resets local state; the first message sent in the new thread will create and persist the conversation via `chat-log`.

### Conversation Model
- Only one "active" conversation is maintained in the floating bot's React state.
- On open, fetch the most recent conversation from `GET /api/assistant/history` (limit 1).
  - The response shape is `{ conversations: Conversation[], total: number }`. The frontend extracts `conversations[0]` if present.
  - If the request fails (network error, 500, auth expired), silently start fresh — show an empty chat with the default welcome message. Do not crash or show an error banner for this background fetch failure.
  - If the response is empty or returns no conversations, start fresh.
- The existing backend APIs (`GET /api/assistant/history`, `POST /api/assistant/chat-log`) remain available for history retrieval and persistence.
- **Optimistic persistence on unmount:** Not required for v1. If the user closes the tab while a conversation exists only in local state, it is lost. `chat-log` is only called on `done` events, not on component unmount.

### Conversation ID Lifecycle
`FloatingChatBot` tracks `activeConversationId` in local React state:
- **Initial:** `undefined`.
- **On load from history:** Set to `conversations[0].id` after fetching from `GET /api/assistant/history`.
- **On new chat:** Set back to `undefined`.
- **On first message in a new thread:** `chat-log` is called without `conversation_id`. The backend creates a new conversation and returns `{ conversation_id: string }`. The frontend captures this ID and sets `activeConversationId` so subsequent messages in the same session append to the same thread.
- **On `chat-log` for existing threads:** `conversation_id` is included in the payload so the backend appends to the existing thread.

### AgentLoop Setup and Lifecycle
`FloatingChatBot` instantiates **one** `AgentLoop` on mount and keeps it in a ref for the lifetime of the component.

**Constructor config (`AgentConfig`):**
- `model`: `'fast'` (hardcoded; no model toggle in the compact UI).
- `systemPrompt`: Built via `buildSystemPrompt(tools)` from `frontend/src/agent/context.ts`.
- `tools`: Fetched from `GET /api/assistant/tools` and unwrapped via `unwrapTool()`.
- `maxIterations`: `5`.
- `onEvent`: Callback that updates local React state based on `AgentEvent` types.

**Per-message system prompt update:** Add an `updateSystemPrompt(prompt: string)` method to `AgentLoop` that mutates `this.config.systemPrompt`. Before each `send()`, `FloatingChatBot` calls `buildSystemPrompt(tools, userMessage)` to build a new system prompt with RAG context, then calls `agentLoopRef.current.updateSystemPrompt(newPrompt)` followed by `agentLoopRef.current.send(userMessage)`.

**History hydration:** Add a `setMessages(messages: AgentMessage[]): void` method to `AgentLoop` that replaces `this.messages`. When `FloatingChatBot` loads a prior conversation from the backend, it calls `agentLoopRef.current.setMessages(loadedMessages)` so the next `send()` includes full historical context.

**Cancellation behavior:**
- Clicking the minimize button while a request is in flight does NOT abort it. The `AgentLoop` continues processing in the background. Reopening the bot shows the completed (or in-progress) response.
- Clicking the clear-chat button while a request is in flight calls `agentLoopRef.current.stop()` (which aborts the `AbortController`) before clearing local state.
- Closing the browser tab/page lets the browser cancel any in-flight fetches naturally.

## Backend Architecture (LLM Provider Config)

### Config Changes (`backend/app/config.py`)
The codebase already has `llm_api_key` (line 54) and `assistant_fast_model` / `assistant_thinking_model` (lines 76-82). We refine the config as follows:

- Add `llm_base_url: str = Field(default="")` — empty default reinforces provider-neutral intent.
- Add `llm_model: str = Field(default="")` — generic default model.
- Existing fields to keep:
  - `llm_api_key` — the primary generic API key.
  - `poolside_api_key` — retained as fallback for backward compatibility.
  - `assistant_fast_model` / `assistant_thinking_model` — retained, but their values now come from the configured provider instead of being hardcoded Poolside names.

**Precedence rules:**
1. `llm_base_url` and `llm_model` are used if set (non-empty).
2. If `llm_base_url` is empty, fall back to `poolside_api_url`.
3. If `llm_model` is empty, fall back to `assistant_model`.
4. API key: `llm_api_key` if set, else `poolside_api_key`.

### LLMClient Refactor (`backend/app/assistant/llm.py`)
- Change `LLMClient.__init__` to accept optional `base_url`, `api_key`, and `model` parameters. When omitted, it falls back to the resolved settings (same behavior as today).
- Add a factory `get_llm_client(model: str | None = None)` that resolves `base_url` and `api_key` via the precedence rules above, and constructs `LLMClient`. If `model` is passed, it is used directly; otherwise the factory resolves the default model (`llm_model` → `assistant_model`).
- Keep the global `llm_client = LLMClient()` singleton for backward compatibility. All existing call sites in `assistant.py` continue to work.
- Remove hardcoded `POOLSIDE_API_URL`/`POOLSIDE_API_KEY` module-level constants; move resolution into `get_llm_client()`. (Audit confirms no other backend files import these constants — only `llm.py` uses them.)
- The actual HTTP call logic stays identical — it already speaks OpenAI-compatible chat completions format (`/chat/completions`).

### Route Changes (`backend/app/routes/assistant.py`)
- In `POST /api/llm/chat`, stop hardcoding `poolside/m.1` and `poolside/laguna-xs.2`.
- Map `request.model` ("fast" / "thinking") to a resolved model string:
  - `"fast"` → `settings.assistant_fast_model` if non-empty, else `settings.llm_model`.
  - `"thinking"` → `settings.assistant_thinking_model` if non-empty, else `settings.llm_model`.
  - If the resolved model string is empty (i.e., none of the above settings are configured), return HTTP 500 with the message: `"LLM provider not configured."`.
- Pass the resolved model string to `get_llm_client(resolved_model)` and forward the request.

### Backward Compatibility
- Existing deployments with `HACKVERIFY_POOLSIDE_API_KEY` continue working without changes.
- To switch providers, set `HACKVERIFY_LLM_BASE_URL`, `HACKVERIFY_LLM_MODEL`, and `HACKVERIFY_LLM_API_KEY`.

## Data Flow

### AgentLoop Interface (Actual)
The `AgentLoop` class (`frontend/src/agent/AgentLoop.ts`) is reused as-is, plus two added methods.
- **Constructor:** `new AgentLoop(config: AgentConfig)` where `AgentConfig = { model, systemPrompt, tools, maxIterations, onEvent }`.
- **Method:** `send(message: string): Promise<void>` — initiates the request, executes tool loops internally, and emits events via `onEvent`.
- **Added method:** `updateSystemPrompt(prompt: string): void` — mutates `this.config.systemPrompt` so RAG context can be refreshed per-message.
- **Method:** `stop(): void` — aborts the in-flight `AbortController` and sets `running = false`.
- **Event contract:** `onEvent` receives `AgentEvent`:
  - `{ type: 'thinking' }`
  - `{ type: 'content', text: string }`
  - `{ type: 'tool_call', tool: ToolCall }`
  - `{ type: 'tool_result', result: ToolResult }`
  - `{ type: 'done', messageId: string }`
  - `{ type: 'error', message: string }`

### Full Flow
1. `FloatingChatBot` component (mounted inside `<Layout>`) renders minimized button when `isAuthenticated` is `true`.
2. User clicks button → `isOpen` toggles `true`. Component fetches the most recent conversation from `GET /api/assistant/history` (limit 1).
   - On failure: silently start fresh (show default welcome message).
   - On success with no conversations: start fresh.
   - On success with a conversation: load its messages into local state. Response shape: `{ conversations, total }`; extract `conversations[0]`.
3. On mount, `FloatingChatBot` fetches tools via `getAvailableTools()`, builds an initial system prompt via `buildSystemPrompt(tools)`, and instantiates `AgentLoop` with these values. The `AgentLoop` instance is stored in a ref and reused for the component's lifetime.
4. User types in compact textarea, hits Enter → `FloatingChatBot`:
   a. Builds a new system prompt with RAG context via `buildSystemPrompt(tools, userMessage)`.
   b. Calls `agentLoopRef.current.updateSystemPrompt(newPrompt)`.
   c. Calls `agentLoopRef.current.send(userMessage)`.
5. `AgentLoop` internally calls `llmChat(messages, 'fast', abortSignal)` which sends `POST /api/llm/chat`.
6. Backend `llm_chat_proxy()` resolves the LLM provider settings via `get_llm_client()`, builds tools for the user's role, and sends a standard OpenAI-compatible chat completion request (`stream=False`).
7. `AgentLoop` receives the JSON response and emits events (`content`, `tool_call`, `tool_result`, `done`, `error`) which `FloatingChatBot` listens to and updates React state.
8. On `done`, `FloatingChatBot` calls `POST /api/assistant/chat-log` to persist the full conversation.
   - **Payload shape:** `{ messages: Array<{ role, content }>, conversation_id?: string }`. The `messages` array includes all user and assistant messages from `agentLoopRef.current.getMessages()`, mapped to `{ role, content }`. Tool-role messages are filtered out before sending to `chat-log` (they lose `tool_call_id` in the simple mapping, and the backend conversation model doesn't require them for display). If this is a continuation of an existing conversation, `conversation_id` is included.
   - If `chat-log` fails, the conversation remains in local state only and is lost on refresh.

## Error Handling
- Backend LLM provider misconfiguration → `POST /api/llm/chat` returns HTTP 500 with message `"LLM provider not configured."`. The frontend shows this error inline in the chat as an assistant message.
- LLM API key missing or invalid → caught by `LLMClient` and surfaced as HTTP 502/503 with a descriptive message. Frontend shows the error inline.
- Network failures to the external LLM endpoint → standard `httpx` timeout handling, frontend shows a retry option (a "Retry" button inline in the failed message).
- `GET /api/assistant/history` failure on open → silently start fresh. No error banner.
- `POST /api/assistant/chat-log` failure → silently ignored. The conversation is still usable in local state but will be lost on refresh.

## Testing
- **Backend unit tests required:**
  - `get_llm_client()` resolution: verify precedence rules (new env vars → old Poolside vars → fallback).
  - `POST /api/llm/chat` model mapping: verify "fast" maps to `assistant_fast_model` and "thinking" maps to `assistant_thinking_model`, with fallback to `llm_model`.
  - Misconfiguration behavior: verify HTTP 500 with correct message when no model is configured.
  - `LLMClient` construction: verify it uses the passed `base_url`, `api_key`, and `model`.
- **Frontend manual verification checklist:**
  - Open/close toggle works.
  - Send message, loading indicator display, done state.
  - New chat clears state.
  - Error states (backend down, LLM misconfigured).
  - Auth-gated visibility (hidden when logged out).
  - Mobile viewport (card resizes correctly, input stays above virtual keyboard).
  - Cancellation: clear-chat aborts in-flight request.
  - Retry: resends last message with full context.

## Migration Path
- Existing `HACKVERIFY_POOLSIDE_API_KEY` users don't need to change anything — the new code falls back to old vars.
- To switch providers, set `HACKVERIFY_LLM_BASE_URL`, `HACKVERIFY_LLM_MODEL`, and `HACKVERIFY_LLM_API_KEY`.
