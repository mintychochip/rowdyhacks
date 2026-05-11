// Auto-generated TypeScript SDK for OpenHack API
// Generated from FastAPI OpenAPI spec — do not edit manually.

/* eslint-disable */

/** Pydantic schema for creating a new announcement. */
/**  */
/** Behavior: */
/** 1. Stub schema with no fields until full announcement flow is restored. */
/** 2. Reserved for future fields: title, body, priority, target_audience. */
/**  */
/** Raises: ValidationError on unexpected extra fields if strict mode is enabled. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/announcements route, organizer broadcast panel. */
export interface AnnouncementCreate {
}

export interface ChatLogRequest {
  messages: Record<string, unknown>[];
  conversation_id?: string | null;
}

/** Pydantic schema for creating a new conflict-of-interest declaration. */
/**  */
/** Behavior: */
/** 1. Stub schema with no fields until full COI flow is restored. */
/** 2. Reserved for future fields: judge_id, team_id, reason. */
/**  */
/** Raises: ValidationError on unexpected extra fields if strict mode is enabled. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/coi route, judge declaration form. */
export interface ConflictOfInterestCreate {
}

export interface CreateCrawledHackathonRequest {
  devpost_url: string;
  name: string;
  start_date: string;
  end_date?: string | null;
}

export interface ExecuteToolRequest {
  tool_name: string;
  parameters?: Record<string, unknown>;
}

/** Request schema for project generation. */
export interface GenerateProjectRequest {
  /** The project plan to generate code for */
  plan: ProjectPlanSchema;
  /** Type of project to generate (e.g., 'react', 'python', 'fullstack') */
  projectType: string;
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

/** Pydantic schema for creating a new hackathon event. */
/**  */
/** Behavior: */
/** 1. Stub schema with no fields until full hackathon creation flow is restored. */
/** 2. Reserved for future fields: name, start_date, end_date, max_participants, url_slug. */
/**  */
/** Raises: ValidationError on unexpected extra fields if strict mode is enabled. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/hackathons route, organizer event wizard. */
export interface HackathonCreate {
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  version?: string;
  checks: Record<string, unknown>;
}

/** Pydantic schema for creating a new judging session. */
/**  */
/** Behavior: */
/** 1. Accepts a list of scoring criteria. */
/** 2. Passed to the judging session factory to initialize evaluation state. */
/**  */
/** Raises: ValidationError on type mismatches. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/judging/sessions route, admin judging panel. */
export interface JudgingSessionCreate {
  criteria?: unknown[];
}

export interface LLMChatRequest {
  messages: Record<string, unknown>[];
  model?: string;
}

/** Schema for a single task in a project plan. */
export interface PlanTaskSchema {
  /** Unique identifier for the task */
  id: string;
  /** Task description */
  description: string;
  /** Estimated time to complete in minutes */
  estimatedMinutes: number;
  /** Whether the task is completed */
  completed?: boolean;
  /** IDs of tasks that must complete before this one */
  dependencies?: string[] | null;
}

/** Schema for a complete project plan. */
export interface ProjectPlanSchema {
  /** Unique identifier for the plan */
  id: string;
  /** Project name */
  name: string;
  /** Project description */
  description: string;
  /** Target hackathon track */
  targetTrack: string;
  /** Estimated total hours to complete */
  estimatedHours: number;
  /** Recommended technologies */
  techStack: string[];
  /** List of tasks to complete */
  tasks: PlanTaskSchema[];
  /** Optional stretch goals */
  stretchGoals?: string[] | null;
}

export interface RAGSearchRequest {
  query: string;
}

/** Pydantic schema for creating a new hackathon registration. */
/**  */
/** Behavior: */
/** 1. Stub schema with no fields until full registration flow is restored. */
/** 2. Reserved for future fields: team_name, dietary_restrictions, etc. */
/**  */
/** Raises: ValidationError on unexpected extra fields if strict mode is enabled. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/registrations route, signup wizard. */
export interface RegistrationCreate {
}

/** Pydantic schema for a project submission request. */
/**  */
/** Behavior: */
/** 1. Validates the submitted project URL and optional hackathon_id. */
/** 2. Consumed by the submission endpoint to create or update a submission. */
/**  */
/** Raises: ValidationError if URL is missing or malformed. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/submit route, crawler trigger. */
export interface SubmitRequest {
  url: string;
  hackathon_id?: string | null;
}

/** Pydantic schema for submitting judge scores. */
/**  */
/** Behavior: */
/** 1. Accepts a list of score objects (criterion + value pairs). */
/** 2. Consumed by the scoring endpoint to persist judge evaluations. */
/**  */
/** Raises: ValidationError on missing scores or type mismatches. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/judging/score route, judge ballot form. */
export interface SubmitScoreRequest {
  scores?: unknown[];
}

/** Pydantic schema for a serialized user record. */
/**  */
/** Behavior: */
/** 1. Returns id, email, name, role, and created_at fields. */
/** 2. Used when the API needs to expose a user object without internal fields. */
/**  */
/** Raises: ValidationError on missing required fields or type mismatches. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: Auth routes, user lookup endpoints, leaderboard serializers. */
export interface UserResponse {
  id: string;
  email: string;
  name?: string | null;
  role?: string | null;
  created_at?: unknown | null;
}

export interface ValidationError {
  loc: string | number[];
  msg: string;
  type: string;
}

export class OpenHackClient {
  private baseUrl: string;

