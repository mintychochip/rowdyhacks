// Tool registry for browser agent harness.
// Converts server tool definitions → executable browser tools.
// Code tools execute in WebContainer sandbox (Chrome/Edge only).

import type { AgentTool } from './types';
import type { Tool } from '../services/assistant';
import { sandbox } from './WebContainer';

const WEBCONTAINER_SUPPORTED =
  typeof window !== 'undefined' && 'SharedArrayBuffer' in window;

// Convert server tool definitions to executable browser tools
export function createHackathonTool(def: Tool, authToken: string): AgentTool {
  return {
    name: def.name,
    description: def.description,
    parameters: def.parameters,
    execute: async (params: Record<string, unknown>) => {
      const res = await fetch(`/api/assistant/execute-tool`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ tool_name: def.name, parameters: params }),
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(`Tool ${def.name} failed: ${err}`);
      }

      const data = await res.json();
      return JSON.stringify(data.result);
    },
  };
}

// Code tools — executed in WebContainer sandbox
export function createCodeTools(): AgentTool[] {
  if (!WEBCONTAINER_SUPPORTED) {
    const nope = 'Code tools require Chrome or Edge browser. Please switch browsers for coding features.';
    return [
      mkCodeTool('read_file', 'Read a file from the sandbox', { path: 'File path relative to project root' }, async () => nope),
      mkCodeTool('write_file', 'Create or overwrite a file in the sandbox', { path: 'File path', content: 'File contents' }, async () => nope),
      mkCodeTool('edit_file', 'Edit a file by replacing a string', { path: 'File path', old_string: 'String to replace', new_string: 'Replacement' }, async () => nope),
      mkCodeTool('bash', 'Run a shell command in the sandbox', { command: 'The shell command to run' }, async () => nope),
    ];
  }

  return [
    {
      name: 'read_file',
      description: 'Read a file from the project sandbox',
      parameters: {
        type: 'object',
        properties: { path: { type: 'string', description: 'File path relative to project root' } },
        required: ['path'],
      },
      execute: async (p) => await sandbox.readFile(p.path as string),
    },
    {
      name: 'write_file',
      description: 'Create or overwrite a file in the project sandbox',
      parameters: {
        type: 'object',
        properties: {
          path: { type: 'string', description: 'File path' },
          content: { type: 'string', description: 'File contents' },
        },
        required: ['path', 'content'],
      },
      execute: async (p) => {
        await sandbox.writeFile(p.path as string, p.content as string);
        return `Wrote ${p.path}`;
      },
    },
    {
      name: 'edit_file',
      description: 'Edit a file by replacing a string',
      parameters: {
        type: 'object',
        properties: {
          path: { type: 'string' },
          old_string: { type: 'string' },
          new_string: { type: 'string' },
        },
        required: ['path', 'old_string', 'new_string'],
      },
      execute: async (p) => {
        await sandbox.editFile(p.path as string, p.old_string as string, p.new_string as string);
        return `Edited ${p.path}`;
      },
    },
    {
      name: 'bash',
      description: 'Run a shell command in the sandbox',
      parameters: {
        type: 'object',
        properties: { command: { type: 'string', description: 'The shell command to run' } },
        required: ['command'],
      },
      execute: async (p) => {
        const { stdout, stderr, exitCode } = await sandbox.bash(p.command as string);
        if (exitCode !== 0) return `Exit ${exitCode}\nstdout: ${stdout}\nstderr: ${stderr}`;
        return stdout || '(command completed successfully)';
      },
    },
  ];
}

function mkCodeTool(
  name: string,
  description: string,
  props: Record<string, string>,
  execute: (params: Record<string, unknown>) => Promise<string>,
): AgentTool {
  return {
    name,
    description,
    parameters: {
      type: 'object',
      properties: Object.fromEntries(
        Object.entries(props).map(([k, desc]) => [k, { type: 'string', description: desc }])
      ),
      required: Object.keys(props),
    },
    execute,
  };
}
