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

/** Pydantic schema returned after a successful branding asset upload. */
/**  */
/** Behavior: */
/** 1. Returns the config key and public URL for the uploaded asset. */
/** 2. Typically used for logo or favicon uploads. */
/**  */
/** Raises: ValidationError on missing key or url. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/config/assets route, admin asset manager. */
export interface AssetUploadResponse {
  key: string;
  url: string;
}

/** Pydantic schema for public hackathon branding configuration. */
/**  */
/** Behavior: */
/** 1. Returns seven branding fields: name, tagline, email, primary color, logo URL, favicon URL, year. */
/** 2. Consumed by the frontend theme initialization and layout components. */
/**  */
/** Raises: ValidationError on missing fields or type mismatches. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: GET /api/config/branding route, frontend theme.ts, Layout component. */
export interface BrandingResponse {
  hackathon_name: string;
  hackathon_tagline: string;
  hackathon_email: string;
  hackathon_primary_color: string;
  hackathon_logo_url: string;
  hackathon_favicon_url: string;
  hackathon_year: number;
}

export interface ChatLogRequest {
  messages: Record<string, unknown>[];
  conversation_id?: string | null;
}

/** Pydantic schema for a single key-value configuration entry. */
/**  */
/** Behavior: */
/** 1. Returns the config key and its stored string value. */
/** 2. Used when the client requests one specific setting. */
/**  */
/** Raises: ValidationError on missing key or value. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: GET /api/config/{key} route. */
export interface ConfigKeyResponse {
  key: string;
  value: string;
}

