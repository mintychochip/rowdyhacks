// Agent harness types — Pi Mono-inspired event-driven agent loop.

export interface AgentMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: ToolCall[];
  tool_results?: ToolResult[];
  tool_call_id?: string; // required for tool role messages (OpenAI format)
  createdAt: string;
}

export interface ToolCall {
  id: string;
  name: string;
  parameters: Record<string, unknown>;
}

export interface ToolResult {
  toolCallId: string;
  name: string;
  result: string;
}

export interface AgentTool {
  name: string;
  description: string;
  parameters: {
    type: string;
    properties: Record<string, { type: string; description?: string }>;
    required: string[];
  };
  execute: (params: Record<string, unknown>) => Promise<string>;
}

export type AgentEvent =
  | { type: 'thinking' }
  | { type: 'content'; text: string }
  | { type: 'tool_call'; tool: ToolCall }
  | { type: 'tool_result'; result: ToolResult }
  | { type: 'done'; messageId: string }
  | { type: 'error'; message: string };

export type AgentEventHandler = (event: AgentEvent) => void;

export interface ConversationNode {
  id: string;
  parentId: string | null;
  message: AgentMessage;
  children: string[];
}

export interface AgentConfig {
  model: 'fast' | 'thinking';
  systemPrompt: string;
  tools: AgentTool[];
  maxIterations: number;
  onEvent: AgentEventHandler;
}
