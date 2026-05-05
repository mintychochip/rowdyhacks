// Minimal context builder — extended in Task 6 (Chunk 2) with RAG + pruning.
import type { AgentTool } from './types';

const SYSTEM_PROMPT_TEMPLATE = `You are an AI assistant for Hack the Valley, a hackathon.
You help participants with hackathon questions AND with writing code in their project sandbox.

## Guidelines
- Be concise and helpful
- When asked to build something, write the code and explain what you did
- When the user asks about the hackathon, use the available tools to get accurate information

## Current Date
{DATE}`;

export async function buildSystemPrompt(
  _tools: AgentTool[],
  _userQuery?: string
): Promise<string> {
  const date = new Date().toISOString().split('T')[0];
  return SYSTEM_PROMPT_TEMPLATE.replace('{DATE}', date);
}
