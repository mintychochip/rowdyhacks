import { useEffect, useState, useCallback, useRef } from 'react';
import { useMediaQuery } from '../hooks/useMediaQuery';
import {
  deleteConversation,
  getConversation,
  getConversations,
  sendChatMessage,
  streamChatResponse,
  type ChatMessage as ChatMessageType,
  type Conversation,
  type ModelType,
} from '../services/assistant';
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
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [backendReady, setBackendReady] = useState(true);
  const abortControllerRef = useRef<(() => void) | null>(null);
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
    if (abortControllerRef.current) {
      abortControllerRef.current();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setIsLoading(false);
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

      // Add user message to UI immediately
      const userMessage: ChatMessageType = {
        id: 'temp-' + Date.now(),
        role: 'user',
        content,
        status: 'completed',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Send to API with model
      const response = await sendChatMessage(
        content,
        activeConversationId,
        undefined,
        model
      );

      // Update active conversation
      if (!activeConversationId) {
        setActiveConversationId(response.conversation_id);
        loadConversations();
      }

      // Create placeholder for assistant response
      const assistantMessage: ChatMessageType = {
        id: response.message_id,
        role: 'assistant',
        content: '',
        status: 'streaming',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Stream response
      abortControllerRef.current = streamChatResponse(
        response.message_id,
        (chunk) => {
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last.role === 'assistant' && last.id === response.message_id) {
              return [...prev.slice(0, -1), { ...last, content: last.content + chunk }];
            }
            return prev;
          });
        },
        (tool, result) => {
          console.log('Tool called:', tool, result);
        },
        () => {
          setIsStreaming(false);
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, status: 'completed' }];
            }
            return prev;
          });
        },
        (err) => {
          setIsStreaming(false);
          setError(err);
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last.role === 'assistant') {
              return [...prev.slice(0, -1), { ...last, status: 'error' }];
            }
            return prev;
          });
        }
      );
    } catch (err: any) {
      setError(err.message || 'Failed to send message');
      setIsStreaming(false);
    }
  }, [activeConversationId, isStreaming]);

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
                  content={msg.content}
                  isStreaming={msg.status === 'streaming'}
                  toolCalls={msg.tool_calls}
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
