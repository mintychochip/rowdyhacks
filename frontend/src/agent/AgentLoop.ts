// Browser-native event-driven agent loop (Pi Mono pattern).
// pi-agent-core depends on node:fs (env-api-keys.js), so we build our own.

import type { AgentConfig, AgentEvent, AgentMessage } from './types';
import { llmChat } from '../services/assistant';

export class AgentLoop {
  private config: AgentConfig;
  private messages: AgentMessage[] = [];
  private abortController: AbortController | null = null;
  private running = false;
  conversationId?: string;

  constructor(config: AgentConfig) {
    this.config = config;
  }

  /** Send user message and start agent loop */
  async send(message: string): Promise<void> {
    if (this.running) return;
    this.running = true;
    this.abortController = new AbortController();

    try {
      const userMsg: AgentMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: message,
        createdAt: new Date().toISOString(),
      };
      this.messages.push(userMsg);

      let iterations = 0;
      while (iterations < this.config.maxIterations) {
        iterations++;
        const response = await this.callLLM();

        if (response.content) {
          this.emit({ type: 'content', text: response.content });
        }

        if (!response.toolCalls || response.toolCalls.length === 0) {
          const assistantMsg: AgentMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: response.content,
            toolCalls: response.toolCalls,
            createdAt: new Date().toISOString(),
          };
          this.messages.push(assistantMsg);
          this.emit({ type: 'done', messageId: assistantMsg.id });
          break;
        }

        const toolResults: Array<{ toolCallId: string; name: string; result: string }> = [];
        for (const tc of response.toolCalls) {
          this.emit({ type: 'tool_call', tool: tc });

          const tool = this.config.tools.find(t => t.name === tc.name);
          if (!tool) {
            toolResults.push({
              toolCallId: tc.id,
              name: tc.name,
              result: `Error: unknown tool "${tc.name}"`,
            });
            continue;
          }

          try {
            const result = await tool.execute(tc.parameters);
            toolResults.push({ toolCallId: tc.id, name: tc.name, result });
            this.emit({ type: 'tool_result', result: toolResults[toolResults.length - 1] });
          } catch (err) {
            const errMsg = err instanceof Error ? err.message : String(err);
            toolResults.push({ toolCallId: tc.id, name: tc.name, result: `Error: ${errMsg}` });
            this.emit({ type: 'tool_result', result: toolResults[toolResults.length - 1] });
          }
        }

        const assistantMsg: AgentMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.content,
          toolCalls: response.toolCalls,
          tool_results: toolResults,
          createdAt: new Date().toISOString(),
        };
        this.messages.push(assistantMsg);

        // Tool result messages (OpenAI requires tool_call_id for correlation)
        for (const tr of toolResults) {
          this.messages.push({
            id: crypto.randomUUID(),
            role: 'tool',
            content: tr.result,
            tool_call_id: tr.toolCallId,
            createdAt: new Date().toISOString(),
          });
        }
      }

      if (iterations >= this.config.maxIterations) {
        this.emit({ type: 'error', message: 'Agent reached maximum iterations' });
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      this.emit({ type: 'error', message: err instanceof Error ? err.message : String(err) });
    } finally {
      this.running = false;
    }
  }

  /** Stop the agent */
  stop(): void {
    this.abortController?.abort();
    this.running = false;
  }

  /** Get current conversation messages */
  getMessages(): AgentMessage[] {
    return [...this.messages];
  }

  /** Clear conversation */
  clear(): void {
    this.messages = [];
  }

  private emit(event: AgentEvent): void {
    this.config.onEvent(event);
  }

  private async callLLM(): Promise<{
    content: string;
    toolCalls?: Array<{ id: string; name: string; parameters: Record<string, unknown> }>;
  }> {
    const llmMessages: Array<{ role: string; content: string; tool_calls?: any[]; tool_call_id?: string }> = [
      { role: 'system', content: this.config.systemPrompt },
      ...this.messages.map(m => {
        const entry: { role: string; content: string; tool_calls?: any[]; tool_call_id?: string } = { role: m.role, content: m.content };
        if (m.toolCalls?.length) entry.tool_calls = m.toolCalls;
        if (m.tool_call_id) entry.tool_call_id = m.tool_call_id;
        return entry;
      }),
    ];

    const response = await llmChat(llmMessages, this.config.model, this.abortController?.signal);

    // Poolside returns OpenAI format: choices[0].message.{content, tool_calls}
    const msg = response.choices?.[0]?.message;
    if (!msg) return { content: '' };
    const toolCalls = msg.tool_calls?.map((tc: any) => ({
      id: tc.id,
      name: tc.function?.name ?? tc.name,
      parameters: typeof tc.function?.arguments === 'string'
        ? JSON.parse(tc.function.arguments)
        : (tc.parameters ?? {}),
    }));

    return { content: msg.content ?? '', toolCalls };
  }
}
