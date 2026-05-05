// ============================================================
// Builder Service - API functions for AI project generation
// ============================================================

import type { ProjectPlan, ProjectFile } from '../types/builder';

const BASE = import.meta.env.VITE_API_URL || '/api';

export interface GeneratePlanRequest {
  description: string;
  project_name?: string;
  hackathon_id?: string;
}

export interface GeneratePlanResponse {
  plan: ProjectPlan;
}

export interface GenerateProjectRequest {
  plan: ProjectPlan;
}

export interface GenerateProjectResponse {
  files: ProjectFile[];
  readme: string;
}

// Generate a project plan from a description
export async function generatePlan(description: string): Promise<GeneratePlanResponse> {
  const token = localStorage.getItem('auth_token') || '';

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout for plan generation

  try {
    const res = await fetch(`${BASE}/assistant/generate-plan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ description } as GeneratePlanRequest),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const errorText = await res.text();
      let errorMessage = 'Failed to generate plan';
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
      throw new Error('Request timed out - plan generation is taking too long. Please try again.');
    }
    throw error;
  }
}

// Generate project files from a plan
export async function generateProject(plan: ProjectPlan): Promise<GenerateProjectResponse> {
  const token = localStorage.getItem('auth_token') || '';

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout for project generation

  try {
    const res = await fetch(`${BASE}/assistant/generate-project`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ plan } as GenerateProjectRequest),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const errorText = await res.text();
      let errorMessage = 'Failed to generate project';
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
      throw new Error('Request timed out - project generation is taking too long. Please try again.');
    }
    throw error;
  }
}