  /**
   * Create a new OpenHack API client.
   * @param baseUrl — API base URL (default: https://localhost/api)
   */
  constructor(baseUrl: string = 'https://localhost/api') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  /**
   * POST /api/assistant/chat — Create Chat Message
   * Create a new chat message and start processing.
   * Tags: assistant, assistant
   */
  async createChatMessageApiAssistantChatPost(message: string, conversation_id?: string | null, hackathon_id?: string | null, model?: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (message != null) params.append('message', String(message));
    if (conversation_id != null) params.append('conversation_id', String(conversation_id));
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    if (model != null) params.append('model', String(model));
    const url = `${this.baseUrl}/api/assistant/chat` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/assistant/chat-log — Chat Log
   * Persist a conversation from the browser agent.
   * Tags: assistant, assistant
   */
  async chatLogApiAssistantChatLogPost(body: { messages: Record<string, unknown>[]; conversation_id?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/assistant/chat-log`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/assistant/detect-intent — Detect Intent
   * Detect if user message indicates intent to build a project.
   * Tags: assistant, assistant
   */
  async detectIntentApiAssistantDetectIntentPost(message: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (message != null) params.append('message', String(message));
    const url = `${this.baseUrl}/api/assistant/detect-intent` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/assistant/execute-tool — Execute Tool
   * Execute a single tool. Auth and permission checked server-side.
   * Tags: assistant, assistant
   */
  async executeToolApiAssistantExecuteToolPost(body: { tool_name: string; parameters?: Record<string, unknown> }): Promise<unknown> {
    const url = `${this.baseUrl}/api/assistant/execute-tool`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/assistant/generate-plan — Generate Plan
   * Generate a project plan from user description.
   * Tags: assistant, assistant
   */
  async generatePlanApiAssistantGeneratePlanPost(description: string, hackathon_id?: string | null): Promise<unknown> {
    const params = new URLSearchParams();
    if (description != null) params.append('description', String(description));
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/assistant/generate-plan` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/assistant/generate-project — Generate Project
   * Generate project files from a plan.
   * Tags: assistant, assistant
   */
  async generateProjectApiAssistantGenerateProjectPost(body: { plan: { id: string; name: string; description: string; targetTrack: string; estimatedHours: number; techStack: string[]; tasks: { id: string; description: string; estimatedMinutes: number; completed?: boolean; dependencies?: string[] | null }[]; stretchGoals?: string[] | null }; projectType: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/assistant/generate-project`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/assistant/history — List Conversations
   * List user's conversation history.
   * Tags: assistant, assistant
   */
  async listConversationsApiAssistantHistoryGet(limit?: number, offset?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (limit != null) params.append('limit', String(limit));
    if (offset != null) params.append('offset', String(offset));
    const url = `${this.baseUrl}/api/assistant/history` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/assistant/history/{conversation_id} — Get Conversation
   * Get a specific conversation with all messages.
   * Tags: assistant, assistant
   */
  async getConversationApiAssistantHistoryConversationIdGet(conversation_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/assistant/history/${conversation_id}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * DELETE /api/assistant/history/{conversation_id} — Delete Conversation
   * Delete a conversation and all its messages.
   * Tags: assistant, assistant
   */
  async deleteConversationApiAssistantHistoryConversationIdDelete(conversation_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/assistant/history/${conversation_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/assistant/rag-search — Rag Search
   * Search Qdrant for relevant hackathon documents.
   * Tags: assistant, assistant
   */
  async ragSearchApiAssistantRagSearchPost(hackathon_id: string | null, body: { query: string }): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/assistant/rag-search` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/assistant/stream/{message_id} — Stream Response
   * Stream the assistant response for a message.
   * Tags: assistant, assistant
   */
  async streamResponseApiAssistantStreamMessageIdGet(message_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/assistant/stream/${message_id}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/assistant/tools — List Available Tools
   * List tools available to the current user.
   * Tags: assistant, assistant
   */
  async listAvailableToolsApiAssistantToolsGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/assistant/tools`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/auth/me — Get Me
   * Return the current authenticated user. Clerk-only with auto-create fallback.
   * Tags: auth
   */
  async getMeApiAuthMeGet(): Promise<{ id: string; email: string; name?: string | null; role?: string | null; created_at?: unknown | null }> {
    const url = `${this.baseUrl}/api/auth/me`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/check — Submit For Check
   * Submit a Devpost or GitHub URL for analysis.
   * Tags: checks
   */
  async submitForCheckApiCheckPost(body: { url: string; hackathon_id?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/check`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/check/{submission_id} — Get Check Status
   * Get submission status and check results.
   * Tags: checks
   */
  async getCheckStatusApiCheckSubmissionIdGet(submission_id: string, token?: string | null): Promise<unknown> {
    const params = new URLSearchParams();
    if (token != null) params.append('token', String(token));
    const url = `${this.baseUrl}/api/check/{submission_id}` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/check/{submission_id}/report — Get Check Report
   * Get full report JSON for a submission.
   * 
   * Access rules:
   * - If no access_token is set on submission: public
   * - If token query param matches: access granted
   * - If Authorization header has valid organizer JWT: access granted
   * - Otherwise: access denied
   * Tags: checks
   */
  async getCheckReportApiCheckSubmissionIdReportGet(submission_id: string, token?: string | null): Promise<unknown> {
    const params = new URLSearchParams();
    if (token != null) params.append('token', String(token));
    const url = `${this.baseUrl}/api/check/{submission_id}/report` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/check/{submission_id}/retry — Retry Check
   * Retry a failed submission.
   * Tags: checks
   */
  async retryCheckApiCheckSubmissionIdRetryPost(submission_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/check/${submission_id}/retry`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/checkin/scan — Scan Qr
   * Scan a QR code to check in. Token is validated from JWT signature.
   * Tags: checkin
   */
  async scanQrApiCheckinScanPost(token: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (token != null) params.append('token', String(token));
    const url = `${this.baseUrl}/api/checkin/scan` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/config/ — Get All Config
   * Tags: config
   */
  async getAllConfigApiConfigGet(category?: string | null): Promise<unknown> {
    const params = new URLSearchParams();
    if (category != null) params.append('category', String(category));
    const url = `${this.baseUrl}/api/config/` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * PUT /api/config/ — Update Config
   * Tags: config
   */
  async updateConfigApiConfigPut(body: Record<string, string>): Promise<unknown> {
    const url = `${this.baseUrl}/api/config/`;
    const res = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/config/assets — Upload Asset
   * Tags: config
   */
  async uploadAssetApiConfigAssetsPost(file: File | Blob, key?: string | null): Promise<unknown> {
    const formData = new FormData();
    if (file != null) formData.append('file', file);
    if (key != null) formData.append('key', key);
    const url = `${this.baseUrl}/api/config/assets`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
      body: formData,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/config/branding — Get Branding
   * Backward-compat branding endpoint (deprecated).
   * Tags: config
   */
  async getBrandingApiConfigBrandingGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/config/branding`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/config/custom.css — Get Custom Css
   * Return custom CSS if set.
   * Tags: config
   */
  async getCustomCssApiConfigCustomCssGet(): Promise<string> {
    const url = `${this.baseUrl}/api/config/custom.css`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.text();
  }

  /**
   * GET /api/config/keys/{key} — Get Single Key
   * Tags: config
   */
  async getSingleKeyApiConfigKeysKeyGet(key: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/config/keys/${key}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/config/manifest.json — Get Manifest
   * Dynamic Web App Manifest from site config.
   * Tags: config
   */
  async getManifestApiConfigManifestJsonGet(): Promise<Record<string, unknown>> {
    const url = `${this.baseUrl}/api/config/manifest.json`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/config/theme.css — Get Theme Css
   * Generate CSS custom properties from theme config.
   * Tags: config
   */
  async getThemeCssApiConfigThemeCssGet(): Promise<string> {
    const url = `${this.baseUrl}/api/config/theme.css`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.text();
  }

  /**
   * GET /api/content/pages — List Pages
   * List content pages, optionally filtered by tab_group.
   * Tags: content
   */
  async listPagesApiContentPagesGet(tab_group?: string | null): Promise<unknown> {
    const params = new URLSearchParams();
    if (tab_group != null) params.append('tab_group', String(tab_group));
    const url = `${this.baseUrl}/api/content/pages` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/content/pages — Create Page
   * Create a new content page (organizer only).
   * Tags: content
   */
  async createPageApiContentPagesPost(body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/content/pages`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/content/pages/{slug} — Get Page
   * Get a single content page by slug.
   * Tags: content
   */
  async getPageApiContentPagesSlugGet(slug: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/content/pages/${slug}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * PUT /api/content/pages/{slug} — Update Page
   * Update a content page (organizer only).
   * Tags: content
   */
  async updatePageApiContentPagesSlugPut(slug: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/content/pages/${slug}`;
    const res = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * DELETE /api/content/pages/{slug} — Delete Page
   * Delete a content page (organizer only).
   * Tags: content
   */
  async deletePageApiContentPagesSlugDelete(slug: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/content/pages/${slug}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/crawler/hackathons — List Crawled Hackathons
   * List all crawled hackathons with project counts.
   * Tags: crawler
   */
  async listCrawledHackathonsApiCrawlerHackathonsGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/crawler/hackathons`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/crawler/hackathons — Create Crawled Hackathon
   * Manually add a crawled hackathon (admin/debug use).
   * Tags: crawler
   */
  async createCrawledHackathonApiCrawlerHackathonsPost(body: { devpost_url: string; name: string; start_date: string; end_date?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/crawler/hackathons`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/crawler/hackathons/{hackathon_id}/projects — List Crawled Projects
   * List projects for a specific crawled hackathon.
   * Tags: crawler
   */
  async listCrawledProjectsApiCrawlerHackathonsHackathonIdProjectsGet(hackathon_id: string, offset?: number, limit?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (offset != null) params.append('offset', String(offset));
    if (limit != null) params.append('limit', String(limit));
    const url = `${this.baseUrl}/api/crawler/hackathons/{hackathon_id}/projects` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/crawler/projects — Search Crawled Projects
   * Search crawled projects by title.
   * Tags: crawler
   */
  async searchCrawledProjectsApiCrawlerProjectsGet(q?: string, offset?: number, limit?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (q != null) params.append('q', String(q));
    if (offset != null) params.append('offset', String(offset));
    if (limit != null) params.append('limit', String(limit));
    const url = `${this.baseUrl}/api/crawler/projects` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/crawler/trigger — Trigger Crawl
   * Manually trigger a full crawl cycle (organizer-only).
   * 
   * Returns 409 if a crawl is already running.
   * Tags: crawler
   */
  async triggerCrawlApiCrawlerTriggerPost(): Promise<unknown> {
    const url = `${this.baseUrl}/api/crawler/trigger`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/dashboard — Get Dashboard
   * Get paginated submissions list. Organizer only.
   * Tags: dashboard
   */
  async getDashboardApiDashboardGet(hackathon_id?: string | null, status?: string | null, verdict?: string | null, page?: number, per_page?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    if (status != null) params.append('status', String(status));
    if (verdict != null) params.append('verdict', String(verdict));
    if (page != null) params.append('page', String(page));
    if (per_page != null) params.append('per_page', String(per_page));
    const url = `${this.baseUrl}/api/dashboard` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/discord/bot-status — Bot Status
   * Check Discord bot connection state.
   */
  async botStatusApiDiscordBotStatusGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/discord/bot-status`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/discord/invite-url — Discord Invite Url
   * Get the Discord bot invite URL.
   */
  async discordInviteUrlApiDiscordInviteUrlGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/discord/invite-url`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons — List Hackathons
   * List all hackathons.
   * Tags: hackathons
   */
  async listHackathonsApiHackathonsGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons — Create Hackathon
   * Create a new hackathon.
   * Tags: hackathons
   */
  async createHackathonApiHackathonsPost(body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id} — Get Hackathon
   * Get a single hackathon by ID.
   * Tags: hackathons
   */
  async getHackathonApiHackathonsHackathonIdGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * PUT /api/hackathons/{hackathon_id} — Update Hackathon
   * Update hackathon settings (schedule, wifi, discord, webhook, deadline, capacity).
   * Tags: hackathons
   */
  async updateHackathonApiHackathonsHackathonIdPut(hackathon_id: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}`;
    const res = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/announcements — List Announcements
   * List announcements for a hackathon. Organizers see all, participants see accepted ones.
   * Tags: hackathons
   */
  async listAnnouncementsApiHackathonsHackathonIdAnnouncementsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/announcements`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/announcements — Create Announcement
   * Create and send an announcement to all hackathon participants (organizer only).
   * Tags: hackathons
   */
  async createAnnouncementApiHackathonsHackathonIdAnnouncementsPost(hackathon_id: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/announcements`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/conflicts-of-interest — List Conflicts Of Interest
   * List all conflicts of interest for a hackathon (organizer only).
   * Tags: hackathons
   */
  async listConflictsOfInterestApiHackathonsHackathonIdConflictsOfInterestGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/conflicts-of-interest`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/conflicts-of-interest — Declare Conflict Of Interest
   * Declare a conflict of interest for a submission (judge only).
   * Tags: hackathons
   */
  async declareConflictOfInterestApiHackathonsHackathonIdConflictsOfInterestPost(hackathon_id: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/conflicts-of-interest`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * DELETE /api/hackathons/{hackathon_id}/conflicts-of-interest/{coi_id} — Remove Conflict Of Interest
   * Remove a conflict of interest declaration (organizer or the judge who created it).
   * Tags: hackathons
   */
  async removeConflictOfInterestApiHackathonsHackathonIdConflictsOfInterestCoiIdDelete(hackathon_id: string, coi_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/conflicts-of-interest/${coi_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/hacker-dashboard — Get Hacker Dashboard
   * Get the hacker dashboard for the current user's registration at a hackathon.
   * 
   * Returns hackathon details (schedule, wifi, discord) + registration (QR, scan_count, scans).
   * Tags: hacker-dashboard
   */
  async getHackerDashboardApiHackathonsHackathonIdHackerDashboardGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/hacker-dashboard`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/import-devpost — Import Devpost Submissions
   * Scrape the Devpost hackathon gallery and import project URLs for analysis.
   * Tags: hackathons
   */
  async importDevpostSubmissionsApiHackathonsHackathonIdImportDevpostPost(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/import-devpost`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/judging/activate — Activate Judging
   * Activate judging and auto-assign all judges to all completed submissions.
   * Tags: judging
   */
  async activateJudgingApiHackathonsHackathonIdJudgingActivatePost(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/judging/activate`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/judging/assign — Assign Judges
   * Assign judges to submissions. Body: {"judge_ids": [...], "submission_ids": [...]}.
   * 
   * Creates assignments for every judge×submission pair.
   * Automatically creates JudgeRating records for new judges.
   * Tags: judging
   */
  async assignJudgesApiHackathonsHackathonIdJudgingAssignPost(hackathon_id: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/judging/assign`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/judging/assignments — List Judge Assignments
   * List assignments for a judging session. Filter by judge_id query param.
   * Tags: judging
   */
  async listJudgeAssignmentsApiHackathonsHackathonIdJudgingAssignmentsGet(hackathon_id: string, judge_id?: string | null, include_completed?: boolean): Promise<unknown> {
    const params = new URLSearchParams();
    if (judge_id != null) params.append('judge_id', String(judge_id));
    if (include_completed != null) params.append('include_completed', String(include_completed));
    const url = `${this.baseUrl}/api/hackathons/{hackathon_id}/judging/assignments` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/judging/close — Close Judging
   * Manually close judging to prevent further scoring.
   * Tags: judging
   */
  async closeJudgingApiHackathonsHackathonIdJudgingClosePost(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/judging/close`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/judging/queue — Get Judging Queue
   * Return a priority-ordered list of submissions that need more judging.
   * 
   * Query params:
   *   - judge_id (required): only return projects this judge hasn't scored
   *   - min_judges (default 3): minimum judge count before coverage is satisfied
   * 
   * Each item includes:
   *   - submission info (id, title, url)
   *   - current ELO
   *   - uncertainty breakdown (variance, proximity, coverage)
   *   - priority score (higher = needs judging more urgently)
   * Tags: judging
   */
  async getJudgingQueueApiHackathonsHackathonIdJudgingQueueGet(hackathon_id: string, judge_id: string, min_judges?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (judge_id != null) params.append('judge_id', String(judge_id));
    if (min_judges != null) params.append('min_judges', String(min_judges));
    const url = `${this.baseUrl}/api/hackathons/{hackathon_id}/judging/queue` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/judging/rerun — Rerun Judging
   * Create new assignments for projects flagged by the ELO uncertainty engine.
   * 
   * For each submission with fewer than min_judges scores, creates a new
   * JudgeAssignment for every judge who hasn't scored it yet.
   * Preserves existing scores (each round gets new assignment records).
   * Tags: judging
   */
  async rerunJudgingApiHackathonsHackathonIdJudgingRerunPost(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/judging/rerun`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/judging/results — Get Judging Results
   * Compute and return ELO rankings for the hackathon.
   * 
   * Algorithm:
   *   1. Load all completed assignments with scores.
   *   2. Compute raw weighted score per (judge, submission).
   *   3. Z-score normalize within each judge (judge severity correction).
   *   4. Within-judge pairwise ELO updates.
   *   5. Cross-judge bridging via submissions scored by multiple judges.
   *   6. Return final ELO rankings.
   * Tags: judging
   */
  async getJudgingResultsApiHackathonsHackathonIdJudgingResultsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/judging/results`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/judging/session — Get Judging Session Route
   * Get the judging session configuration for a hackathon.
   * Tags: judging
   */
  async getJudgingSessionRouteApiHackathonsHackathonIdJudgingSessionGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/judging/session`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/judging/session — Create Judging Session
   * Create or replace a judging session with rubric criteria for a hackathon.
   * Tags: judging
   */
  async createJudgingSessionApiHackathonsHackathonIdJudgingSessionPost(hackathon_id: string, body: { criteria?: unknown[] }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/judging/session`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/organizers — List Organizers
   * List all organizers for a hackathon (primary + co-organizers).
   * Tags: hackathons
   */
  async listOrganizersApiHackathonsHackathonIdOrganizersGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/organizers`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/organizers — Add Organizer
   * Add a co-organizer to the hackathon (primary organizer only).
   * Tags: hackathons
   */
  async addOrganizerApiHackathonsHackathonIdOrganizersPost(hackathon_id: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/organizers`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * DELETE /api/hackathons/{hackathon_id}/organizers/{user_id} — Remove Organizer
   * Remove a co-organizer (primary organizer only).
   * Tags: hackathons
   */
  async removeOrganizerApiHackathonsHackathonIdOrganizersUserIdDelete(hackathon_id: string, user_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/organizers/${user_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/register — Register For Hackathon
   * Register current user for a hackathon.
   * Tags: registrations
   */
  async registerForHackathonApiHackathonsHackathonIdRegisterPost(hackathon_id: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/register`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/registrations — List Hackathon Registrations
   * List registrations for a hackathon. Organizer only, RLS: own hackathons only.
   * Tags: organizer-registrations
   */
  async listHackathonRegistrationsApiHackathonsHackathonIdRegistrationsGet(hackathon_id: string, status?: string | null, offset?: number, limit?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (status != null) params.append('status', String(status));
    if (offset != null) params.append('offset', String(offset));
    if (limit != null) params.append('limit', String(limit));
    const url = `${this.baseUrl}/api/hackathons/{hackathon_id}/registrations` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/registrations/bulk-accept — Bulk Accept Registrations
   * Bulk accept pending registrations.
   * Tags: hackathons
   */
  async bulkAcceptRegistrationsApiHackathonsHackathonIdRegistrationsBulkAcceptPost(hackathon_id: string, body: string[]): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/bulk-accept`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/registrations/bulk-reject — Bulk Reject Registrations
   * Bulk reject pending/waitlisted registrations.
   * Tags: hackathons
   */
  async bulkRejectRegistrationsApiHackathonsHackathonIdRegistrationsBulkRejectPost(hackathon_id: string, body: string[]): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/bulk-reject`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/registrations/bulk-waitlist — Bulk Waitlist Registrations
   * Bulk waitlist pending registrations.
   * Tags: hackathons
   */
  async bulkWaitlistRegistrationsApiHackathonsHackathonIdRegistrationsBulkWaitlistPost(hackathon_id: string, body: string[]): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/bulk-waitlist`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/registrations/export — Export Registrations Csv
   * Export all registrations to CSV (organizer only).
   * Tags: hackathons
   */
  async exportRegistrationsCsvApiHackathonsHackathonIdRegistrationsExportGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/export`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/accept — Accept Registration
   * Approve a registration and generate QR token. Organizer only.
   * Tags: organizer-registrations
   */
  async acceptRegistrationApiHackathonsHackathonIdRegistrationsRegistrationIdAcceptPost(hackathon_id: string, registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/accept`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/checkin — Checkin Registration
   * Check in a registration. Organizer only.
   * Tags: organizer-registrations
   */
  async checkinRegistrationApiHackathonsHackathonIdRegistrationsRegistrationIdCheckinPost(hackathon_id: string, registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/checkin`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/reject — Reject Registration
   * Reject a registration. Organizer only.
   * Tags: organizer-registrations
   */
  async rejectRegistrationApiHackathonsHackathonIdRegistrationsRegistrationIdRejectPost(hackathon_id: string, registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/reject`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/unwaitlist — Remove From Waitlist
   * Move a waitlisted registration back to pending. Organizer only.
   * Tags: organizer-registrations
   */
  async removeFromWaitlistApiHackathonsHackathonIdRegistrationsRegistrationIdUnwaitlistPost(hackathon_id: string, registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/unwaitlist`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/waitlist — Move To Waitlist
   * Move a pending registration to waitlist. Organizer only.
   * Tags: organizer-registrations
   */
  async moveToWaitlistApiHackathonsHackathonIdRegistrationsRegistrationIdWaitlistPost(hackathon_id: string, registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/waitlist`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/similarity — Run Hackathon Similarity
   * Run cross-team similarity checks for all completed submissions.
   * 
   * Detects duplicate GitHub URLs, same repo name patterns, and overlapping
   * commit hashes. Stores results in the database and updates risk scores /
   * verdicts on flagged submissions.
   * Tags: hackathons
   */
  async runHackathonSimilarityApiHackathonsHackathonIdSimilarityPost(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/similarity`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/stats — Get Hackathon Stats
   * Get aggregate stats for a hackathon.
   * Tags: hackathons
   */
  async getHackathonStatsApiHackathonsHackathonIdStatsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/stats`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/submissions — Get Hackathon Submissions
   * List submissions for a hackathon.
   * Tags: hackathons
   */
  async getHackathonSubmissionsApiHackathonsHackathonIdSubmissionsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/submissions`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/swag-counts — Get Swag Counts
   * Get meal and swag planning counts (organizer only).
   * Tags: hackathons
   */
  async getSwagCountsApiHackathonsHackathonIdSwagCountsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/swag-counts`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/tracks — List Tracks
   * Tags: tracks
   */
  async listTracksApiHackathonsHackathonIdTracksGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/tracks`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/tracks — Create Track
   * Tags: tracks
   */
  async createTrackApiHackathonsHackathonIdTracksPost(hackathon_id: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/tracks`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * PUT /api/hackathons/{hackathon_id}/tracks/{track_id} — Update Track
   * Tags: tracks
   */
  async updateTrackApiHackathonsHackathonIdTracksTrackIdPut(hackathon_id: string, track_id: string, body: Record<string, unknown>): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/tracks/${track_id}`;
    const res = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * DELETE /api/hackathons/{hackathon_id}/tracks/{track_id} — Delete Track
   * Tags: tracks
   */
  async deleteTrackApiHackathonsHackathonIdTracksTrackIdDelete(hackathon_id: string, track_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/tracks/${track_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/hackathons/{hackathon_id}/waitlist — List Waitlist
   * List waitlisted registrations with position. Organizer only.
   * Tags: organizer-registrations
   */
  async listWaitlistApiHackathonsHackathonIdWaitlistGet(hackathon_id: string, offset?: number, limit?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (offset != null) params.append('offset', String(offset));
    if (limit != null) params.append('limit', String(limit));
    const url = `${this.baseUrl}/api/hackathons/{hackathon_id}/waitlist` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/hackathons/{hackathon_id}/waitlist/promote — Manual Promote Waitlist
   * Manually promote top waitlisted person to offered. Organizer only.
   * Tags: organizer-registrations
   */
  async manualPromoteWaitlistApiHackathonsHackathonIdWaitlistPromotePost(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/waitlist/promote`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/health — Health
   */
  async healthApiHealthGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/health`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/judging/assignments/{assignment_id} — Get Assignment Detail
   * Get full assignment detail including submission info, rubric criteria, and existing scores.
   * Tags: judging
   */
  async getAssignmentDetailApiJudgingAssignmentsAssignmentIdGet(assignment_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/judging/assignments/${assignment_id}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/judging/assignments/{assignment_id}/open — Open Assignment
   * Mark an assignment as opened by the judge (starts the timer).
   * Tags: judging
   */
  async openAssignmentApiJudgingAssignmentsAssignmentIdOpenPost(assignment_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/judging/assignments/${assignment_id}/open`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/judging/assignments/{assignment_id}/score — Submit Scores
   * Submit or update scores for an assignment. Can be called incrementally.
   * 
   * Auto-submits (marks complete) when all criteria have non-null scores.
   * Also checks per_project_seconds soft deadline.
   * Tags: judging
   */
  async submitScoresApiJudgingAssignmentsAssignmentIdScorePost(assignment_id: string, body: { scores?: unknown[] }): Promise<unknown> {
    const url = `${this.baseUrl}/api/judging/assignments/${assignment_id}/score`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/llm/chat — Llm Chat Proxy
   * Proxy LLM chat requests to Poolside.
   * 
   * Strips client tool defs, injects server-authorized ones.
   * Validates Clerk JWT.
   * Tags: llm
   */
  async llmChatProxyApiLlmChatPost(body: { messages: Record<string, unknown>[]; model?: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/llm/chat`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/monitoring/health — Health Check
   * Comprehensive health check including database and Redis.
   * Tags: monitoring
   */
  async healthCheckApiMonitoringHealthGet(): Promise<{ status: string; timestamp: string; version?: string; checks: Record<string, unknown> }> {
    const url = `${this.baseUrl}/api/monitoring/health`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/monitoring/live — Liveness Check
   * Kubernetes-style liveness probe.
   * Tags: monitoring
   */
  async livenessCheckApiMonitoringLiveGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/monitoring/live`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/monitoring/metrics — Get Metrics
   * Application metrics (Prometheus-compatible format).
   * Tags: monitoring
   */
  async getMetricsApiMonitoringMetricsGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/monitoring/metrics`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/monitoring/metrics/prometheus — Prometheus Metrics
   * Prometheus-formatted metrics endpoint.
   * Tags: monitoring
   */
  async prometheusMetricsApiMonitoringMetricsPrometheusGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/monitoring/metrics/prometheus`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/monitoring/ready — Readiness Check
   * Kubernetes-style readiness probe.
   * Tags: monitoring
   */
  async readinessCheckApiMonitoringReadyGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/monitoring/ready`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/monitoring/version — Version
   * Get application version and build info.
   * Tags: monitoring
   */
  async versionApiMonitoringVersionGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/monitoring/version`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/qr — Get Qr Image
   * Serve a QR code PNG image for the given data.
   * Tags: qr
   */
  async getQrImageApiQrGet(data: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (data != null) params.append('data', String(data));
    const url = `${this.baseUrl}/api/qr` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/registrations — List My Registrations
   * List registrations for the current user. RLS: own registrations only.
   * Tags: registrations
   */
  async listMyRegistrationsApiRegistrationsGet(offset?: number, limit?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (offset != null) params.append('offset', String(offset));
    if (limit != null) params.append('limit', String(limit));
    const url = `${this.baseUrl}/api/registrations` + (params.toString() ? `?${params.toString()}` : '');
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * GET /api/registrations/{registration_id} — Get Registration
   * Get a single registration. RLS: own only.
   * Tags: registrations
   */
  async getRegistrationApiRegistrationsRegistrationIdGet(registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/registrations/${registration_id}`;
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/{registration_id}/accept-offer — Accept Offer
   * Participant accepts an offered spot from waitlist promotion.
   * Tags: registrations
   */
  async acceptOfferApiRegistrationIdAcceptOfferPost(registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/${registration_id}/accept-offer`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }

  /**
   * POST /api/{registration_id}/decline-offer — Decline Offer
   * Participant declines an offered spot. Returns to waitlist with lower priority.
   * Tags: registrations
   */
  async declineOfferApiRegistrationIdDeclineOfferPost(registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/${registration_id}/decline-offer`;
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return res.json();
  }


  /** GET /api/config */
  async getConfig(): Promise<Record<string, string>> {
    return this.getAllConfigApiConfigGet();
  }

  /** GET /api/config/theme.css */
  async getThemeCss(): Promise<string> {
    return this.getThemeCssApiConfigThemeCssGet();
  }

  /** PUT /api/config */
  async updateConfig(updates: Record<string, string>): Promise<{ updated: string[] }> {
    return this.updateConfigApiConfigPut(updates);
  }

  /** POST /api/config/assets */
  async uploadAsset(file: File | Blob, key?: string | null): Promise<{ key: string; url: string }> {
    return this.uploadAssetApiConfigAssetsPost(file, key);
  }

  /** GET /api/config/branding */
  async getBranding(): Promise<BrandingResponse> {
    return this.getBrandingApiConfigBrandingGet();
  }

}

export default OpenHackClient;