const BASE = import.meta.env.VITE_API_URL || '/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  tool_calls?: any[];
  tool_results?: any[];
  status: 'pending' | 'streaming' | 'completed' | 'error';
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  hackathon_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Tool {
  name: string;
  description: string;
  parameters: {
    type: string;
    properties: Record<string, any>;
    required: string[];
  };
}

// Send a new chat message
export async function sendChatMessage(
  message: string,
  conversationId?: string,
  hackathonId?: string
): Promise<{ conversation_id: string; message_id: string; status: string }> {
  const params = new URLSearchParams();
  params.append('message', message);
  if (conversationId) params.append('conversation_id', conversationId);
  if (hackathonId) params.append('hackathon_id', hackathonId);

  const res = await fetch(`${BASE}/assistant/chat?${params.toString()}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to send message');
  }

  return res.json();
}

// Stream response using SSE
export function streamChatResponse(
  messageId: string,
  onChunk: (chunk: string) => void,
  onToolCall: (tool: string, result: any) => void,
  onComplete: () => void,
  onError: (error: string) => void
): () => void {
  const token = localStorage.getItem('auth_token') || '';
  const eventSource = new EventSource(
    `${BASE}/assistant/stream/${messageId}?token=${encodeURIComponent(token)}`
  );

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.content) {
        onChunk(data.content);
      }

      if (data.tool_call) {
        onToolCall(data.tool_call, data.result);
      }

      if (data.completed) {
        onComplete();
        eventSource.close();
      }

      if (data.error) {
        onError(data.error);
        eventSource.close();
      }
    } catch (e) {
      // Ignore parse errors for incomplete chunks
    }
  };

  eventSource.onerror = (error) => {
    onError('Connection error');
    eventSource.close();
  };

  return () => eventSource.close();
}

// Get conversation history
export async function getConversations(): Promise<{
  conversations: Conversation[];
  total: number;
}> {
  const res = await fetch(`${BASE}/assistant/history`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
  });

  if (!res.ok) throw new Error('Failed to load conversations');
  return res.json();
}

// Get specific conversation with messages
export async function getConversation(
  conversationId: string
): Promise<{
  id: string;
  title: string;
  hackathon_id?: string;
  messages: ChatMessage[];
}> {
  const res = await fetch(`${BASE}/assistant/history/${conversationId}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
  });

  if (!res.ok) throw new Error('Failed to load conversation');
  return res.json();
}

// Delete conversation
export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${BASE}/assistant/history/${conversationId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
  });

  if (!res.ok) throw new Error('Failed to delete conversation');
}

// Get available tools
export async function getAvailableTools(): Promise<{
  role: string;
  tools: Tool[];
}> {
  const res = await fetch(`${BASE}/assistant/tools`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
    },
  });

  if (!res.ok) throw new Error('Failed to load tools');
  return res.json();
}
