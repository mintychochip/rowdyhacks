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

export type ModelType = 'fast' | 'thinking';

// Send a new chat message
export async function sendChatMessage(
  message: string,
  conversationId?: string,
  hackathonId?: string,
  model: ModelType = 'fast'
): Promise<{ conversation_id: string; message_id: string; status: string; model?: string }> {
  const params = new URLSearchParams();
  params.append('message', message);
  params.append('model', model);
  if (conversationId) params.append('conversation_id', conversationId);
  if (hackathonId) params.append('hackathon_id', hackathonId);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

  try {
    const res = await fetch(`${BASE}/assistant/chat?${params.toString()}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const errorText = await res.text();
      let errorMessage = 'Failed to send message';
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return res.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out - please try again');
    }
    throw error;
  }
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

  // Connection timeout - if no message received in 30s, consider it failed
  const CONNECTION_TIMEOUT = 30000;
  let connectionTimeoutId: ReturnType<typeof setTimeout> | null = null;
  let isConnected = false;

  const clearConnectionTimeout = () => {
    if (connectionTimeoutId) {
      clearTimeout(connectionTimeoutId);
      connectionTimeoutId = null;
    }
  };

  const startConnectionTimeout = () => {
    clearConnectionTimeout();
    connectionTimeoutId = setTimeout(() => {
      if (!isConnected) {
        console.error('[SSE] Connection timeout - no data received');
        onError('Connection timeout - assistant is taking too long to respond');
        eventSource.close();
      }
    }, CONNECTION_TIMEOUT);
  };

  startConnectionTimeout();

  // Buffer chunks to reduce React re-renders (batch updates every 50ms)
  let chunkBuffer = '';
  let flushTimeout: ReturnType<typeof setTimeout> | null = null;

  const flushBuffer = () => {
    if (chunkBuffer) {
      onChunk(chunkBuffer);
      chunkBuffer = '';
    }
    flushTimeout = null;
  };

  eventSource.onopen = () => {
    console.log('[SSE] Connection opened');
    isConnected = true;
  };

  eventSource.onmessage = (event) => {
    isConnected = true;
    clearConnectionTimeout();
    try {
      const data = JSON.parse(event.data);

      if (data.content) {
        // Buffer content chunks for smoother UI updates
        chunkBuffer += data.content;
        if (!flushTimeout) {
          flushTimeout = setTimeout(flushBuffer, 50);
        }
      }

      if (data.tool_call) {
        // Flush any pending chunks before tool call
        if (flushTimeout) {
          clearTimeout(flushTimeout);
          flushBuffer();
        }
        onToolCall(data.tool_call, data.result);
      }

      if (data.completed) {
        // Flush remaining buffer
        if (flushTimeout) {
          clearTimeout(flushTimeout);
        }
        flushBuffer();
        onComplete();
        eventSource.close();
      }

      if (data.error) {
        if (flushTimeout) {
          clearTimeout(flushTimeout);
        }
        flushBuffer();
        onError(data.error);
        eventSource.close();
      }
    } catch (e) {
      // Log parse errors for debugging
      console.error('Failed to parse SSE message:', event.data);
      console.error('Parse error:', e);
      onError('Failed to parse response');
      eventSource.close();
    }
  };

  eventSource.onerror = (error) => {
    console.error('[SSE] Connection error:', error);
    clearConnectionTimeout();
    
    // Don't show error if we already received data (connection might just be closing)
    if (!isConnected) {
      onError('Failed to connect to assistant. Please try again.');
    }
    eventSource.close();
  };

  return () => {
    clearConnectionTimeout();
    eventSource.close();
  };
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
