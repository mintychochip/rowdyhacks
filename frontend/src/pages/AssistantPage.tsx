import { useEffect, useState, useCallback, useRef } from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';
import {
  deleteConversation,
  getConversation,
  getConversations,
  getAvailableTools,
  unwrapTool,
  type ChatMessage as ChatMessageType,
  type Conversation,
  type ModelType,
} from '../services/assistant';
import { AgentLoop } from '../agent/AgentLoop';
import { buildSystemPrompt } from '../agent/context';
import type { AgentMessage } from '../agent/types';
import { sandbox } from '../agent/WebContainer';
import {
  PAGE_BG,
  CARD_BG,
  PRIMARY,
  RADIUS,
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER,
  BORDER_LIGHT,
  TYPO,
} from '../theme';
import LinearChatInput from '../components/assistant/LinearChatInput';
import ChatMessageComponent from '../components/assistant/ChatMessage';
import ConversationSidebar from '../components/assistant/ConversationSidebar';

// Linear-style assistant page
export default function AssistantPage() {
  const { isMobile } = useMediaQuery();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [backendReady, setBackendReady] = useState(true);
  const [selectedModel, setSelectedModel] = useState<ModelType>('fast');
  const agentRef = useRef<AgentLoop | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Health check
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL || '/api'}/monitoring/health`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
          },
        });
        setBackendReady(res.ok);
      } catch {
        setBackendReady(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Initialize agent harness on mount
  useEffect(() => {
    initAgent();
    return () => { agentRef.current?.stop(); };
  }, []);

  async function initAgent() {
    try {
      const { tools } = await getAvailableTools();
      const systemPrompt = await buildSystemPrompt(tools);

      const agent = new AgentLoop({
        model: selectedModel,
        systemPrompt,
        tools: tools.map(t => ({
          ...unwrapTool(t),
          execute: async (params) => {
            const name = (t as any).function?.name ?? (t as any).name;
            const token = localStorage.getItem('auth_token') || '';
            const res = await fetch(`/api/assistant/execute-tool`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
              },
              body: JSON.stringify({ tool_name: name, parameters: params }),
            });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            return JSON.stringify(data.result);
          },
        })),
        maxIterations: 5,
        onEvent: () => {}, // set per-send in handleSendMessage
      });

      agentRef.current = agent;
    } catch (err: any) {
      console.error('Failed to initialize agent:', err);
    }
  }

  // Load conversations
  useEffect(() => {
    loadConversations();
  }, []);

  // Load active conversation
  useEffect(() => {
    if (activeConversationId) {
      loadConversation(activeConversationId);
    } else {
      setMessages([]);
    }
  }, [activeConversationId]);

  const loadConversations = async () => {
    try {
      const data = await getConversations();
      setConversations(data.conversations);
    } catch (err: any) {
      setError('Failed to load conversations');
    }
  };

  const loadConversation = async (id: string) => {
    try {
      setIsLoading(true);
      const data = await getConversation(id);
      setMessages(data.messages);
      setError(null);
    } catch (err: any) {
      setError('Failed to load conversation');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = () => {
    agentRef.current?.stop();
    setIsStreaming(false);
    setIsLoading(false);
    setStreamingContent('');
  };

  const handleNewChat = () => {
    setActiveConversationId(undefined);
    setMessages([]);
    setError(null);
    handleStop();
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  const handleSelectConversation = (id: string) => {
    setActiveConversationId(id);
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        handleNewChat();
      }
    } catch (err: any) {
      setError('Failed to delete conversation');
    }
  };

  const handleSendMessage = useCallback(async (content: string, model: ModelType) => {
    if (isStreaming) return;

    try {
      setIsStreaming(true);
      setError(null);
      setStreamingContent('');
      setSelectedModel(model);

      // Add user message to UI immediately
      const userMsg: AgentMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        createdAt: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMsg]);

      // Get tools and build fresh system prompt for this query
      const { tools } = await getAvailableTools();
      const systemPrompt = await buildSystemPrompt(tools, content);

      // Create agent with updated system prompt (has RAG context for this query)
      const agent = new AgentLoop({
        model,
        systemPrompt,
        tools: tools.map(t => ({
          ...unwrapTool(t),
          execute: async (params) => {
            const name = (t as any).function?.name ?? (t as any).name;
            const token = localStorage.getItem('auth_token') || '';
            const res = await fetch(`/api/assistant/execute-tool`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
              },
              body: JSON.stringify({ tool_name: name, parameters: params }),
            });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            return JSON.stringify(data.result);
          },
        })),
        maxIterations: 5,
        onEvent: (event) => {
          switch (event.type) {
            case 'content':
              setStreamingContent(prev => prev + event.text);
              break;
            case 'tool_call':
              setMessages(prev => {
                const last = prev[prev.length - 1];
                if (last?.role === 'assistant' && !last.toolCalls) last.toolCalls = [];
                if (last?.role === 'assistant') {
                  last.toolCalls = [...(last.toolCalls || []), event.tool];
                  return [...prev];
                }
                return [...prev, {
                  id: crypto.randomUUID(),
                  role: 'assistant',
                  content: '',
                  toolCalls: [event.tool],
                  createdAt: new Date().toISOString(),
                }];
              });
              break;
            case 'tool_result':
              setMessages(prev => {
                const last = prev[prev.length - 1];
                if (last?.role === 'assistant') {
                  last.tool_results = [...(last.tool_results || []), event.result];
                  return [...prev];
                }
                return prev;
              });
              break;
            case 'done':
              setIsStreaming(false);
              setMessages(prev => {
                const content = streamingContent;
                // Find the last assistant message (from tool calls) and update it
                const reversed = [...prev].reverse();
                const idx = reversed.findIndex(m => m.role === 'assistant');
                if (idx >= 0) {
                  reversed[idx] = { ...reversed[idx], content };
                  return reversed.reverse();
                }
                return [...prev, {
                  id: event.messageId,
                  role: 'assistant',
                  content,
                  createdAt: new Date().toISOString(),
                }];
              });
              setStreamingContent('');
              break;
            case 'error':
              setIsStreaming(false);
              setError(event.message);
              setStreamingContent('');
              break;
          }
        },
      });

      agentRef.current = agent;
      await agent.send(content);
    } catch (err: any) {
      setError(err.message || 'Failed to send message');
      setIsStreaming(false);
      setStreamingContent('');
    }
  }, [isStreaming]);

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        background: PAGE_BG,
        overflow: 'hidden',
      }}
    >
      {/* Sidebar - Linear style */}
      {(!isMobile || sidebarOpen) && (
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewChat}
          onDelete={handleDeleteConversation}
          onClose={() => setSidebarOpen(false)}
          isOpen={sidebarOpen}
        />
      )}

      {/* Main Content */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
          position: 'relative',
        }}
      >
        {/* Top Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: `${SPACE.md}px ${SPACE.lg}px`,
            borderBottom: `1px solid ${BORDER}`,
            background: PAGE_BG,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                style={{
                  width: 32,
                  height: 32,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'transparent',
                  border: `1px solid ${BORDER}`,
                  borderRadius: RADIUS.md,
                  color: TEXT_SECONDARY,
                  cursor: 'pointer',
                  fontSize: 16,
                }}
              >
                ☰
              </button>
            )}
            <h1 style={{ ...TYPO.h3, margin: 0, color: TEXT_PRIMARY, fontWeight: 600 }}>
              {activeConversationId
                ? conversations.find((c) => c.id === activeConversationId)?.title || 'Conversation'
                : 'New Chat'}
            </h1>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
            {/* Status indicator */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: SPACE.xs,
                padding: `${SPACE.xs}px ${SPACE.sm}px`,
                background: isStreaming ? 'rgba(94, 106, 210, 0.1)' : 'transparent',
                borderRadius: RADIUS.sm,
                fontSize: 12,
                color: isStreaming ? PRIMARY : TEXT_MUTED,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: isStreaming ? PRIMARY : backendReady ? '#22c55e' : '#ef4444',
                  animation: isStreaming ? 'pulse 1.5s infinite' : undefined,
                }}
              />
              {isStreaming ? 'Responding...' : backendReady ? 'Ready' : 'Offline'}
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: `${SPACE.lg}px ${SPACE.xl}px`,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Empty State */}
          {messages.length === 0 && !isLoading && (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: SPACE.xl,
              }}
            >
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: RADIUS.xl,
                  background: 'linear-gradient(135deg, rgba(94, 106, 210, 0.2), rgba(94, 106, 210, 0.05))',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: SPACE.lg,
                  fontSize: 32,
                }}
              >
                🤖
              </div>
              <h2
                style={{
                  ...TYPO.h2,
                  margin: 0,
                  marginBottom: SPACE.sm,
                  color: TEXT_PRIMARY,
                  fontWeight: 600,
                  textAlign: 'center',
                }}
              >
                How can I help?
              </h2>
              <p
                style={{
                  margin: 0,
                  marginBottom: SPACE.xl,
                  color: TEXT_SECONDARY,
                  textAlign: 'center',
                  maxWidth: 400,
                  lineHeight: 1.6,
                }}
              >
                Ask about hackathon details, tracks, submission guidance, or anything else you need help with.
              </p>

              {/* Quick Prompts */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'center',
                  gap: SPACE.sm,
                  maxWidth: 500,
                }}
              >
                {[
                  'What tracks are available?',
                  'Help me brainstorm project ideas',
                  'What should I bring?',
                  'When is the deadline?',
                ].map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSendMessage(prompt, 'fast')}
                    disabled={isStreaming}
                    style={{
                      padding: `${SPACE.sm}px ${SPACE.md}px`,
                      background: 'transparent',
                      border: `1px solid ${BORDER}`,
                      borderRadius: RADIUS.md,
                      color: TEXT_SECONDARY,
                      cursor: isStreaming ? 'not-allowed' : 'pointer',
                      fontSize: 13,
                      transition: 'all 0.15s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = BORDER_LIGHT;
                      e.currentTarget.style.color = TEXT_PRIMARY;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = BORDER;
                      e.currentTarget.style.color = TEXT_SECONDARY;
                    }}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.length > 0 && (
            <div style={{ maxWidth: 720, width: '100%', margin: '0 auto' }}>
              {messages.map((msg, i) => (
                <ChatMessageComponent
                  key={msg.id || i}
                  role={msg.role}
                  content={msg.role === 'assistant' && isStreaming && i === messages.length - 1
                    ? msg.content + streamingContent
                    : msg.content}
                  isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
                  toolCalls={(msg as any).toolCalls}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Loading State */}
          {isLoading && messages.length === 0 && (
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: TEXT_MUTED,
              }}
            >
              Loading conversation...
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              style={{
                maxWidth: 720,
                margin: `${SPACE.md}px auto`,
                padding: SPACE.md,
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: RADIUS.md,
                color: '#ef4444',
                textAlign: 'center',
                fontSize: 14,
              }}
            >
              {error}
            </div>
          )}

          {/* Backend Warning */}
          {!backendReady && !error && (
            <div
              style={{
                maxWidth: 720,
                margin: `${SPACE.md}px auto`,
                padding: `${SPACE.sm}px ${SPACE.md}px`,
                background: 'rgba(245, 158, 11, 0.1)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                borderRadius: RADIUS.md,
                color: '#f59e0b',
                textAlign: 'center',
                fontSize: 13,
              }}
            >
              ⚠️ Backend is not responding - messages may not work
            </div>
          )}
        </div>

        {/* Input Area - Fixed at bottom */}
        <div
          style={{
            padding: `${SPACE.md}px ${SPACE.lg}px ${SPACE.lg}px`,
            borderTop: `1px solid ${messages.length > 0 ? BORDER : 'transparent'}`,
            background: PAGE_BG,
          }}
        >
          <LinearChatInput
            onSend={handleSendMessage}
            onStop={handleStop}
            disabled={!backendReady}
            isStreaming={isStreaming}
          />
        </div>
      </div>
    </div>
  );
}
