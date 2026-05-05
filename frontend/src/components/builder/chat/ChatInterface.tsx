import { useState, useRef, useCallback, useEffect } from 'react';
import {
  CARD_BG,
  PRIMARY,
  PRIMARY_HOVER,
  CYAN,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER,
  SPACE,
  RADIUS,
  SHADOW,
} from '../../../theme';
import ChatMessage from '../../assistant/ChatMessage';
import {
  sendChatMessage,
  streamChatResponse,
  ChatMessage as ChatMessageType,
} from '../../../services/assistant';

interface IntentDetectionResult {
  hasBuildIntent: boolean;
  suggestedMode: string;
}

interface ChatInterfaceProps {
  hackathonId?: string;
  conversationId?: string;
  onModeChange?: (mode: string) => void;
  onCreatePlan?: () => void;
}

export default function ChatInterface({
  hackathonId,
  conversationId: initialConversationId,
  onModeChange,
  onCreatePlan,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(
    initialConversationId
  );
  const [detectedIntent, setDetectedIntent] = useState<IntentDetectionResult | null>(null);
  const [showIntentButtons, setShowIntentButtons] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  // Detect build intent from user message
  const detectBuildIntent = useCallback(async (message: string): Promise<IntentDetectionResult> => {
    try {
      const token = localStorage.getItem('auth_token') || '';
      const baseUrl = import.meta.env.VITE_API_URL || '/api';

      const response = await fetch(`${baseUrl}/assistant/detect-intent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        // Fallback to client-side detection if API fails
        return fallbackIntentDetection(message);
      }

      return await response.json();
    } catch (error) {
      // Fallback to client-side detection
      return fallbackIntentDetection(message);
    }
  }, []);

  // Client-side fallback intent detection
  const fallbackIntentDetection = (message: string): IntentDetectionResult => {
    const buildPatterns = [
      /i want to build/i,
      /i want to create/i,
      /i want to make/i,
      /i'm building/i,
      /i am building/i,
      /let's build/i,
      /lets build/i,
      /help me build/i,
      /i need to build/i,
      /i would like to build/i,
      /plan to build/i,
      /thinking about building/i,
      /starting a project/i,
      /new project idea/i,
      /hackathon project/i,
      /app idea/i,
      /website idea/i,
    ];

    const hasBuildIntent = buildPatterns.some((pattern) => pattern.test(message));

    return {
      hasBuildIntent,
      suggestedMode: hasBuildIntent ? 'plan' : 'chat',
    };
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading || isStreaming) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);
    setDetectedIntent(null);
    setShowIntentButtons(false);

    // Add user message to UI
    const newUserMessage: ChatMessageType = {
      id: Date.now().toString(),
      role: 'user',
      content: userMessage,
      status: 'completed',
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, newUserMessage]);

    // Detect build intent
    const intentResult = await detectBuildIntent(userMessage);
    setDetectedIntent(intentResult);

    // Show intent buttons if build intent detected
    if (intentResult.hasBuildIntent) {
      setShowIntentButtons(true);
    }

    try {
      // Send message to backend
      const response = await sendChatMessage(
        userMessage,
        conversationId,
        hackathonId
      );

      setConversationId(response.conversation_id);

      // Add placeholder for assistant response
      const assistantMessageId = response.message_id;
      const newAssistantMessage: ChatMessageType = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        status: 'streaming',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, newAssistantMessage]);
      setIsStreaming(true);

      // Stream the response
      let streamedContent = '';

      const cleanup = streamChatResponse(
        assistantMessageId,
        (chunk) => {
          streamedContent += chunk;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: streamedContent }
                : msg
            )
          );
        },
        () => {
          // Tool call handler
        },
        () => {
          // Complete
          setIsStreaming(false);
          setIsLoading(false);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, status: 'completed' }
                : msg
            )
          );
        },
        (error) => {
          // Error
          console.error('Stream error:', error);
          setIsStreaming(false);
          setIsLoading(false);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, status: 'error', content: msg.content || 'Error: ' + error }
                : msg
            )
          );
        }
      );

      // Cleanup on component unmount
      return () => cleanup();
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsLoading(false);
      setIsStreaming(false);

      // Add error message
      const errorMessage: ChatMessageType = {
        id: Date.now().toString(),
        role: 'assistant',
        content:
          'Sorry, I encountered an error. Please try again.\n\n' +
          (error instanceof Error ? error.message : 'Unknown error'),
        status: 'error',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCreatePlan = () => {
    setShowIntentButtons(false);
    if (onCreatePlan) {
      onCreatePlan();
    } else if (onModeChange) {
      onModeChange('plan');
    }
  };

  const handleStartBuilding = () => {
    setShowIntentButtons(false);
    if (onModeChange) {
      onModeChange('build');
    }
  };

  const handleKeepChatting = () => {
    setShowIntentButtons(false);
    // Continue in chat mode - no action needed
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: CARD_BG,
        borderRadius: RADIUS.lg,
        border: `1px solid ${BORDER}`,
        boxShadow: SHADOW.card,
        overflow: 'hidden',
      }}
    >
      {/* Messages Area */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: SPACE.lg,
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: TEXT_SECONDARY,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 48, marginBottom: SPACE.md }}>💬</div>
            <h3 style={{ margin: 0, marginBottom: SPACE.sm, color: TEXT_PRIMARY }}>
              Start a Conversation
            </h3>
            <p style={{ margin: 0, maxWidth: 400 }}>
              Ask me anything about the hackathon, tracks, or say "I want to build..." to
              start planning your project.
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                content={msg.content}
                isStreaming={msg.status === 'streaming' && index === messages.length - 1}
                toolCalls={msg.tool_calls}
              />
            ))}
            <div ref={messagesEndRef} />

            {/* Intent Detection Buttons */}
            {showIntentButtons && detectedIntent?.hasBuildIntent && (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: SPACE.md,
                  padding: SPACE.md,
                  background: `linear-gradient(135deg, ${PRIMARY}15, ${CYAN}15)`,
                  borderRadius: RADIUS.md,
                  marginTop: SPACE.md,
                  border: `1px solid ${PRIMARY}30`,
                }}
              >
                <div style={{ color: TEXT_PRIMARY, fontSize: 14, fontWeight: 500 }}>
                  It looks like you want to build something! What would you like to do?
                </div>
                <div
                  style={{
                    display: 'flex',
                    gap: SPACE.md,
                    flexWrap: 'wrap',
                    justifyContent: 'center',
                  }}
                >
                  <button
                    onClick={handleCreatePlan}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: SPACE.xs,
                      padding: `${SPACE.sm}px ${SPACE.md}px`,
                      background: PRIMARY,
                      color: '#fff',
                      border: 'none',
                      borderRadius: RADIUS.md,
                      cursor: 'pointer',
                      fontSize: 14,
                      fontWeight: 500,
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = PRIMARY_HOVER;
                      e.currentTarget.style.transform = 'translateY(-1px)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = PRIMARY;
                      e.currentTarget.style.transform = 'translateY(0)';
                    }}
                  >
                    <span>📋</span>
                    Create Plan
                  </button>
                  <button
                    onClick={handleStartBuilding}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: SPACE.xs,
                      padding: `${SPACE.sm}px ${SPACE.md}px`,
                      background: 'transparent',
                      color: CYAN,
                      border: `1px solid ${CYAN}`,
                      borderRadius: RADIUS.md,
                      cursor: 'pointer',
                      fontSize: 14,
                      fontWeight: 500,
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = CYAN + '20';
                      e.currentTarget.style.transform = 'translateY(-1px)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }}
                  >
                    <span>🔨</span>
                    Start Building
                  </button>
                  <button
                    onClick={handleKeepChatting}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: SPACE.xs,
                      padding: `${SPACE.sm}px ${SPACE.md}px`,
                      background: 'transparent',
                      color: TEXT_SECONDARY,
                      border: `1px solid ${BORDER}`,
                      borderRadius: RADIUS.md,
                      cursor: 'pointer',
                      fontSize: 14,
                      fontWeight: 500,
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = BORDER;
                      e.currentTarget.style.color = TEXT_PRIMARY;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = TEXT_SECONDARY;
                    }}
                  >
                    <span>💬</span>
                    Keep Chatting
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Input Area */}
      <div
        style={{
          padding: SPACE.md,
          borderTop: `1px solid ${BORDER}`,
          background: CARD_BG,
        }}
      >
        <div
          style={{
            display: 'flex',
            gap: SPACE.sm,
            alignItems: 'flex-end',
          }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Shift+Enter for new line)"
            disabled={isLoading || isStreaming}
            style={{
              flex: 1,
              minHeight: 44,
              maxHeight: 200,
              padding: `${SPACE.sm}px ${SPACE.md}px`,
              background: '#334155',
              border: `1px solid ${BORDER}`,
              borderRadius: RADIUS.md,
              color: TEXT_PRIMARY,
              fontSize: 14,
              lineHeight: 1.5,
              resize: 'none',
              outline: 'none',
              fontFamily: 'inherit',
            }}
          />
          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading || isStreaming}
            style={{
              padding: `${SPACE.sm}px ${SPACE.lg}px`,
              background:
                !input.trim() || isLoading || isStreaming ? BORDER : PRIMARY,
              color: !input.trim() || isLoading || isStreaming ? TEXT_MUTED : '#fff',
              border: 'none',
              borderRadius: RADIUS.md,
              cursor:
                !input.trim() || isLoading || isStreaming ? 'not-allowed' : 'pointer',
              fontSize: 14,
              fontWeight: 500,
              transition: 'all 0.2s ease',
              height: 44,
            }}
          >
            {isStreaming ? 'Streaming...' : isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
        <div
          style={{
            marginTop: SPACE.sm,
            fontSize: 12,
            color: TEXT_MUTED,
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <span>Press Enter to send, Shift+Enter for new line</span>
          {isStreaming && <span>AI is responding...</span>}
        </div>
      </div>
    </div>
  );
}
