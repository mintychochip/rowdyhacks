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
  const activeConversationIdRef = useRef<string | undefined>(undefined);
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
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="4" y="4" width="16" height="12" rx="2"/>
            <path d="M9 9h.01"/><path d="M15 9h.01"/>
            <path d="M10 14l2 2 2-2"/>
            <path d="M12 16v4"/>
            <path d="M8 20h8"/>
            <path d="M2 10h2"/><path d="M20 10h2"/>
            <circle cx="8" cy="9" r="1" fill="#fff" stroke="none"/>
            <circle cx="16" cy="9" r="1" fill="#fff" stroke="none"/>
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
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#5e6ad2" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="4" y="4" width="16" height="12" rx="2"/>
                    <path d="M9 9h.01"/><path d="M15 9h.01"/>
                    <path d="M10 14l2 2 2-2"/>
                    <path d="M12 16v4"/>
                    <path d="M8 20h8"/>
                    <path d="M2 10h2"/><path d="M20 10h2"/>
                    <circle cx="8" cy="9" r="1" fill="#5e6ad2" stroke="none"/>
                    <circle cx="16" cy="9" r="1" fill="#5e6ad2" stroke="none"/>
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
