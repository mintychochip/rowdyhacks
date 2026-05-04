import { useEffect, useState, useCallback, useRef } from 'react';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import {
  deleteConversation,
  getConversation,
  getConversations,
  sendChatMessage,
  streamChatResponse,
  type ChatMessage,
  type Conversation,
} from '../../services/assistant';
import { CARD_BG, PAGE_BG, PRIMARY, RADIUS, SPACE, TEXT_PRIMARY, TEXT_SECONDARY, TYPO } from '../../theme';
import ChatInput from './ChatInput';
import ChatMessage from './ChatMessage';
import ConversationSidebar from './ConversationSidebar';

export default function AssistantPage() {
  const { isMobile } = useMediaQuery();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const abortControllerRef = useRef<(() => void) | null>(null);

  // Load conversations on mount
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

  const handleNewChat = () => {
    setActiveConversationId(undefined);
    setMessages([]);
    setError(null);
    if (abortControllerRef.current) {
      abortControllerRef.current();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
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

  const handleSendMessage = useCallback(async (content: string) => {
    if (isStreaming) return;

    try {
      setIsStreaming(true);
      setError(null);

      // Add user message to UI immediately
      const userMessage: ChatMessage = {
        id: 'temp-' + Date.now(),
        role: 'user',
        content,
        status: 'completed',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Send to API
      const response = await sendChatMessage(
        content,
        activeConversationId,
        undefined // hackathonId - auto-detect or let user select
      );

      // Update active conversation
      if (!activeConversationId) {
        setActiveConversationId(response.conversation_id);
        loadConversations(); // Refresh list to get new conversation
      }

      // Create placeholder for assistant response
      const assistantMessage: ChatMessage = {
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
          // Append chunk to assistant message
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last.role === 'assistant' && last.id === response.message_id) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: last.content + chunk },
              ];
            }
            return prev;
          });
        },
        (tool, result) => {
          // Handle tool call
          console.log('Tool called:', tool, result);
        },
        () => {
          // Complete
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
          // Error
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
        height: 'calc(100vh - 80px)', // Account for header
        background: PAGE_BG,
        padding: isMobile ? SPACE.sm : SPACE.md,
        gap: SPACE.md,
      }}
    >
      {/* Sidebar */}
      {(!isMobile || sidebarOpen) && (
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewChat}
          onDelete={handleDeleteConversation}
        />
      )}

      {/* Main chat area */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          background: CARD_BG,
          borderRadius: RADIUS.md,
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: `${SPACE.md}px ${SPACE.lg}px`,
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
            {isMobile && (
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: TEXT_PRIMARY,
                  cursor: 'pointer',
                  padding: SPACE.xs,
                }}
              >
                <span className="material-symbols-outlined">menu</span>
              </button>
            )}
            <h1 style={{ ...TYPO.h2, margin: 0, color: TEXT_PRIMARY }}>
              AI Assistant
            </h1>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: SPACE.sm }}>
            <span
              style={{
                padding: `${SPACE.xs}px ${SPACE.sm}px`,
                background: isStreaming ? 'rgba(37, 99, 235, 0.2)' : 'transparent',
                color: isStreaming ? PRIMARY : TEXT_SECONDARY,
                borderRadius: RADIUS.sm,
                fontSize: 12,
              }}
            >
              {isStreaming ? '● Responding...' : 'Ready'}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: SPACE.lg,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {messages.length === 0 && !isLoading && (
            <div
              style={{
                textAlign: 'center',
                color: TEXT_SECONDARY,
                padding: SPACE.xl,
              }}
            >
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 64, marginBottom: SPACE.md, opacity: 0.5 }}
              >
                smart_toy
              </span>
              <h2 style={{ ...TYPO.h3, marginBottom: SPACE.sm }}>
                How can I help you today?
              </h2>
              <p style={{ margin: 0, lineHeight: 1.6 }}>
                Ask about hackathon details, tracks, submission guidance,
                <br />
                or anything else you need help with!
              </p>

              {/* Suggested prompts */}
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'center',
                  gap: SPACE.sm,
                  marginTop: SPACE.lg,
                }}
              >
                {[
                  'What tracks are available?',
                  'Help me brainstorm project ideas',
                  'What should I bring?',
                  'When is the submission deadline?',
                ].map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSendMessage(prompt)}
                    disabled={isStreaming}
                    style={{
                      padding: `${SPACE.sm}px ${SPACE.md}px`,
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: RADIUS.sm,
                      color: TEXT_PRIMARY,
                      cursor: isStreaming ? 'not-allowed' : 'pointer',
                      fontSize: 13,
                      opacity: isStreaming ? 0.5 : 1,
                    }}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <ChatMessage
              key={msg.id || i}
              role={msg.role}
              content={msg.content}
              isStreaming={msg.status === 'streaming'}
              toolCalls={msg.tool_calls}
            />
          ))}

          {isLoading && (
            <div style={{ textAlign: 'center', padding: SPACE.lg, color: TEXT_SECONDARY }}>
              Loading...
            </div>
          )}

          {error && (
            <div
              style={{
                padding: SPACE.md,
                background: 'rgba(239, 68, 68, 0.2)',
                borderRadius: RADIUS.sm,
                color: '#ef4444',
                textAlign: 'center',
              }}
            >
              {error}
            </div>
          )}
        </div>

        {/* Input */}
        <div style={{ padding: SPACE.lg }}>
          <ChatInput
            onSend={handleSendMessage}
            disabled={isStreaming}
          />
        </div>
      </div>
    </div>
  );
}