/** Pydantic schema confirming a batch configuration update. */
/**  */
/** Behavior: */
/** 1. Returns the list of keys that were successfully updated. */
/** 2. Lets the frontend know which settings changed. */
/**  */
/** Raises: ValidationError if updated list is missing. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: PUT /api/config route, admin configuration panel. */
export interface ConfigUpdateResponse {
  updated: string[];
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

export interface CreateHelpRequestRequest {
  hackathon_id: string;
  title: string;
  description?: string | null;
}

export interface CreatePrizeRequest {
  hackathon_id: string;
  name: string;
  description?: string | null;
  amount?: string | null;
  currency?: string;
  track_id?: string | null;
}

export interface CreateSponsorRequest {
  hackathon_id: string;
  name: string;
  tier?: string;
  logo_url?: string | null;
  website_url?: string | null;
  description?: string | null;
}

export interface CreateTeamRequest {
  hackathon_id: string;
  name: string;
}

export interface CreateWorkshopRequest {
  hackathon_id: string;
  title: string;
  description?: string | null;
  start_time: string;
  end_time: string;
  location?: string | null;
  speaker_name?: string | null;
}

/** Pydantic schema for a single rubric criterion. */
/**  */
/** Behavior: */
/** 1. Defines name, description, max_score, weight, and sort_order. */
/** 2. Consumed by JudgingSessionCreate to build the full rubric. */
/**  */
/** Raises: ValidationError on type mismatches. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
export interface CriterionCreate {
  name: string;
  description?: string;
  max_score?: number;
  weight?: number;
  sort_order?: number;
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

export interface JoinTeamRequest {
  join_code: string;
}

/** Pydantic schema for creating a new judging session. */
/**  */
/** Behavior: */
/** 1. Accepts timing, settings, and a list of scoring criteria. */
/** 2. Passed to the judging session factory to initialize evaluation state. */
/**  */
/** Raises: ValidationError on type mismatches. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/judging/sessions route, admin judging panel. */
export interface JudgingSessionCreate {
  start_time: string;
  end_time: string;
  per_project_seconds?: number;
  leaderboard_public?: boolean;
  criteria?: CriterionCreate[];
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

export interface RegisterPluginRequest {
  name: string;
  version?: string;
  description?: string | null;
  enabled?: boolean;
  config?: Record<string, unknown> | null;
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

export interface RestoreRequest {
  data: Record<string, unknown>;
}

/** Pydantic schema for a single criterion score. */
/**  */
/** Behavior: */
/** 1. Maps a criterion_id to a numeric score. */
/** 2. Consumed by SubmitScoreRequest. */
/**  */
/** Raises: ValidationError on type mismatches. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
export interface ScoreItem {
  criterion_id: string;
  score: number;
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
  scores?: ScoreItem[];
}

export interface SubscribeRequest {
  url: string;
  secret: string;
  events: string[];
}

export interface SubscriptionResponse {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
}

export interface UpdatePluginRequest {
  version?: string | null;
  description?: string | null;
  enabled?: boolean | null;
  config?: Record<string, unknown> | null;
}

export interface UpdatePrizeRequest {
  name?: string | null;
  description?: string | null;
  amount?: string | null;
  currency?: string | null;
  track_id?: string | null;
}

export interface UpdateSponsorRequest {
  name?: string | null;
  tier?: string | null;
  logo_url?: string | null;
  website_url?: string | null;
  description?: string | null;
}

export interface UpdateTeamRequest {
  name: string;
}

export interface UpdateWorkshopRequest {
  title?: string | null;
  description?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  location?: string | null;
  speaker_name?: string | null;
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
   * POST /api/backup/restore — Restore Hackathon
   * Restore a hackathon from exported data.
   * Tags: backup
   */
  async restoreHackathonApiBackupRestorePost(body: { data: Record<string, unknown> }): Promise<unknown> {
    const url = `${this.baseUrl}/api/backup/restore`;
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
   * GET /api/backup/{hackathon_id} — Backup Hackathon
   * Export a hackathon and all related data.
   * Tags: backup
   */
  async backupHackathonApiBackupHackathonIdGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/backup/${hackathon_id}`;
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
   * Submit a Devpost or GitHub URL for automated integrity analysis.
   * 
   * Behavior:
   * 1. Extract client IP and enforce rate limiting (10/min).
   * 2. Validate the URL is a Devpost or GitHub link.
   * 3. Auto-link to the existing hackathon if none specified.
   * 4. Create a pending Submission with an anonymous access token.
   * 5. Persist the submission to the database.
   * 6. Trigger background analysis via analyze_submission.
   * 
   * Raises: HTTPException(429) if rate limited, HTTPException(400) if URL invalid.
   * Side Effects: Inserts Submission row; spawns background asyncio task.
   * Dependencies: app.analyzer.analyze_submission, app.auth.create_anonymous_token, app.scraper.is_devpost_url, app.scraper.is_github_url.
   * Consumers: POST /api/check, public submission form.
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
   * Get submission status, metadata, and all check results.
   * 
   * Behavior:
   * 1. Load the submission with eager-loaded check_results.
   * 2. Return 404 if the submission does not exist.
   * 3. Return the submission state including progress, risk score, verdict, and detailed check results.
   * 
   * Raises: HTTPException(404) if submission not found.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Submission, sqlalchemy.orm.selectinload.
   * Consumers: GET /api/check/{submission_id}, status polling UI.
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
   * Get full analysis report JSON for a submission.
   * 
   * Behavior:
   * 1. Load the submission with eager-loaded check_results.
   * 2. Return 404 if the submission does not exist.
   * 3. Determine if the requester is an organizer via Clerk JWT.
   * 4. Enforce access control (organizer bypass, token match, or public if no token set).
   * 5. Return submission metadata, check results, and scoring weights.
   * 
   * Raises: HTTPException(404) if submission not found, HTTPException(403) if access denied.
   * Side Effects: None (read-only).
   * Dependencies: app.clerk_auth.is_clerk_token, app.clerk_auth.decode_clerk_token, app.models.Submission, app.models.User, app.checks.WEIGHTS.
   * Consumers: GET /api/check/{submission_id}/report, report viewer.
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
   * Retry analysis for a failed or completed submission.
   * 
   * Behavior:
   * 1. Load the submission by ID; 404 if not found.
   * 2. Delete all existing CheckResult rows for the submission.
   * 3. Reset submission status to pending and clear risk_score, verdict, completed_at, stage, and check_progress.
   * 4. Commit the reset.
   * 5. Trigger a new background analysis task.
   * 
   * Raises: HTTPException(404) if submission not found.
   * Side Effects: Deletes CheckResult rows; mutates Submission fields; spawns background asyncio task.
   * Dependencies: app.analyzer.analyze_submission, app.models.Submission, app.models.SubmissionStatus, app.models.CheckResultModel.
   * Consumers: POST /api/check/{submission_id}/retry, organizer dashboard.
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
   * Scan a QR code to check in a registered participant.
   * 
   * Behavior:
   * 1. Decode and validate the QR JWT token.
   * 2. Extract reg_id from the token payload.
   * 3. Load the registration by ID.
   * 4. Validate registration state (accepted, not already checked in, not rejected).
   * 5. Update status to checked_in and set checked_in_at timestamp.
   * 6. Commit and return registration details.
   * 
   * Raises: HTTPException(401) for invalid token, HTTPException(410) for missing or revoked registration, HTTPException(409) for already checked in or not active.
   * Side Effects: Mutates Registration.status and Registration.checked_in_at; commits to DB.
   * Dependencies: app.auth.decode_qr_token, app.models.Registration, app.models.RegistrationStatus.
   * Consumers: POST /api/checkin/scan, check-in scanner UI.
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
  async getAllConfigApiConfigGet(category?: string | null): Promise<Record<string, string>> {
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
  async updateConfigApiConfigPut(body: Record<string, string>): Promise<{ updated: string[] }> {
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
  async uploadAssetApiConfigAssetsPost(file: File | Blob, key?: string | null): Promise<{ key: string; url: string }> {
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
  async getBrandingApiConfigBrandingGet(): Promise<{ hackathon_name: string; hackathon_tagline: string; hackathon_email: string; hackathon_primary_color: string; hackathon_logo_url: string; hackathon_favicon_url: string; hackathon_year: number }> {
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
  async getSingleKeyApiConfigKeysKeyGet(key: string): Promise<{ key: string; value: string }> {
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
   * List all crawled hackathons with associated project counts.
   * 
   * Behavior:
   * 1. Query all CrawledHackathon records with an outer join to CrawledProject.
   * 2. Aggregate project counts per hackathon.
   * 3. Order results by last_crawled_at descending (nulls last).
   * 4. Return serialized list with IDs, dates, URLs, and counts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.models.CrawledHackathon, app.models.CrawledProject, sqlalchemy.func.count.
   * Consumers: GET /hackathons, organizer crawler dashboard.
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
   * Manually add a crawled hackathon entry (admin/debug use).
   * 
   * Behavior:
   * 1. Parse start_date and optional end_date from ISO strings.
   * 2. Create a CrawledHackathon record with the provided URL, name, and dates.
   * 3. Set last_crawled_at to now.
   * 4. Persist and return the created record ID.
   * 
   * Raises: HTTPException(400) if date format is invalid.
   * Side Effects: Inserts CrawledHackathon row.
   * Dependencies: app.models.CrawledHackathon.
   * Consumers: POST /hackathons, admin/debug panel.
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
   * List projects for a specific crawled hackathon with pagination.
   * 
   * Behavior:
   * 1. Validate the hackathon_id as a UUID.
   * 2. Verify the hackathon exists; 404 if not found.
   * 3. Query CrawledProject rows for the hackathon ordered by created_at descending.
   * 4. Apply offset/limit pagination.
   * 5. Return the total count and paginated project list.
   * 
   * Raises: HTTPException(400) for invalid UUID, HTTPException(404) if hackathon not found.
   * Side Effects: None (read-only).
   * Dependencies: app.models.CrawledHackathon, app.models.CrawledProject.
   * Consumers: GET /hackathons/{hackathon_id}/projects, organizer project browser.
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
   * Search crawled projects by title with pagination.
   * 
   * Behavior:
   * 1. Apply an optional case-insensitive title filter if q is provided.
   * 2. Query CrawledProject rows ordered by created_at descending.
   * 3. Apply offset/limit pagination.
   * 4. Return matching projects with hackathon linkage.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.models.CrawledProject.
   * Consumers: GET /projects, organizer project search.
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
   * Behavior:
   * 1. Check if a crawl is already in progress via is_crawling.
   * 2. Return 409 if a crawl is already running.
   * 3. Spawn run_crawl as an asyncio background task.
   * 4. Attach a done callback that logs exceptions.
   * 5. Return {"status": "started"}.
   * 
   * Raises: HTTPException(409) if crawl already in progress.
   * Side Effects: Spawns a background asyncio task.
   * Dependencies: app.crawler.scheduler.is_crawling, app.crawler.scheduler.run_crawl.
   * Consumers: POST /trigger, organizer dashboard.
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
   * List all hackathons with caching.
   * 
   * Behavior:
   * 1. Query all Hackathon records ordered by created_at descending.
   * 2. Return serialized summaries with participant counts and deadlines.
   * 
   * Raises: None
   * Side Effects: None (read-only, cached).
   * Dependencies: app.models.Hackathon, app.cache.cached.
   * Consumers: GET /api/hackathons, public hackathon listing.
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
   * Create a new hackathon (organizer-only, one per portal).
   * 
   * Behavior:
   * 1. Verify the user is an organizer.
   * 2. Reject if a hackathon already exists (portal limit).
   * 3. Build and persist a Hackathon record from the request body.
   * 4. Seed default tracks for the hackathon.
   * 5. Index hackathon data for the assistant.
   * 6. Bust the hackathon list cache.
   * 7. Return the created hackathon summary.
   * 
   * Raises: HTTPException(403) if not organizer, HTTPException(400) if hackathon already exists.
   * Side Effects: Inserts Hackathon and Track rows; mutates cache; triggers assistant indexing.
   * Dependencies: app.models.Hackathon, app.models.UserRole, app.routes.tracks.seed_tracks, app.cache.cache_delete_pattern.
   * Consumers: POST /api/hackathons, organizer setup wizard.
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
   * Get a single hackathon by ID with caching.
   * 
   * Behavior:
   * 1. Query the Hackathon record by UUID.
   * 2. Return 404 if not found.
   * 3. Return full hackathon details including schedule, venue, and Discord info.
   * 
   * Raises: HTTPException(404) if hackathon not found.
   * Side Effects: None (read-only, cached).
   * Dependencies: app.models.Hackathon, app.cache.cached.
   * Consumers: GET /api/hackathons/{hackathon_id}, hackathon detail page.
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
   * Update hackathon settings (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. Apply updates only to allowed fields from the request body.
   * 3. Commit changes and bust relevant caches if any field was updated.
   * 4. Return the updated field list.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: Mutates Hackathon fields; deletes cache keys.
   * Dependencies: app.models.Hackathon, app.cache.cache_delete_pattern.
   * Consumers: PUT /api/hackathons/{hackathon_id}, organizer settings form.
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
   * List announcements for a hackathon with role-based filtering.
   * 
   * Behavior:
   * 1. Verify the user has access (organizer or registered participant).
   * 2. Load all announcements for the hackathon.
   * 3. Filter out draft announcements for non-organizers.
   * 4. Order by sent_at descending and return.
   * 
   * Raises: HTTPException(403) if user lacks access.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Hackathon, app.models.Registration, app.models.Announcement, app.schemas.AnnouncementResponse.
   * Consumers: GET /api/hackathons/{hackathon_id}/announcements, participant and organizer announcement feeds.
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
   * Create and broadcast an announcement to all hackathon participants (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. Create an Announcement record from the request body.
   * 3. Persist and return the announcement.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: Inserts Announcement row.
   * Dependencies: app.models.Hackathon, app.models.Announcement, app.schemas.AnnouncementCreate, app.schemas.AnnouncementResponse.
   * Consumers: POST /api/hackathons/{hackathon_id}/announcements, organizer communication panel.
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
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. Query all ConflictOfInterest rows for the hackathon.
   * 3. Return serialized conflict records.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Hackathon, app.models.ConflictOfInterest, app.schemas.ConflictOfInterestResponse.
   * Consumers: GET /api/hackathons/{hackathon_id}/conflicts-of-interest, organizer judging panel.
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
   * 
   * Behavior:
   * 1. Verify the user is a judge.
   * 2. Verify the hackathon and submission exist.
   * 3. Reject if a conflict already exists for this judge and submission.
   * 4. Create and persist the ConflictOfInterest record.
   * 5. Return the created conflict.
   * 
   * Raises: HTTPException(403) if not a judge, HTTPException(404) if hackathon or submission not found, HTTPException(409) if conflict already declared.
   * Side Effects: Inserts ConflictOfInterest row.
   * Dependencies: app.models.Hackathon, app.models.Submission, app.models.ConflictOfInterest, app.models.UserRole, app.schemas.ConflictOfInterestCreate, app.schemas.ConflictOfInterestResponse.
   * Consumers: POST /api/hackathons/{hackathon_id}/conflicts-of-interest, judge dashboard.
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
   * Remove a conflict of interest declaration.
   * 
   * Behavior:
   * 1. Load the conflict record by ID and hackathon ID.
   * 2. Verify the requesting user is either the hackathon organizer or the judge who created the conflict.
   * 3. Delete the record and commit.
   * 4. Return confirmation.
   * 
   * Raises: HTTPException(404) if conflict not found, HTTPException(403) if user unauthorized.
   * Side Effects: Deletes ConflictOfInterest row.
   * Dependencies: app.models.Hackathon, app.models.ConflictOfInterest, app.models.UserRole.
   * Consumers: DELETE /api/hackathons/{hackathon_id}/conflicts-of-interest/{coi_id}, organizer or judge dashboard.
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
   * Scrape a Devpost hackathon gallery and import project URLs for analysis (organizer only).
   * 
   * Behavior:
   * 1. Verify the user is an organizer and the hackathon exists with a configured Devpost URL.
   * 2. Paginate through the Devpost project gallery up to 20 pages.
   * 3. Extract all unique project URLs using regex and CSS selectors.
   * 4. Skip URLs already imported for this hackathon.
   * 5. Create pending Submission records with anonymous tokens.
   * 6. Trigger background analysis for each new submission.
   * 7. Return import counts (found, imported, skipped).
   * 
   * Raises: HTTPException(403) if not organizer, HTTPException(404) if hackathon not found or no Devpost URL, HTTPException(404) if no projects found, HTTPException(502) if gallery fetch fails.
   * Side Effects: Inserts Submission rows; spawns background asyncio tasks.
   * Dependencies: app.models.Hackathon, app.models.Submission, app.models.SubmissionStatus, app.analyzer.analyze_submission, app.auth.create_anonymous_token, httpx.AsyncClient, bs4.BeautifulSoup.
   * Consumers: POST /api/hackathons/{hackathon_id}/import-devpost, organizer submission import tool.
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
   * Activate a judging session and auto-assign all judges to completed submissions.
   * 
   * Behavior:
   * 1. Load the JudgingSession for the hackathon; 404 if missing.
   * 2. Set session status to active.
   * 3. Load all judge IDs and all completed submission IDs for the hackathon.
   * 4. Ensure each judge has a JudgeRating record.
   * 5. Create pending JudgeAssignment rows for every judge×submission pair not already assigned.
   * 6. Commit and return activation summary.
   * 
   * Raises: HTTPException(404) if no judging session exists.
   * Side Effects: Mutates JudgingSession.status; inserts JudgeAssignment and JudgeRating rows.
   * Dependencies: _get_judging_session, app.models.User, app.models.Submission, app.models.JudgeAssignment, app.models.JudgeRating, app.models.JudgingSessionStatus.
   * Consumers: POST /hackathons/{hackathon_id}/judging/activate, organizer judging setup.
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
   * Assign judges to submissions for a hackathon judging session.
   * 
   * Behavior:
   * 1. Load the JudgingSession for the hackathon; 404 if missing.
   * 2. Parse judge_ids and submission_ids from the request body; 422 if either is empty.
   * 3. Verify all submission IDs belong to this hackathon; 422 if any are invalid.
   * 4. Mark existing assignments for this session as old (is_completed = -1).
   * 5. Ensure each judge has a JudgeRating record, creating one if missing.
   * 6. Create new JudgeAssignment rows for every judge×submission pair.
   * 7. Commit and return the count of created assignments.
   * 
   * Raises: HTTPException(404, 422)
   * Side Effects: Updates existing JudgeAssignment rows; inserts JudgeRating and JudgeAssignment rows.
   * Dependencies: _get_judging_session, app.models.JudgeAssignment, app.models.JudgeRating, app.models.Submission.
   * Consumers: POST /hackathons/{hackathon_id}/judging/assign, organizer judging setup.
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
   * List judge assignments for a hackathon judging session.
   * 
   * Behavior:
   * 1. Load the JudgingSession for the hackathon; 404 if missing.
   * 2. Build a query filtering by session, optionally by judge_id, and optionally excluding completed assignments.
   * 3. Load related Submission details for each assignment.
   * 4. Return serialized assignment list with project metadata.
   * 
   * Raises: HTTPException(404) if no judging session exists.
   * Side Effects: None (read-only).
   * Dependencies: _get_judging_session, app.models.JudgeAssignment, app.models.Submission.
   * Consumers: GET /hackathons/{hackathon_id}/judging/assignments, judge and organizer dashboards.
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
   * Manually close a judging session to prevent further scoring.
   * 
   * Behavior:
   * 1. Load the JudgingSession for the hackathon; 404 if missing.
   * 2. Set session status to closed.
   * 3. Commit and return the closed state.
   * 
   * Raises: HTTPException(404) if no judging session exists.
   * Side Effects: Mutates JudgingSession.status.
   * Dependencies: _get_judging_session, app.models.JudgingSession, app.models.JudgingSessionStatus.
   * Consumers: POST /hackathons/{hackathon_id}/judging/close, organizer judging setup.
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
   * Behavior:
   * 1. Load the JudgingSession for the hackathon; 404 if missing.
   * 2. Parse judge_id from query param.
   * 3. Load all completed assignments with scores and build submission coverage maps.
   * 4. Identify pending assignments for the requesting judge.
   * 5. Compute uncertainty metrics (variance, proximity, coverage) per submission.
   * 6. Sort by uncertainty total descending (higher = needs judging more urgently).
   * 7. Return the queue, count already scored by this judge, and a message if empty.
   * 
   * Raises: HTTPException(404) if no judging session exists.
   * Side Effects: None (read-only).
   * Dependencies: _get_judging_session, app.models.JudgeAssignment, app.models.Submission, app.models.Score, _compute_raw_score, _elo_update.
   * Consumers: GET /hackathons/{hackathon_id}/judging/queue, frontend judge dashboard.
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
   * Behavior:
   * 1. Load the JudgingSession for the hackathon; 404 if missing.
   * 2. Load all judge IDs with role=judge.
   * 3. Load all completed submission IDs for the hackathon.
   * 4. Load completed assignments and build a map of who scored what.
   * 5. For each submission with fewer than min_judges scores, create new JudgeAssignments for judges who haven't scored it.
   * 6. Also flag submissions with high score variance (>15% CV) among existing judges.
   * 7. Commit and return the count of newly created assignments.
   * 
   * Raises: HTTPException(404) if no judging session exists.
   * Side Effects: Inserts new JudgeAssignment rows.
   * Dependencies: _get_judging_session, app.models.User, app.models.Submission, app.models.JudgeAssignment, app.models.JudgeRating.
   * Consumers: POST /hackathons/{hackathon_id}/judging/rerun, organizer judging panel.
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
   * Compute and return ELO rankings for a hackathon.
   * 
   * Behavior:
   * 1. Load the JudgingSession for the hackathon; 404 if missing.
   * 2. Load all completed assignments with eager-loaded scores.
   * 3. Compute raw weighted scores per (judge, submission) using rubric criteria weights.
   * 4. Z-score normalize within each judge to correct for severity bias.
   * 5. Run within-judge pairwise ELO updates.
   * 6. Bridge across judges via submissions scored by multiple judges.
   * 7. Return final ELO rankings sorted by score descending.
   * 
   * Raises: HTTPException(404) if no judging session exists.
   * Side Effects: None (read-only).
   * Dependencies: _get_judging_session, _expected_score, _elo_update, app.models.JudgeAssignment, app.models.Submission.
   * Consumers: GET /hackathons/{hackathon_id}/judging/results, leaderboard page.
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
   * 
   * Behavior:
   * 1. Load the JudgingSession for the hackathon via _get_judging_session.
   * 2. Return the full session detail including rubric and criteria.
   * 
   * Raises: HTTPException(404) if no judging session exists.
   * Side Effects: None (read-only).
   * Dependencies: _get_judging_session, _session_detail.
   * Consumers: GET /api/hackathons/{hackathon_id}/judging/session, judging config UI.
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
   * Create or replace a judging session with rubric criteria for a hackathon (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists.
   * 2. Validate that criteria weights sum to exactly 100.
   * 3. Delete any existing JudgingSession (cascade deletes rubric, criteria, assignments).
   * 4. Create a new JudgingSession with timing and leaderboard settings.
   * 5. Create a Rubric and linked RubricCriterion rows.
   * 6. Commit and return the full session configuration.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(422) if weights do not sum to 100.
   * Side Effects: Deletes old session cascade; inserts JudgingSession, Rubric, and RubricCriterion rows.
   * Dependencies: app.models.Hackathon, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.schemas.JudgingSessionCreate.
   * Consumers: POST /api/hackathons/{hackathon_id}/judging/session, organizer judging setup.
   * Tags: judging
   */
  async createJudgingSessionApiHackathonsHackathonIdJudgingSessionPost(hackathon_id: string, body: { start_time: string; end_time: string; per_project_seconds?: number; leaderboard_public?: boolean; criteria?: { name: string; description?: string; max_score?: number; weight?: number; sort_order?: number }[] }): Promise<unknown> {
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
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. Load the primary organizer user record.
   * 3. Load all co-organizers joined with their user records.
   * 4. Return a consolidated list with roles and metadata.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Hackathon, app.models.HackathonOrganizer, app.models.User.
   * Consumers: GET /api/hackathons/{hackathon_id}/organizers, organizer team management page.
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
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the requesting user is the primary organizer.
   * 2. Require an email in the request body.
   * 3. Lookup the target user by email.
   * 4. Reject if target is the primary organizer or already a co-organizer.
   * 5. Create a HackathonOrganizer record and commit.
   * 6. Return the new co-organizer summary.
   * 
   * Raises: HTTPException(404) if hackathon or user not found, HTTPException(403) if not primary organizer, HTTPException(400) for self-add, HTTPException(409) if already co-organizer.
   * Side Effects: Inserts HackathonOrganizer row.
   * Dependencies: app.models.Hackathon, app.models.HackathonOrganizer, app.models.User.
   * Consumers: POST /api/hackathons/{hackathon_id}/organizers, organizer team management page.
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
   * Remove a co-organizer from the hackathon (primary organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the requesting user is the primary organizer.
   * 2. Reject if attempting to remove the primary organizer.
   * 3. Find and delete the HackathonOrganizer record for the target user.
   * 4. Commit and return confirmation.
   * 
   * Raises: HTTPException(404) if hackathon or co-organizer not found, HTTPException(403) if not primary organizer, HTTPException(400) if attempting self-removal.
   * Side Effects: Deletes HackathonOrganizer row.
   * Dependencies: app.models.Hackathon, app.models.HackathonOrganizer.
   * Consumers: DELETE /api/hackathons/{hackathon_id}/organizers/{user_id}, organizer team management page.
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
   * Bulk accept pending registrations with capacity and waitlist handling (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. For each pending registration ID:
   *    a. Skip if not pending or not in this hackathon.
   *    b. If at capacity and waitlist enabled, move to waitlisted.
   *    c. If at capacity and waitlist disabled, skip.
   *    d. Otherwise accept, increment current_participants, and set accepted_at.
   * 3. Commit and return accepted and waitlisted counts.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: Mutates Registration rows and Hackathon.current_participants.
   * Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
   * Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-accept, organizer registration panel.
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
   * Bulk reject pending or waitlisted registrations (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. For each registration ID, skip if not pending or waitlisted.
   * 3. Set status to rejected for matching registrations.
   * 4. Commit and return the rejected count.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: Mutates Registration.status.
   * Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
   * Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-reject, organizer registration panel.
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
   * Bulk waitlist pending registrations (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. Reject if waitlist is not enabled for the hackathon.
   * 3. For each pending registration ID, skip if not pending.
   * 4. Set status to waitlisted.
   * 5. Commit and return the waitlisted count.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer, HTTPException(400) if waitlist disabled.
   * Side Effects: Mutates Registration.status.
   * Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
   * Consumers: POST /api/hackathons/{hackathon_id}/registrations/bulk-waitlist, organizer registration panel.
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
   * Export all hackathon registrations to CSV (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. Query all registrations joined with user info, ordered by registration date.
   * 3. Write CSV rows with full registration and user fields.
   * 4. Return the CSV as a StreamingResponse download.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: None (read-only, generates CSV in memory).
   * Dependencies: app.models.Hackathon, app.models.Registration, app.models.User, fastapi.responses.StreamingResponse.
   * Consumers: GET /api/hackathons/{hackathon_id}/registrations/export, organizer data export.
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
   * Behavior:
   * 1. Verify the hackathon exists; return 404 if not found.
   * 2. Delegate to run_similarity(hackathon_id) for batch analysis.
   * 3. Return the similarity summary.
   * 
   * Raises: HTTPException(404) if hackathon not found.
   * Side Effects: run_similarity manages its own DB session for mutations.
   * Dependencies: app.checks.similarity.run_similarity, app.models.Hackathon.
   * Consumers: POST /api/hackathons/{hackathon_id}/similarity, organizer fraud panel.
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
   * Get aggregate statistics for a hackathon.
   * 
   * Behavior:
   * 1. Load all submissions for the hackathon and compute totals, completion rate, average risk, and verdict breakdown.
   * 2. Load registration status counts from the database.
   * 3. Compute check-in rate from accepted vs checked-in counts.
   * 4. Return the aggregated stats object.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.models.Submission, app.models.Registration, app.models.Verdict, app.models.SubmissionStatus, sqlalchemy.func.count.
   * Consumers: GET /api/hackathons/{hackathon_id}/stats, organizer dashboard.
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
   * List all submissions for a hackathon.
   * 
   * Behavior:
   * 1. Query Submission rows for the hackathon.
   * 2. Return serialized summaries with project titles, URLs, team info, risk scores, and verdicts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.models.Submission.
   * Consumers: GET /api/hackathons/{hackathon_id}/submissions, submissions browser.
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
   * Get meal and swag planning counts for accepted participants (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. Query all accepted and checked-in registrations.
   * 3. Aggregate counts for t-shirt sizes, dietary restrictions, and experience levels.
   * 4. Return the aggregated planning data.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Hackathon, app.models.Registration, app.models.RegistrationStatus.
   * Consumers: GET /api/hackathons/{hackathon_id}/swag-counts, organizer logistics panel.
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
   * GET /api/help-requests — List Open Help Requests
   * List open help requests for a hackathon.
   * Tags: help-requests
   */
  async listOpenHelpRequestsApiHelpRequestsGet(hackathon_id: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/help-requests` + (params.toString() ? `?${params.toString()}` : '');
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
   * POST /api/help-requests — Create Help Request
   * Create a new help request.
   * Tags: help-requests
   */
  async createHelpRequestApiHelpRequestsPost(body: { hackathon_id: string; title: string; description?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/help-requests`;
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
   * GET /api/help-requests/{request_id} — Get Help Request
   * Get a single help request.
   * Tags: help-requests
   */
  async getHelpRequestApiHelpRequestsRequestIdGet(request_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/help-requests/${request_id}`;
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
   * DELETE /api/help-requests/{request_id} — Delete Help Request
   * Delete a help request.
   * Tags: help-requests
   */
  async deleteHelpRequestApiHelpRequestsRequestIdDelete(request_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/help-requests/${request_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return;
  }

  /**
   * POST /api/help-requests/{request_id}/claim — Claim Help Request
   * Claim an open help request.
   * Tags: help-requests
   */
  async claimHelpRequestApiHelpRequestsRequestIdClaimPost(request_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/help-requests/${request_id}/claim`;
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
   * POST /api/help-requests/{request_id}/resolve — Resolve Help Request
   * Mark a help request as resolved.
   * Tags: help-requests
   */
  async resolveHelpRequestApiHelpRequestsRequestIdResolvePost(request_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/help-requests/${request_id}/resolve`;
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
   * GET /api/judging/assignments/{assignment_id} — Get Assignment Detail
   * Get full assignment detail including submission info, rubric criteria, and existing scores.
   * 
   * Behavior:
   * 1. Load the JudgeAssignment by ID with eager-loaded session, rubric, and criteria.
   * 2. Return 404 if assignment not found.
   * 3. Enforce the judging time window.
   * 4. Load the related Submission.
   * 5. Load existing Score rows and map them by criterion_id.
   * 6. Build the criteria list with current scores.
   * 7. Return the complete assignment payload.
   * 
   * Raises: HTTPException(404) if assignment not found, HTTPException(403) if outside time window.
   * Side Effects: None (read-only).
   * Dependencies: app.models.JudgeAssignment, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.models.Score, app.models.Submission, _enforce_time_window.
   * Consumers: GET /judging/assignments/{assignment_id}, frontend judging form.
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
   * Mark a judge assignment as opened and initialize blank score records.
   * 
   * Behavior:
   * 1. Load the JudgeAssignment by ID; 404 if not found.
   * 2. Load the parent JudgingSession and enforce the time window.
   * 3. Set opened_at to now if not already set.
   * 4. Create blank Score rows for each rubric criterion if not already present.
   * 5. Commit and return the opened state.
   * 
   * Raises: HTTPException(404) if assignment not found, HTTPException(403) if outside time window.
   * Side Effects: Mutates JudgeAssignment.opened_at; inserts Score rows.
   * Dependencies: app.models.JudgeAssignment, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.models.Score, _enforce_time_window.
   * Consumers: POST /judging/assignments/{assignment_id}/open, frontend judging flow.
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
   * Submit or update scores for a judge assignment.
   * 
   * Behavior:
   * 1. Load the JudgeAssignment by ID; 404 if not found.
   * 2. Reject if the assignment is already completed (400).
   * 3. Load the parent JudgingSession and enforce its time window.
   * 4. Flag as late if elapsed time exceeds per_project_seconds.
   * 5. Load the Rubric and validate each criterion ID and score range (0–max_score).
   * 6. Upsert Score rows for each criterion.
   * 7. If all criteria now have scores, mark the assignment completed and update submitted_at.
   * 8. Commit and return the updated assignment state.
   * 
   * Raises: HTTPException(404, 400, 422)
   * Side Effects: Inserts or updates Score rows; may mutate JudgeAssignment.is_completed, submitted_at, and auto-submit null scores as 0 when late.
   * Dependencies: app.models.JudgeAssignment, app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion, app.models.Score, _enforce_time_window.
   * Consumers: POST /judging/assignments/{assignment_id}/score, frontend judging form.
   * Tags: judging
   */
  async submitScoresApiJudgingAssignmentsAssignmentIdScorePost(assignment_id: string, body: { scores?: { criterion_id: string; score: number }[] }): Promise<unknown> {
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
   * GET /api/monitoring/diagnostics — Diagnostics
   * Extended diagnostics for all subsystems.
   * Tags: monitoring
   */
  async diagnosticsApiMonitoringDiagnosticsGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/monitoring/diagnostics`;
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
   * GET /api/plugins — List Plugins
   * List all registered plugins.
   * Tags: plugins
   */
  async listPluginsApiPluginsGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/plugins`;
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
   * POST /api/plugins — Register Plugin
   * Register a new plugin.
   * Tags: plugins
   */
  async registerPluginApiPluginsPost(body: { name: string; version?: string; description?: string | null; enabled?: boolean; config?: Record<string, unknown> | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/plugins`;
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
   * GET /api/plugins/{plugin_id} — Get Plugin
   * Get a single plugin.
   * Tags: plugins
   */
  async getPluginApiPluginsPluginIdGet(plugin_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/plugins/${plugin_id}`;
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
   * PUT /api/plugins/{plugin_id} — Update Plugin
   * Update a plugin.
   * Tags: plugins
   */
  async updatePluginApiPluginsPluginIdPut(plugin_id: string, body: { version?: string | null; description?: string | null; enabled?: boolean | null; config?: Record<string, unknown> | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/plugins/${plugin_id}`;
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
   * DELETE /api/plugins/{plugin_id} — Delete Plugin
   * Unregister a plugin.
   * Tags: plugins
   */
  async deletePluginApiPluginsPluginIdDelete(plugin_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/plugins/${plugin_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return;
  }

  /**
   * GET /api/prizes — List Prizes
   * List prizes for a hackathon.
   * Tags: prizes
   */
  async listPrizesApiPrizesGet(hackathon_id: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/prizes` + (params.toString() ? `?${params.toString()}` : '');
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
   * POST /api/prizes — Create Prize
   * Create a new prize.
   * Tags: prizes
   */
  async createPrizeApiPrizesPost(body: { hackathon_id: string; name: string; description?: string | null; amount?: string | null; currency?: string; track_id?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/prizes`;
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
   * GET /api/prizes/{prize_id} — Get Prize
   * Get a single prize.
   * Tags: prizes
   */
  async getPrizeApiPrizesPrizeIdGet(prize_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/prizes/${prize_id}`;
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
   * PUT /api/prizes/{prize_id} — Update Prize
   * Update a prize.
   * Tags: prizes
   */
  async updatePrizeApiPrizesPrizeIdPut(prize_id: string, body: { name?: string | null; description?: string | null; amount?: string | null; currency?: string | null; track_id?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/prizes/${prize_id}`;
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
   * DELETE /api/prizes/{prize_id} — Delete Prize
   * Delete a prize.
   * Tags: prizes
   */
  async deletePrizeApiPrizesPrizeIdDelete(prize_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/prizes/${prize_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return;
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
   * GET /api/sponsors — List Sponsors
   * List sponsors for a hackathon.
   * Tags: sponsors
   */
  async listSponsorsApiSponsorsGet(hackathon_id: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/sponsors` + (params.toString() ? `?${params.toString()}` : '');
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
   * POST /api/sponsors — Create Sponsor
   * Create a new sponsor.
   * Tags: sponsors
   */
  async createSponsorApiSponsorsPost(body: { hackathon_id: string; name: string; tier?: string; logo_url?: string | null; website_url?: string | null; description?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/sponsors`;
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
   * GET /api/sponsors/{sponsor_id} — Get Sponsor
   * Get a single sponsor.
   * Tags: sponsors
   */
  async getSponsorApiSponsorsSponsorIdGet(sponsor_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/sponsors/${sponsor_id}`;
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
   * PUT /api/sponsors/{sponsor_id} — Update Sponsor
   * Update a sponsor.
   * Tags: sponsors
   */
  async updateSponsorApiSponsorsSponsorIdPut(sponsor_id: string, body: { name?: string | null; tier?: string | null; logo_url?: string | null; website_url?: string | null; description?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/sponsors/${sponsor_id}`;
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
   * DELETE /api/sponsors/{sponsor_id} — Delete Sponsor
   * Delete a sponsor.
   * Tags: sponsors
   */
  async deleteSponsorApiSponsorsSponsorIdDelete(sponsor_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/sponsors/${sponsor_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return;
  }

  /**
   * POST /api/teams — Create Team
   * Create a new team for a hackathon (requires accepted registration).
   * Tags: teams
   */
  async createTeamApiTeamsPost(body: { hackathon_id: string; name: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/teams`;
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
   * GET /api/teams/{team_id} — Get Team
   * Get team details with member list.
   * Tags: teams
   */
  async getTeamApiTeamsTeamIdGet(team_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/teams/${team_id}`;
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
   * PUT /api/teams/{team_id} — Update Team
   * Update team name (captain only).
   * Tags: teams
   */
  async updateTeamApiTeamsTeamIdPut(team_id: string, body: { name: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/teams/${team_id}`;
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
   * POST /api/teams/{team_id}/join — Join Team
   * Join a team by its join code.
   * Tags: teams
   */
  async joinTeamApiTeamsTeamIdJoinPost(team_id: string, body: { join_code: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/teams/${team_id}/join`;
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
   * DELETE /api/teams/{team_id}/members/{user_id} — Remove Team Member
   * Remove a member from the team (captain only).
   * Tags: teams
   */
  async removeTeamMemberApiTeamsTeamIdMembersUserIdDelete(team_id: string, user_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/teams/${team_id}/members/${user_id}`;
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
   * POST /api/webhooks/subscribe — Subscribe
   * Create a new webhook subscription (organizer only).
   * Tags: webhooks
   */
  async subscribeApiWebhooksSubscribePost(body: { url: string; secret: string; events: string[] }): Promise<{ id: string; url: string; events: string[]; active: boolean; created_at: string }> {
    const url = `${this.baseUrl}/api/webhooks/subscribe`;
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
   * GET /api/webhooks/subscriptions — List Subscriptions
   * List all webhook subscriptions (organizer only).
   * Tags: webhooks
   */
  async listSubscriptionsApiWebhooksSubscriptionsGet(): Promise<{ id: string; url: string; events: string[]; active: boolean; created_at: string }[]> {
    const url = `${this.baseUrl}/api/webhooks/subscriptions`;
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
   * DELETE /api/webhooks/subscriptions/{subscription_id} — Delete Subscription
   * Delete a webhook subscription (organizer only).
   * Tags: webhooks
   */
  async deleteSubscriptionApiWebhooksSubscriptionsSubscriptionIdDelete(subscription_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/webhooks/subscriptions/${subscription_id}`;
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
   * GET /api/workshops — List Workshops
   * List workshops for a hackathon.
   * Tags: workshops
   */
  async listWorkshopsApiWorkshopsGet(hackathon_id: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/workshops` + (params.toString() ? `?${params.toString()}` : '');
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
   * POST /api/workshops — Create Workshop
   * Create a new workshop (any authenticated user).
   * Tags: workshops
   */
  async createWorkshopApiWorkshopsPost(body: { hackathon_id: string; title: string; description?: string | null; start_time: string; end_time: string; location?: string | null; speaker_name?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/workshops`;
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
   * GET /api/workshops/{workshop_id} — Get Workshop
   * Get a single workshop.
   * Tags: workshops
   */
  async getWorkshopApiWorkshopsWorkshopIdGet(workshop_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/workshops/${workshop_id}`;
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
   * PUT /api/workshops/{workshop_id} — Update Workshop
   * Update a workshop.
   * Tags: workshops
   */
  async updateWorkshopApiWorkshopsWorkshopIdPut(workshop_id: string, body: { title?: string | null; description?: string | null; start_time?: string | null; end_time?: string | null; location?: string | null; speaker_name?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/workshops/${workshop_id}`;
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
   * DELETE /api/workshops/{workshop_id} — Delete Workshop
   * Delete a workshop.
   * Tags: workshops
   */
  async deleteWorkshopApiWorkshopsWorkshopIdDelete(workshop_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/workshops/${workshop_id}`;
    const res = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return;
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