// Context builder — system prompt + RAG from Qdrant + pruning.
import type { AgentTool } from './types';
import { ragSearch } from '../services/assistant';

const SYSTEM_PROMPT_TEMPLATE = `You are an AI assistant for Hack the Valley, a hackathon.
You help participants with hackathon questions AND with writing code in their project sandbox.

## Your Tools
You have access to tools for:
- Answering hackathon questions (tracks, schedule, FAQ, submission, etc.)
- Writing and running code (read_file, write_file, edit_file, bash)

## Guidelines
- Be concise and helpful
- When asked to build something, write the code and explain what you did
- When the user asks about the hackathon, use the available tools to get accurate information
- RAG context below provides relevant hackathon information

## Hackathon Context
{RAG_CONTEXT}

## Current Date
{DATE}`;

export async function buildSystemPrompt(
  tools: AgentTool[],
  userQuery?: string
): Promise<string> {
  const date = new Date().toISOString().split('T')[0];
  let ragContext = '';

  if (userQuery) {
    try {
      const { documents } = await ragSearch(userQuery);
      ragContext = documents
        .map(d => `[${d.doc_type}] ${d.title}: ${d.content}`)
        .join('\n');
    } catch {
      ragContext = '(No additional context available)';
    }
  }

  return SYSTEM_PROMPT_TEMPLATE
    .replace('{RAG_CONTEXT}', ragContext || '(No additional context available)')
    .replace('{DATE}', date);
}

const APPROX_CHARS_PER_TOKEN = 4;
const MAX_CONTEXT_TOKENS = 6000;

export function pruneMessages(
  messages: Array<{ role: string; content: string }>,
  maxTokens: number = MAX_CONTEXT_TOKENS
): Array<{ role: string; content: string }> {
  let totalChars = messages.reduce((sum, m) => sum + m.content.length, 0);
  const pruned = [...messages];

  while (totalChars / APPROX_CHARS_PER_TOKEN > maxTokens && pruned.length > 2) {
    const sysIdx = pruned.findIndex(m => m.role !== 'system');
    if (sysIdx === -1) break;
    const removed = pruned.splice(sysIdx, 1)[0];
    totalChars -= removed.content.length;
  }

  return pruned;
}
