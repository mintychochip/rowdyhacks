import ChatInterface from '../chat/ChatInterface';

interface ChatModeProps {
  hackathonId?: string;
  conversationId?: string;
  onModeChange?: (mode: 'chat' | 'plan' | 'build') => void;
  onCreatePlan?: () => void;
}

/**
 * ChatMode - Wrapper component for the chat interface in builder mode.
 *
 * This component provides a chat interface with build intent detection.
 * When the user expresses intent to build something (e.g., "I want to build..."),
 * the interface will show action buttons to:
 * - Create a plan
 * - Start building directly
 * - Continue chatting
 */
export default function ChatMode({
  hackathonId,
  conversationId,
  onModeChange,
  onCreatePlan,
}: ChatModeProps) {
  const handleModeChange = (mode: string) => {
    if (onModeChange) {
      onModeChange(mode as 'chat' | 'plan' | 'build');
    }
  };

  return (
    <ChatInterface
      hackathonId={hackathonId}
      conversationId={conversationId}
      onModeChange={handleModeChange}
      onCreatePlan={onCreatePlan}
    />
  );
}
