// Auto-generated TypeScript SDK for OpenHack API
// Generated from FastAPI OpenAPI spec — do not edit manually.

/* eslint-disable */

/** Pydantic schema for creating a new announcement. */
/**  */
/** Behavior: */
/** 1. Validates title, content, and priority. */
/** 2. Consumed by the announcement creation endpoint. */
/**  */
/** Raises: ValidationError on unexpected extra fields if strict mode is enabled. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/announcements route, organizer broadcast panel. */
export interface AnnouncementCreate {
  title: string;
  content: string;
  priority?: string;
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

/** Request body for broadcasting a notification to hackathon participants. */
/**  */
/** Attributes: */
/**     title: Short headline of the notification. */
/**     message: Body text of the notification. */
/**     type: Severity level (info, success, warning, error). Defaults to info. */
/**     action_url: Optional URL to open when the user clicks the action button. */
/**     action_text: Optional label for the action button. */
export interface BroadcastNotificationRequest {
  title: string;
  message: string;
  type?: NotificationType;
  action_url?: string | null;
  action_text?: string | null;
}

/** Request body for changing a user's role. */
export interface ChangeRoleRequest {
  role: string;
}

/** Request body for persisting a browser agent conversation. */
/**  */
/** Behavior: */
/** 1. Define the schema for a chat log persistence request. */
/** 2. Provide messages and optional conversation_id fields. */
/**  */
/** Side Effects: None (schema definition). */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/chat-log, assistant chat logging. */
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
/** 1. Validates submission_id and reason fields. */
/** 2. Consumed by the COI declaration endpoint. */
/**  */
/** Raises: ValidationError on unexpected extra fields if strict mode is enabled. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/coi route, judge declaration form. */
export interface ConflictOfInterestCreate {
  submission_id: unknown;
  reason?: string | null;
}

/** Request body for manually adding a crawled hackathon entry. */
export interface CreateCrawledHackathonRequest {
  devpost_url: string;
  name: string;
  start_date: string;
  end_date?: string | null;
}

/** Request body for creating a help request. */
/**  */
/** Attributes: */
/**     hackathon_id: UUID of the hackathon where help is needed. */
/**     title: Short summary of the request. */
/**     description: Optional detailed description of the problem. */
export interface CreateHelpRequestRequest {
  hackathon_id: string;
  title: string;
  description?: string | null;
}

/** Request body for creating a mentorship request. */
export interface CreateMentorshipRequest {
  topic: string;
}

/** Request body for creating a prize. */
/**  */
/** Attributes: */
/**     hackathon_id: UUID of the hackathon this prize belongs to. */
/**     name: Display name of the prize. */
/**     description: Optional description of the prize. */
/**     amount: Optional prize amount string (e.g. "500"). */
/**     currency: Currency code (default "USD"). */
/**     track_id: Optional UUID of the associated track. */
export interface CreatePrizeRequest {
  hackathon_id: string;
  name: string;
  description?: string | null;
  amount?: string | null;
  currency?: string;
  track_id?: string | null;
}

/** Request body for creating a sponsor. */
/**  */
/** Attributes: */
/**     hackathon_id: UUID of the hackathon this sponsor supports. */
/**     name: Display name of the sponsor. */
/**     tier: Sponsorship tier (default "silver"). */
/**     logo_url: Optional URL to the sponsor's logo. */
/**     website_url: Optional URL to the sponsor's website. */
/**     description: Optional description or tagline. */
export interface CreateSponsorRequest {
  hackathon_id: string;
  name: string;
  tier?: string;
  logo_url?: string | null;
  website_url?: string | null;
  description?: string | null;
}

/** Request body for creating a survey. */
export interface CreateSurveyRequest {
  title: string;
  questions_json: Record<string, unknown> | unknown[];
}

/** Request body for creating a team finder post. */
export interface CreateTeamFinderPostRequest {
  post_type: string;
  skills_needed?: string[] | null;
  description?: string | null;
}

/** Request body for creating a new team within a hackathon. */
export interface CreateTeamRequest {
  hackathon_id: string;
  name: string;
}

/** Request body for creating a workshop. */
export interface CreateWorkshopRequest {
  hackathon_id: string;
  title: string;
  description?: string | null;
  start_time: string;
  end_time: string;
  location?: string | null;
  speaker_name?: string | null;
  max_capacity?: number | null;
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

/** Request body for sending a bulk email blast to a registrant cohort. */
export interface EmailBlastRequest {
  subject: string;
  body: string;
  cohort?: string;
  track_id?: string | null;
}

/** Request body for executing an assistant tool. */
/**  */
/** Behavior: */
/** 1. Define the schema for a tool execution request. */
/** 2. Provide tool_name and parameters fields. */
/**  */
/** Side Effects: None (schema definition). */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/execute-tool, assistant tool execution. */
export interface ExecuteToolRequest {
  tool_name: string;
  parameters?: Record<string, unknown>;
}

export interface ForgotPasswordRequest {
  email: string;
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
/** 1. Validates required name, start_date, end_date and optional settings. */
/** 2. Consumed by the hackathon creation endpoint. */
/**  */
/** Raises: ValidationError on unexpected extra fields if strict mode is enabled. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/hackathons route, organizer event wizard. */
export interface HackathonCreate {
  name: string;
  start_date: string;
  end_date: string;
  description?: string | null;
  application_deadline?: string | null;
  max_participants?: number | null;
  waitlist_enabled?: boolean | null;
  venue_address?: string | null;
  parking_info?: string | null;
  wifi_ssid?: string | null;
  wifi_password?: string | null;
  discord_invite_url?: string | null;
  devpost_url?: string | null;
  schedule?: unknown | null;
}

/** Health check response schema. */
/**  */
/** Attributes: */
/**     status: Overall health status ("healthy" or "degraded"). */
/**     timestamp: ISO 8601 timestamp of the check. */
/**     version: Application version string. */
/**     checks: Dict of subsystem names to status strings. */
export interface HealthStatus {
  status: string;
  timestamp: string;
  version?: string;
  checks: Record<string, unknown>;
}

export interface InviteGenerateRequest {
  count?: number;
  role?: UserRole;
  expires_days?: number | null;
}

/** Request body for joining an existing team by its join code. */
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

/** Request body for LLM chat proxy. */
/**  */
/** Behavior: */
/** 1. Define the schema for an LLM chat proxy request. */
/** 2. Provide messages and model fields. */
/**  */
/** Side Effects: None (schema definition). */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/llm/chat (mounted in main.py), LLM proxy. */
export interface LLMChatRequest {
  messages: Record<string, unknown>[];
  model?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

/** Severity level of an in-app notification. */
export interface NotificationType {
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

/** Request body for RAG document search. */
/**  */
/** Behavior: */
/** 1. Define the schema for a RAG search request. */
/** 2. Provide a query field. */
/**  */
/** Side Effects: None (schema definition). */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/rag-search, assistant document search. */
export interface RAGSearchRequest {
  query: string;
}

/** Request body for registering a plugin. */
/**  */
/** Behavior: */
/** 1. Define the schema for a plugin registration request. */
/** 2. Provide name, version, description, enabled, and config fields. */
/**  */
/** Side Effects: None (schema definition). */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/plugins, plugin registry. */
export interface RegisterPluginRequest {
  name: string;
  version?: string;
  description?: string | null;
  enabled?: boolean;
  config?: Record<string, unknown> | null;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

/** Pydantic schema for creating a new hackathon registration. */
/**  */
/** Behavior: */
/** 1. Validates optional registration fields. */
/** 2. All fields are optional to support flexible registration flows. */
/**  */
/** Raises: ValidationError on unexpected extra fields if strict mode is enabled. */
/** Side Effects: None. */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/registrations route, signup wizard. */
export interface RegistrationCreate {
  team_name?: string | null;
  team_members?: string[] | null;
  linkedin_url?: string | null;
  github_url?: string | null;
  resume_url?: string | null;
  experience_level?: string | null;
  t_shirt_size?: string | null;
  phone?: string | null;
  dietary_restrictions?: string | null;
  what_build?: string | null;
  why_participate?: string | null;
  age?: number | null;
  school?: string | null;
  major?: string | null;
  pronouns?: string | null;
  skills?: string[] | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  invite_code?: string | null;
  answers?: unknown[] | null;
}

/** Schema for creating a custom registration question. */
export interface RegistrationQuestionCreate {
  question_text: string;
  question_type: string;
  options?: string[] | null;
  is_required?: boolean;
  sort_order?: number;
}

/** Schema for updating a custom registration question. */
export interface RegistrationQuestionUpdate {
  question_text?: string | null;
  question_type?: string | null;
  options?: string[] | null;
  is_required?: boolean | null;
  sort_order?: number | null;
}

/** Schema for creating a review note. */
export interface RegistrationReviewNoteCreate {
  note_text: string;
  rating?: number | null;
}

/** Schema for updating a review note. */
export interface RegistrationReviewNoteUpdate {
  note_text?: string | null;
  rating?: number | null;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

/** Request body for restoring a hackathon from exported data. */
/**  */
/** Attributes: */
/**     data: Full exported hackathon payload previously returned by the backup endpoint. */
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

/** Request body for sending a chat message within a hackathon. */
export interface SendMessageRequest {
  message: string;
  recipient_id?: string | null;
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

/** Request body for submitting a survey response. */
export interface SubmitSurveyResponseRequest {
  answers_json: Record<string, unknown> | unknown[];
  nps_score?: number | null;
}

/** Request body for creating a webhook subscription. */
/**  */
/** Behavior: */
/** 1. Define the schema for a webhook subscription request. */
/** 2. Provide url, secret, and events fields. */
/**  */
/** Side Effects: None (schema definition). */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: POST /api/webhooks/subscribe, subscription creation. */
export interface SubscribeRequest {
  url: string;
  secret: string;
  events: string[];
}

/** Response schema for a webhook subscription. */
/**  */
/** Behavior: */
/** 1. Define the schema for a webhook subscription response. */
/** 2. Provide id, url, events, active, and created_at fields. */
/**  */
/** Side Effects: None (schema definition). */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: GET /api/webhooks/subscriptions, subscription listing. */
export interface SubscriptionResponse {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
}

/** Request body for updating a plugin. */
/**  */
/** Behavior: */
/** 1. Define the schema for a plugin update request. */
/** 2. Provide version, description, enabled, and config fields. */
/**  */
/** Side Effects: None (schema definition). */
/** Dependencies: pydantic.BaseModel. */
/** Consumers: PUT /api/plugins/{plugin_id}, plugin update. */
export interface UpdatePluginRequest {
  version?: string | null;
  description?: string | null;
  enabled?: boolean | null;
  config?: Record<string, unknown> | null;
}

/** Request body for updating a prize. */
/**  */
/** Attributes: */
/**     name: Optional new display name. */
/**     description: Optional new description. */
/**     amount: Optional new prize amount. */
/**     currency: Optional new currency code. */
/**     track_id: Optional new associated track UUID. */
export interface UpdatePrizeRequest {
  name?: string | null;
  description?: string | null;
  amount?: string | null;
  currency?: string | null;
  track_id?: string | null;
}

/** Request body for updating a user's public profile. */
export interface UpdateProfileRequest {
  bio?: string | null;
  skills?: unknown[] | null;
  links?: Record<string, unknown> | null;
  availability?: string | null;
  looking_for_team?: boolean | null;
}

/** Request body for updating a sponsor. */
/**  */
/** Attributes: */
/**     name: Optional new display name. */
/**     tier: Optional new sponsorship tier. */
/**     logo_url: Optional new logo URL. */
/**     website_url: Optional new website URL. */
/**     description: Optional new description. */
export interface UpdateSponsorRequest {
  name?: string | null;
  tier?: string | null;
  logo_url?: string | null;
  website_url?: string | null;
  description?: string | null;
}

/** Request body for updating a team's name. */
export interface UpdateTeamRequest {
  name: string;
}

/** Request body for updating a workshop. */
export interface UpdateWorkshopRequest {
  title?: string | null;
  description?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  location?: string | null;
  speaker_name?: string | null;
  max_capacity?: number | null;
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

/** Roles available to users in the platform: organizer, participant, judge, or volunteer. */
export interface UserRole {
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
   * GET /api/admin/oauth/providers — List Providers
   * Tags: admin-oauth
   */
  async listProvidersApiAdminOauthProvidersGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/admin/oauth/providers`;
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
   * POST /api/admin/oauth/providers — Add Provider
   * Tags: admin-oauth
   */
  async addProviderApiAdminOauthProvidersPost(name: string, client_id: string, client_secret: string, preset?: string | null, authorize_url?: string | null, token_url?: string | null, userinfo_url?: string | null, scope?: string | null, display_name?: string | null): Promise<unknown> {
    const params = new URLSearchParams();
    if (name != null) params.append('name', String(name));
    if (client_id != null) params.append('client_id', String(client_id));
    if (client_secret != null) params.append('client_secret', String(client_secret));
    if (preset != null) params.append('preset', String(preset));
    if (authorize_url != null) params.append('authorize_url', String(authorize_url));
    if (token_url != null) params.append('token_url', String(token_url));
    if (userinfo_url != null) params.append('userinfo_url', String(userinfo_url));
    if (scope != null) params.append('scope', String(scope));
    if (display_name != null) params.append('display_name', String(display_name));
    const url = `${this.baseUrl}/api/admin/oauth/providers` + (params.toString() ? `?${params.toString()}` : '');
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
   * DELETE /api/admin/oauth/providers/{name} — Remove Provider
   * Tags: admin-oauth
   */
  async removeProviderApiAdminOauthProvidersNameDelete(name: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/admin/oauth/providers/${name}`;
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
   * GET /api/admin/users — List Users
   * List all users with optional search and filter (organizer only).
   * 
   * Behavior:
   * 1. Verify the user is an organizer.
   * 2. Query users via AdminService with filters.
   * 3. Return paginated results.
   * 
   * Raises: HTTPException(403) if not organizer.
   * Tags: admin
   */
  async listUsersApiAdminUsersGet(search?: string | null, role?: string | null, banned?: boolean | null, limit?: number, offset?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (search != null) params.append('search', String(search));
    if (role != null) params.append('role', String(role));
    if (banned != null) params.append('banned', String(banned));
    if (limit != null) params.append('limit', String(limit));
    if (offset != null) params.append('offset', String(offset));
    const url = `${this.baseUrl}/api/admin/users` + (params.toString() ? `?${params.toString()}` : '');
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
   * GET /api/admin/users/{user_id}/activity — Get User Activity
   * View user activity log (organizer only).
   * 
   * Behavior:
   * 1. Verify organizer role.
   * 2. Fetch activity summary via AdminService.
   * 3. Return the activity dict.
   * 
   * Raises: HTTPException(403) if not organizer.
   * Tags: admin
   */
  async getUserActivityApiAdminUsersUserIdActivityGet(user_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/admin/users/${user_id}/activity`;
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
   * POST /api/admin/users/{user_id}/ban — Ban User
   * Ban a user (organizer only).
   * 
   * Behavior:
   * 1. Verify organizer role.
   * 2. Ban the user via AdminService.
   * 3. Return confirmation.
   * 
   * Raises: HTTPException(403) if not organizer, HTTPException(404) if user not found.
   * Tags: admin
   */
  async banUserApiAdminUsersUserIdBanPost(user_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/admin/users/${user_id}/ban`;
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
   * POST /api/admin/users/{user_id}/role — Change User Role
   * Change a user's role (organizer only).
   * 
   * Behavior:
   * 1. Verify organizer role.
   * 2. Change role via AdminService.
   * 3. Return confirmation.
   * 
   * Raises: HTTPException(403) if not organizer, HTTPException(400/404) on errors.
   * Tags: admin
   */
  async changeUserRoleApiAdminUsersUserIdRolePost(user_id: string, body: { role: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/admin/users/${user_id}/role`;
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
   * POST /api/admin/users/{user_id}/unban — Unban User
   * Unban a user (organizer only).
   * 
   * Behavior:
   * 1. Verify organizer role.
   * 2. Unban the user via AdminService.
   * 3. Return confirmation.
   * 
   * Raises: HTTPException(403) if not organizer, HTTPException(404) if user not found.
   * Tags: admin
   */
  async unbanUserApiAdminUsersUserIdUnbanPost(user_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/admin/users/${user_id}/unban`;
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
   * POST /api/assistant/chat — Create Chat Message
   * Create a new chat message and start processing.
   * 
   * Deprecated: Replaced by client-side AgentLoop + POST /api/llm/chat.
   * Kept for backward compatibility.
   * 
   * Behavior:
   * 1. Get or create an AssistantConversation for the user.
   * 2. Raise 404 if an existing conversation_id does not belong to the user.
   * 3. Save the user message as an AssistantMessage.
   * 4. Create a pending assistant response placeholder.
   * 5. Commit and return the conversation and message ids with status.
   * 
   * Raises: HTTPException(404) if conversation not found or does not belong to user.
   * Side Effects: Inserts AssistantConversation and AssistantMessage rows.
   * Dependencies: app.models_assistant.AssistantConversation, app.models_assistant.AssistantMessage, app.models.Hackathon.
   * Consumers: POST /api/chat, assistant chat (deprecated).
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
   * 
   * Behavior:
   * 1. Create a new conversation if no conversation_id is provided.
   * 2. Verify an existing conversation_id belongs to the current user.
   * 3. Raise 404 if the conversation is not found.
   * 4. Persist each message as an AssistantMessage row.
   * 5. Commit and return the conversation_id with status "saved".
   * 
   * Raises: HTTPException(404) if conversation not found or does not belong to user.
   * Side Effects: Inserts AssistantConversation and AssistantMessage rows.
   * Dependencies: app.models_assistant.AssistantConversation, app.models_assistant.AssistantMessage.
   * Consumers: POST /api/chat-log, assistant chat logging.
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
   * 
   * Behavior:
   * 1. Call detect_build_intent on the raw message text.
   * 2. Return the intent flag, confidence score, and original message.
   * 
   * Side Effects: None (read-only).
   * Dependencies: app.assistant.context_builder.detect_build_intent.
   * Consumers: POST /api/detect-intent, builder mode.
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
   * 
   * Behavior:
   * 1. Verify the user's role can use the requested tool.
   * 2. Raise 403 if the tool is not allowed for the role.
   * 3. Execute the tool via ToolExecutor.
   * 4. Return the result under the "result" key.
   * 5. Raise 500 if tool execution fails unexpectedly.
   * 
   * Raises: HTTPException(403) if tool not allowed for role. HTTPException(500) if tool execution fails.
   * Side Effects: May mutate database state depending on the tool executed.
   * Dependencies: app.assistant.permissions.can_use_tool, app.assistant.tools.ToolExecutor.
   * Consumers: POST /api/execute-tool, assistant tool execution.
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
   * 
   * Behavior:
   * 1. Load optional hackathon context and associated tracks.
   * 2. Build a plan generation prompt with description, hackathon name, and tracks.
   * 3. Call the LLM and attempt to parse JSON from the response.
   * 4. Add a generated UUID to the plan.
   * 5. Return the plan with a success flag, or an error dict on failure.
   * 
   * Side Effects: None (read-only, LLM call only).
   * Dependencies: app.assistant.context_builder.build_plan_generation_prompt, app.assistant.llm.llm_client, app.models.Hackathon, app.models.Track.
   * Consumers: POST /api/generate-plan, builder mode.
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
   * 
   * Behavior:
   * 1. Convert the request plan to a dict.
   * 2. Build a project generation prompt with the plan and project type.
   * 3. Call the LLM and attempt to parse JSON from the response.
   * 4. Validate the response contains a files array.
   * 5. Auto-generate a README if missing.
   * 6. Return the files, README, and success flag, or an error dict on failure.
   * 
   * Side Effects: None (read-only, LLM call only).
   * Dependencies: app.assistant.context_builder.build_project_generation_prompt, app.assistant.llm.llm_client, app.schemas.builder.GenerateProjectRequest.
   * Consumers: POST /api/generate-project, builder mode.
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
   * 
   * Behavior:
   * 1. Query AssistantConversation rows for the current user.
   * 2. Order by updated_at descending and apply pagination.
   * 3. Serialize each conversation to a summary dict.
   * 4. Return the list and total count.
   * 
   * Side Effects: None (read-only).
   * Dependencies: app.models_assistant.AssistantConversation.
   * Consumers: GET /api/history, assistant conversation list.
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
   * 
   * Behavior:
   * 1. Load the conversation by id and user_id.
   * 2. Raise 404 if the conversation is not found or does not belong to the user.
   * 3. Load all messages ordered by created_at.
   * 4. Return the conversation metadata and message list.
   * 
   * Raises: HTTPException(404) if conversation not found or does not belong to user.
   * Side Effects: None (read-only).
   * Dependencies: app.models_assistant.AssistantConversation, app.models_assistant.AssistantMessage.
   * Consumers: GET /api/history/{conversation_id}, assistant conversation detail.
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
   * 
   * Behavior:
   * 1. Load the conversation by id and user_id.
   * 2. Raise 404 if the conversation is not found or does not belong to the user.
   * 3. Delete associated messages from the vector store.
   * 4. Delete the conversation from the database and commit.
   * 5. Return a success dict.
   * 
   * Raises: HTTPException(404) if conversation not found or does not belong to user.
   * Side Effects: Deletes AssistantConversation row and vector store entries.
   * Dependencies: app.models_assistant.AssistantConversation, app.assistant.vector_store.vector_store.
   * Consumers: DELETE /api/history/{conversation_id}, assistant conversation management.
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
   * 
   * Behavior:
   * 1. Embed the query text.
   * 2. Search the vector store for matching documents.
   * 3. Apply role-based and hackathon-scoped filters.
   * 4. Return the matching documents with relevance scores.
   * 
   * Side Effects: None (read-only).
   * Dependencies: app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
   * Consumers: POST /api/rag-search, assistant document search.
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
   * 
   * Deprecated: Replaced by client-side AgentLoop. Kept for backward compat.
   * 
   * Behavior:
   * 1. Load the assistant message and verify ownership via conversation user_id.
   * 2. Raise 404 if the message is not found or does not belong to the user.
   * 3. Return the existing content if the message is already completed.
   * 4. Build conversation context, history, and available tools.
   * 5. Stream LLM response chunks via SSE.
   * 6. Execute any tool calls and yield results.
   * 7. Persist final content and index for semantic search.
   * 8. Return a StreamingResponse.
   * 
   * Raises: HTTPException(404) if message not found or does not belong to user.
   * Side Effects: Mutates AssistantMessage content, status, tool_results; indexes message in vector store.
   * Dependencies: app.assistant.context_builder.ContextBuilder, app.assistant.llm.llm_client, app.assistant.tools.ToolExecutor, app.assistant.embedder.embedder, app.assistant.vector_store.vector_store.
   * Consumers: GET /api/stream/{message_id}, assistant streaming (deprecated).
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
   * 
   * Behavior:
   * 1. Get the tool definitions for the user's role.
   * 2. Return the role and available tools.
   * 
   * Side Effects: None (read-only).
   * Dependencies: app.assistant.permissions.get_tools_for_role.
   * Consumers: GET /api/tools, assistant tool listing.
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
   * POST /api/auth/forgot-password — Forgot Password
   * Request a password reset link. Always returns 200 to prevent enumeration.
   * Tags: auth
   */
  async forgotPasswordApiAuthForgotPasswordPost(body: { email: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/auth/forgot-password`;
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
   * POST /api/auth/login — Login
   * Authenticate with email and password.
   * Tags: auth
   */
  async loginApiAuthLoginPost(body: { email: string; password: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/auth/login`;
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
   * POST /api/auth/logout — Logout
   * Revoke refresh token and clear cookie.
   * Tags: auth
   */
  async logoutApiAuthLogoutPost(): Promise<unknown> {
    const url = `${this.baseUrl}/api/auth/logout`;
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
   * GET /api/auth/me — Get Me
   * Return the current authenticated user.
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
   * GET /api/auth/oauth/{provider}/callback — Oauth Callback
   * Tags: oauth
   */
  async oauthCallbackApiAuthOauthProviderCallbackGet(provider: string, code: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (code != null) params.append('code', String(code));
    const url = `${this.baseUrl}/api/auth/oauth/{provider}/callback` + (params.toString() ? `?${params.toString()}` : '');
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
   * GET /api/auth/oauth/{provider}/login — Oauth Login
   * Tags: oauth
   */
  async oauthLoginApiAuthOauthProviderLoginGet(provider: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/auth/oauth/${provider}/login`;
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
   * GET /api/auth/providers — List Providers
   * List active OAuth providers.
   * Tags: auth
   */
  async listProvidersApiAuthProvidersGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/auth/providers`;
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
   * POST /api/auth/refresh — Refresh
   * Rotate refresh token and issue a new access token.
   * Tags: auth
   */
  async refreshApiAuthRefreshPost(): Promise<unknown> {
    const url = `${this.baseUrl}/api/auth/refresh`;
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
   * POST /api/auth/register — Register
   * Register a new participant account.
   * Tags: auth
   */
  async registerApiAuthRegisterPost(body: { email: string; password: string; name: string }): Promise<{ id: string; email: string; name?: string | null; role?: string | null; created_at?: unknown | null }> {
    const url = `${this.baseUrl}/api/auth/register`;
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
   * POST /api/auth/reset-password — Reset Password
   * Reset password using a valid reset token.
   * Tags: auth
   */
  async resetPasswordApiAuthResetPasswordPost(body: { token: string; new_password: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/auth/reset-password`;
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
   * POST /api/backup/restore — Restore Hackathon
   * Restore a hackathon from exported data.
   * 
   * Behavior:
   * 1. Invoke BackupService.restore_hackathon with the user's sub as organizer.
   * 2. Return the restored hackathon's id, name, and restored flag.
   * 
   * Raises: None
   * Side Effects: Inserts hackathon and related rows into the database.
   * Dependencies: app.services.backup_service.BackupService.
   * Consumers: POST /api/backup/restore, organizer backup tool.
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
   * 
   * Behavior:
   * 1. Validate hackathon_id UUID and invoke BackupService.export_hackathon.
   * 2. Return 404 if the hackathon is not found.
   * 3. Return the full hackathon snapshot dict.
   * 
   * Raises: HTTPException(404) if the hackathon is not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.backup_service.BackupService.
   * Consumers: GET /api/backup/{hackathon_id}, organizer backup tool.
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
   * POST /api/chat/{message_id}/read — Mark Message Read
   * Mark a chat message as read.
   * 
   * Behavior:
   * 1. Instantiate ChatService and attempt to mark the message as read.
   * 2. Return 404 if the message does not exist.
   * 3. Return the updated message with read_at timestamp.
   * 
   * Raises: HTTPException(404) if message not found.
   * Side Effects: Updates the ChatMessage row.
   * Dependencies: app.services.chat_service.ChatService.
   * Consumers: POST /api/chat/{message_id}/read, messaging UI read receipts.
   * Tags: chat
   */
  async markMessageReadApiChatMessageIdReadPost(message_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/chat/${message_id}/read`;
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
   * POST /api/check — Submit For Check
   * Submit a Devpost or GitHub URL for automated integrity analysis.
   * 
   * Behavior:
   * 1. Extract client IP and enforce rate limiting (10/min).
   * 2. Validate the URL is a Devpost or GitHub link.
   * 3. Auto-link to the existing hackathon if none specified.
   * 4. Create a pending Submission with an anonymous access token.
   * 5. Persist the submission to the database.
   * 6. Trigger background analysis via SubmissionService.analyze_submission.
   * 
   * Raises: HTTPException(429) if rate limited, HTTPException(400) if URL invalid.
   * Side Effects: Inserts Submission row; spawns background asyncio task.
   * Dependencies: app.services.submission_service.SubmissionService, app.scraper.is_devpost_url, app.scraper.is_github_url.
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
   * Dependencies: app.services.submission_service.SubmissionService.
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
   * Dependencies: app.auth.verify_access_token, app.models.Submission, app.models.User, app.services.submission_service.SubmissionService.
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
   * Dependencies: app.services.submission_service.SubmissionService.
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
   * Dependencies: app.services.scan_service.ScanService.
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
   * Get all config values, optionally filtered by category.
   * 
   * Behavior:
   * 1. Validate the category against allowed set if provided; 400 if invalid.
   * 2. Fetch all config values (optionally filtered) from the config service.
   * 3. Return the config dict.
   * 
   * Raises: HTTPException(400) if an invalid category is provided.
   * Side Effects: None (read-only).
   * Dependencies: app.services.config_service.ConfigService.
   * Consumers: GET /api/config/, frontend settings panel.
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
   * Update multiple config values (organizer only).
   * 
   * Behavior:
   * 1. Validate and persist the key-value updates via config service; 400 if invalid.
   * 2. Return the list of updated keys.
   * 
   * Raises: HTTPException(400) if any key or value is invalid.
   * Side Effects: Mutates config store.
   * Dependencies: app.services.config_service.ConfigService, app.clerk_auth.require_organizer.
   * Consumers: PUT /api/config/, organizer settings panel.
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
   * Upload a file asset to storage (organizer only).
   * 
   * Behavior:
   * 1. Receive uploaded file and optional key name.
   * 2. Upload via storage service; 400 if file invalid, 502 if storage backend fails.
   * 3. Return asset key and public URL.
   * 
   * Raises: HTTPException(400) if the file is invalid. HTTPException(502) if the storage backend fails.
   * Side Effects: Writes file to storage backend.
   * Dependencies: app.storage.StorageService, app.clerk_auth.require_organizer.
   * Consumers: POST /api/config/assets, organizer asset manager.
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
   * 
   * Behavior:
   * 1. Load all config values.
   * 2. Parse the hackathon year integer (default 2025).
   * 3. Return branding fields as a dict.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.config_service.ConfigService.
   * Consumers: GET /api/config/branding, legacy frontend views.
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
   * 
   * Behavior:
   * 1. Fetch custom CSS from config service.
   * 2. Return empty PlainTextResponse if none is configured, otherwise return the CSS with nosniff header.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.config_service.ConfigService.
   * Consumers: GET /api/config/custom.css, frontend theming.
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
   * Get a single config value by key.
   * 
   * Behavior:
   * 1. Look up the config key via config service.
   * 2. Return 400 if the key is invalid or not found.
   * 3. Return the key and its value.
   * 
   * Raises: HTTPException(400) if the key is invalid or not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.config_service.ConfigService.
   * Consumers: GET /api/config/keys/{key}, frontend settings.
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
   * 
   * Behavior:
   * 1. Load all config values from the config service.
   * 2. Build a manifest dict with name, short_name, icons, and theme colors.
   * 3. Return as a JSONResponse with no-cache headers.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.config_service.ConfigService.
   * Consumers: GET /api/config/manifest.json, PWA support.
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
   * 
   * Behavior:
   * 1. Fetch theme CSS from config service.
   * 2. Return it as a PlainTextResponse with text/css media type.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.config_service.ConfigService.
   * Consumers: GET /api/config/theme.css, frontend theming.
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
   * List published content pages, optionally filtered by tab_group.
   * 
   * Behavior:
   * 1. Query published ContentPage rows joined with author names.
   * 2. Optionally filter by tab_group query parameter.
   * 3. Order results by tab_group_order and sort_order.
   * 4. Return serialized pages and the set of present tab_groups.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.models.ContentPage, app.models.User, app.cache.cached.
   * Consumers: GET /api/content/pages, public page listing.
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
   * 
   * Behavior:
   * 1. Validate the title is present; 422 if missing.
   * 2. Generate or validate the slug (lowercase alphanumeric with hyphens); 422 if invalid.
   * 3. Check for slug conflicts; 409 if duplicate.
   * 4. Create and persist the ContentPage row.
   * 5. Bust the content cache.
   * 6. Return the created page's serialized details.
   * 
   * Raises: HTTPException(422) if title is missing or slug is invalid. HTTPException(409) if slug already exists.
   * Side Effects: Inserts ContentPage row; clears content cache.
   * Dependencies: app.models.ContentPage, app.cache.cache_delete_pattern.
   * Consumers: POST /api/content/pages, organizer dashboard.
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
   * Get a single published content page by slug.
   * 
   * Behavior:
   * 1. Query ContentPage by slug where is_published is True, joined with author name.
   * 2. Return 404 if no matching page exists.
   * 3. Return serialized page details.
   * 
   * Raises: HTTPException(404) if the page is not found or unpublished.
   * Side Effects: None (read-only).
   * Dependencies: app.models.ContentPage, app.models.User.
   * Consumers: GET /api/content/pages/{slug}, public page viewer.
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
   * 
   * Behavior:
   * 1. Look up the page by slug; 404 if not found.
   * 2. Apply allowed field updates from the body (title, content, tab_group, sort_order, tab_group_order, is_published).
   * 3. Update the updated_at timestamp.
   * 4. Commit changes and bust the content cache.
   * 5. Return the updated page's serialized details.
   * 
   * Raises: HTTPException(404) if the page is not found.
   * Side Effects: Mutates ContentPage row; clears content cache.
   * Dependencies: app.models.ContentPage.
   * Consumers: PUT /api/content/pages/{slug}, organizer dashboard.
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
   * 
   * Behavior:
   * 1. Look up the page by slug; 404 if not found.
   * 2. Delete the page from the database and commit.
   * 3. Bust the content cache.
   * 4. Return confirmation dict.
   * 
   * Raises: HTTPException(404) if the page is not found.
   * Side Effects: Deletes ContentPage row; clears content cache.
   * Dependencies: app.models.ContentPage.
   * Consumers: DELETE /api/content/pages/{slug}, organizer dashboard.
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
   * Dependencies: app.services.crawler_service.CrawlerService.
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
   * Dependencies: app.services.crawler_service.CrawlerService.
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
   * Dependencies: app.services.crawler_service.CrawlerService.
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
   * Dependencies: app.services.crawler_service.CrawlerService.
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
   * 
   * Behavior:
   * 1. Build a filtered count query based on optional hackathon_id, status, and verdict.
   * 2. Execute count to get total.
   * 3. Build the submissions query with the same filters, ordered by risk_score descending.
   * 4. Apply pagination offset and limit.
   * 5. Return submissions list, page, per_page, and total count.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.models.Submission, app.auth.require_organizer.
   * Consumers: GET /api/dashboard, organizer submissions review.
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
   * 
   * Behavior:
   * 1. Import the global Discord bot instance.
   * 2. Read connection readiness, bot user string, and guild list.
   * 3. Return a dict with ready flag, user name, guild count, and guild summaries.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.discord_bot.bot.
   * Consumers: GET /api/discord/bot-status, frontend admin dashboard.
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
   * 
   * Behavior:
   * 1. Import and call get_bot_invite_url to compute the OAuth invite link.
   * 2. Return the URL if the client ID is configured, otherwise return an error dict.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.discord_bot.get_bot_invite_url.
   * Consumers: GET /api/discord/invite-url, frontend admin settings panel.
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
   * DELETE /api/hackathons/invites/{code} — Revoke Invite
   * Tags: invites
   */
  async revokeInviteApiHackathonsInvitesCodeDelete(code: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/invites/${code}`;
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
   * POST /api/hackathons/surveys/{survey_id}/responses — Submit Response
   * Submit a response to a survey.
   * 
   * Behavior:
   * 1. Submit via SurveyService.
   * 2. Return confirmation.
   * 
   * Raises: HTTPException(400) on validation errors.
   * Tags: surveys
   */
  async submitResponseApiHackathonsSurveysSurveyIdResponsesPost(survey_id: string, body: { answers_json: Record<string, unknown> | unknown[]; nps_score?: number | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/surveys/${survey_id}/responses`;
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
   * GET /api/hackathons/surveys/{survey_id}/results — Get Survey Results
   * Get aggregated survey results (organizer only).
   * 
   * Behavior:
   * 1. Verify organizer role.
   * 2. Aggregate results via SurveyService.
   * 3. Return metrics.
   * 
   * Raises: HTTPException(403) if not organizer, HTTPException(404) if survey not found.
   * Tags: surveys
   */
  async getSurveyResultsApiHackathonsSurveysSurveyIdResultsGet(survey_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/surveys/${survey_id}/results`;
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
   * GET /api/hackathons/{hackathon_id}/analytics — Get Hackathon Analytics
   * Get analytics metrics for a hackathon (organizer only).
   * 
   * Behavior:
   * 1. Verify the user is an organizer.
   * 2. Load the hackathon.
   * 3. Aggregate all metrics via AnalyticsService.
   * 4. Return the combined analytics payload.
   * 
   * Raises: HTTPException(403) if not organizer, HTTPException(404) if hackathon not found.
   * Tags: hackathons
   */
  async getHackathonAnalyticsApiHackathonsHackathonIdAnalyticsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/analytics`;
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
   * GET /api/hackathons/{hackathon_id}/audit-log — Get Hackathon Audit Log
   * Get audit log entries for a hackathon (organizer only).
   * 
   * Behavior:
   * 1. Verify the user is an organizer.
   * 2. Query AuditLog rows for the hackathon, ordered by created_at desc.
   * 3. Return paginated results.
   * 
   * Raises: HTTPException(403) if not organizer.
   * Tags: hackathons
   */
  async getHackathonAuditLogApiHackathonsHackathonIdAuditLogGet(hackathon_id: string, limit?: number, offset?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (limit != null) params.append('limit', String(limit));
    if (offset != null) params.append('offset', String(offset));
    const url = `${this.baseUrl}/api/hackathons/{hackathon_id}/audit-log` + (params.toString() ? `?${params.toString()}` : '');
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
   * GET /api/hackathons/{hackathon_id}/chat — Get Chat History
   * Get chat history for the current user within a hackathon.
   * 
   * Behavior:
   * 1. Verify the hackathon exists.
   * 2. Instantiate ChatService and load messages where the user is sender or recipient.
   * 3. Return a serialized list of messages.
   * 
   * Raises: HTTPException(404) if hackathon not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.chat_service.ChatService.
   * Consumers: GET /api/hackathons/{id}/chat, participant messaging UI.
   * Tags: chat
   */
  async getChatHistoryApiHackathonsHackathonIdChatGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/chat`;
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
   * POST /api/hackathons/{hackathon_id}/chat — Send Chat Message
   * Send a chat message to organizers (or a specific recipient) within a hackathon.
   * 
   * Behavior:
   * 1. Verify the hackathon exists.
   * 2. Verify the sender is a participant (accepted/checked_in) or an organizer.
   * 3. Instantiate ChatService and persist the message.
   * 4. Return the serialized message with id, sender_id, message, and created_at.
   * 
   * Raises: HTTPException(404) if hackathon not found. HTTPException(403) if sender is not a participant or organizer.
   * Side Effects: Inserts a ChatMessage row.
   * Dependencies: app.services.chat_service.ChatService.
   * Consumers: POST /api/hackathons/{id}/chat, participant messaging UI.
   * Tags: chat
   */
  async sendChatMessageApiHackathonsHackathonIdChatPost(hackathon_id: string, body: { message: string; recipient_id?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/chat`;
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
   * POST /api/hackathons/{hackathon_id}/email-blast — Email Blast
   * Send a bulk email to a registrant cohort (organizer only).
   * 
   * Behavior:
   * 1. Load the hackathon and verify the caller is an organizer.
   * 2. Instantiate EmailBlastService and dispatch to the correct cohort method.
   * 3. Return the delivery summary with sent and failed counts.
   * 
   * Raises: HTTPException(404) if hackathon not found. HTTPException(403) if not organizer.
   * Side Effects: Triggers outbound emails via EmailBlastService.
   * Dependencies: app.services.email_blast_service.EmailBlastService.
   * Consumers: POST /api/hackathons/{id}/email-blast, organizer communications panel.
   * Tags: hackathons
   */
  async emailBlastApiHackathonsHackathonIdEmailBlastPost(hackathon_id: string, body: { subject: string; body: string; cohort?: string; track_id?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/email-blast`;
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
   * GET /api/hackathons/{hackathon_id}/hacker-dashboard — Get Hacker Dashboard
   * Get the hacker dashboard for the current user's registration at a hackathon.
   * 
   * Behavior:
   * 1. Load the hackathon by ID; 404 if not found.
   * 2. Load the user's registration with scans and user details; 404 if not registered.
   * 3. Count scans and build sorted scan history.
   * 4. Return hackathon details and registration info including QR token and scans.
   * 
   * Raises: HTTPException(404) if the hackathon or user's registration is not found.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Hackathon, app.models.Registration, sqlalchemy.orm.selectinload.
   * Consumers: GET /api/hackathons/{hackathon_id}/hacker-dashboard, participant mobile view.
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
   * GET /api/hackathons/{hackathon_id}/invites — List Invites
   * Tags: invites
   */
  async listInvitesApiHackathonsHackathonIdInvitesGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/invites`;
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
   * POST /api/hackathons/{hackathon_id}/invites — Generate Invites
   * Tags: invites
   */
  async generateInvitesApiHackathonsHackathonIdInvitesPost(hackathon_id: string, body: { count?: number; role?: string; expires_days?: number | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/invites`;
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
   * POST /api/hackathons/{hackathon_id}/judging/activate — Activate Judging
   * Activate a judging session and auto-assign all judges to completed submissions.
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
   * Create or replace a judging session with rubric criteria (organizer only).
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
   * POST /api/hackathons/{hackathon_id}/mentorship/request — Request Mentor
   * Request a mentor for a hackathon.
   * 
   * Behavior:
   * 1. Create the mentorship request via MentorshipService.
   * 2. Return serialized request details.
   * 
   * Raises: None
   * Side Effects: Inserts MentorshipRequest row.
   * Dependencies: app.services.mentorship_service.MentorshipService, app.clerk_auth.require_clerk_user.
   * Consumers: POST /api/hackathons/{id}/mentorship/request.
   * Tags: mentorship
   */
  async requestMentorApiHackathonsHackathonIdMentorshipRequestPost(hackathon_id: string, body: { topic: string }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/mentorship/request`;
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
   * GET /api/hackathons/{hackathon_id}/mentorship/requests — List Mentorship Requests
   * List mentorship requests for the current user at a hackathon.
   * 
   * Behavior:
   * 1. Fetch requests where the user is the requester or mentor via MentorshipService.
   * 2. Return serialized list with requester and mentor names.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.mentorship_service.MentorshipService.
   * Consumers: GET /api/hackathons/{id}/mentorship/requests.
   * Tags: mentorship
   */
  async listMentorshipRequestsApiHackathonsHackathonIdMentorshipRequestsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/mentorship/requests`;
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
   * POST /api/hackathons/{hackathon_id}/notifications/broadcast — Broadcast To Hackathon
   * Broadcast a notification to all accepted registrants of a hackathon.
   * 
   * Behavior:
   * 1. Instantiate NotificationService and broadcast to all accepted registrants.
   * 2. Return the number of notifications created.
   * 
   * Raises: HTTPException(403) if the user is not an organizer for the hackathon.
   * Side Effects: Inserts many Notification rows.
   * Dependencies: app.services.notification_service.NotificationService, app.clerk_auth.require_hackathon_organizer.
   * Consumers: POST /api/hackathons/{id}/notifications/broadcast, organizer broadcast panel.
   * Tags: hackathons
   */
  async broadcastToHackathonApiHackathonsHackathonIdNotificationsBroadcastPost(hackathon_id: string, body: { title: string; message: string; type?: string; action_url?: string | null; action_text?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/notifications/broadcast`;
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
   * GET /api/hackathons/{hackathon_id}/organizer-chat — Get Organizer Chat
   * Get all chat messages for a hackathon (organizer view).
   * 
   * Behavior:
   * 1. Verify the hackathon exists.
   * 2. Verify the caller is an organizer or co-organizer.
   * 3. Instantiate ChatService and load all messages scoped to the hackathon.
   * 4. Return a serialized list of messages.
   * 
   * Raises: HTTPException(404) if hackathon not found. HTTPException(403) if not organizer.
   * Side Effects: None (read-only).
   * Dependencies: app.services.chat_service.ChatService, app.models.HackathonOrganizer.
   * Consumers: GET /api/hackathons/{id}/organizer-chat, organizer messaging dashboard.
   * Tags: chat
   */
  async getOrganizerChatApiHackathonsHackathonIdOrganizerChatGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/organizer-chat`;
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
   * GET /api/hackathons/{hackathon_id}/participants — List Participants
   * List public participant profiles for a hackathon.
   * 
   * Behavior:
   * 1. Fetch accepted registrations via ProfileService.
   * 2. Return serialized list of public profile fields.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.profile_service.ProfileService.
   * Consumers: GET /api/hackathons/{id}/participants, participant directory.
   * Tags: profiles
   */
  async listParticipantsApiHackathonsHackathonIdParticipantsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/participants`;
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
   * GET /api/hackathons/{hackathon_id}/prizes/awarded — List Awarded Prizes
   * List all awarded prizes for a hackathon.
   * 
   * Behavior:
   * 1. Fetch awarded prizes via PrizeService.list_awarded_prizes.
   * 2. Return serialized list with prize and team details.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.prize_service.PrizeService.
   * Consumers: GET /api/hackathons/{hackathon_id}/prizes/awarded.
   * Tags: hackathons
   */
  async listAwardedPrizesApiHackathonsHackathonIdPrizesAwardedGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/prizes/awarded`;
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
   * GET /api/hackathons/{hackathon_id}/project-expo — List Project Expo Submissions
   * List all submissions with public details for a hackathon.
   * 
   * Behavior:
   * 1. Fetch submissions via ProjectExpoService.
   * 2. Return serialized list of public submission details.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.project_expo_service.ProjectExpoService.
   * Consumers: GET /api/hackathons/{id}/project-expo, project expo page.
   * Tags: project-expo
   */
  async listProjectExpoSubmissionsApiHackathonsHackathonIdProjectExpoGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/project-expo`;
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
   * GET /api/hackathons/{hackathon_id}/project-expo/results — Get Project Expo Results
   * Get vote counts per submission for a hackathon (organizer only).
   * 
   * Behavior:
   * 1. Fetch results via ProjectExpoService.
   * 2. Return serialized vote tally.
   * 
   * Raises: HTTPException(403) if the user is not an organizer.
   * Side Effects: None (read-only).
   * Dependencies: app.services.project_expo_service.ProjectExpoService.
   * Consumers: GET /api/hackathons/{id}/project-expo/results, organizer dashboard.
   * Tags: project-expo
   */
  async getProjectExpoResultsApiHackathonsHackathonIdProjectExpoResultsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/project-expo/results`;
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
   * POST /api/hackathons/{hackathon_id}/project-expo/{submission_id}/vote — Cast Project Expo Vote
   * Cast a people's choice vote for a submission.
   * 
   * Behavior:
   * 1. Cast the vote via ProjectExpoService.
   * 2. Return 400 if the user has already voted in this hackathon.
   * 3. Return confirmation.
   * 
   * Raises: HTTPException(400) if the user has already voted.
   * Side Effects: Inserts PublicVote row.
   * Dependencies: app.services.project_expo_service.ProjectExpoService.
   * Consumers: POST /api/hackathons/{id}/project-expo/{submission_id}/vote.
   * Tags: project-expo
   */
  async castProjectExpoVoteApiHackathonsHackathonIdProjectExpoSubmissionIdVotePost(hackathon_id: string, submission_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/project-expo/${submission_id}/vote`;
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
   * POST /api/hackathons/{hackathon_id}/register — Register For Hackathon
   * Register current user for a hackathon.
   * 
   * Behavior:
   * 1. Load the user and hackathon in parallel.
   * 2. Raise 401 if the user is not found.
   * 3. Raise 404 if the hackathon is not found.
   * 4. Raise 400 if the application deadline has passed.
   * 5. Raise 409 if the user is already registered.
   * 6. Determine if auto-waitlist is needed based on capacity.
   * 7. Create a Registration with the appropriate initial status.
   * 8. Commit and send a Discord notification via background task.
   * 9. Publish a registration.created event.
   * 10. Return the registration details with optional waitlist info.
   * 
   * Raises: HTTPException(401) if user not found. HTTPException(404) if hackathon not found. HTTPException(400) if deadline passed or at capacity without waitlist. HTTPException(409) if already registered.
   * Side Effects: Inserts Registration row; increments Hackathon.current_participants if waitlisted; spawns background task; publishes event.
   * Dependencies: app.models.Registration, app.models.Hackathon, app.models.User, app.discord_bot.post_application_to_discord, app.services.event_service.publish_event.
   * Consumers: POST /api/hackathons/{hackathon_id}/register, participant registration form.
   * Tags: registrations
   */
  async registerForHackathonApiHackathonsHackathonIdRegisterPost(hackathon_id: string, body: { team_name?: string | null; team_members?: string[] | null; linkedin_url?: string | null; github_url?: string | null; resume_url?: string | null; experience_level?: string | null; t_shirt_size?: string | null; phone?: string | null; dietary_restrictions?: string | null; what_build?: string | null; why_participate?: string | null; age?: number | null; school?: string | null; major?: string | null; pronouns?: string | null; skills?: string[] | null; emergency_contact_name?: string | null; emergency_contact_phone?: string | null; invite_code?: string | null; answers?: unknown[] | null }): Promise<unknown> {
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
   * GET /api/hackathons/{hackathon_id}/registration-questions — List Questions
   * List custom registration questions for a hackathon. Logged-in users only.
   * Tags: registration-questions
   */
  async listQuestionsApiHackathonsHackathonIdRegistrationQuestionsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registration-questions`;
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
   * POST /api/hackathons/{hackathon_id}/registration-questions — Create Question
   * Create a custom registration question. Organizer only.
   * Tags: registration-questions
   */
  async createQuestionApiHackathonsHackathonIdRegistrationQuestionsPost(hackathon_id: string, body: { question_text: string; question_type: string; options?: string[] | null; is_required?: boolean; sort_order?: number }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registration-questions`;
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
   * PUT /api/hackathons/{hackathon_id}/registration-questions/{question_id} — Update Question
   * Update a custom registration question. Organizer only.
   * Tags: registration-questions
   */
  async updateQuestionApiHackathonsHackathonIdRegistrationQuestionsQuestionIdPut(hackathon_id: string, question_id: string, body: { question_text?: string | null; question_type?: string | null; options?: string[] | null; is_required?: boolean | null; sort_order?: number | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registration-questions/${question_id}`;
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
   * DELETE /api/hackathons/{hackathon_id}/registration-questions/{question_id} — Delete Question
   * Delete a custom registration question. Organizer only.
   * Tags: registration-questions
   */
  async deleteQuestionApiHackathonsHackathonIdRegistrationQuestionsQuestionIdDelete(hackathon_id: string, question_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registration-questions/${question_id}`;
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
   * GET /api/hackathons/{hackathon_id}/registrations — List Hackathon Registrations
   * List registrations for a hackathon. Organizer only, RLS: own hackathons only.
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Build filtered count and list queries by hackathon_id and optional status.
   * 3. Fetch registrations with pagination.
   * 4. Load associated users for name/email enrichment.
   * 5. Return the registration list with pagination metadata.
   * 
   * Raises: HTTPException(404) if hackathon not found or not owned.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Registration, app.models.User, app.auth.require_organizer.
   * Consumers: GET /api/hackathons/{hackathon_id}/registrations, organizer dashboard.
   * Tags: organizer-registrations
   */
  async organizerListHackathonRegistrations(hackathon_id: string, status?: string | null, offset?: number, limit?: number): Promise<unknown> {
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
   * 2. Delegate to RegistrationService.bulk_reject.
   * 3. Return the rejected count.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: Mutates Registration.status.
   * Dependencies: app.services.registration_service.RegistrationService.
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
   * 2. Delegate to RegistrationService.bulk_waitlist.
   * 3. Return the waitlisted count.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer, HTTPException(400) if waitlist disabled.
   * Side Effects: Mutates Registration.status.
   * Dependencies: app.services.registration_service.RegistrationService.
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
   * GET /api/hackathons/{hackathon_id}/registrations/dietary-report — Get Dietary Report
   * Return aggregated dietary restrictions for accepted registrations. Organizer only.
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Query accepted registrations with their users.
   * 3. Aggregate counts by dietary restriction value.
   * 4. Return both summary and individual entries.
   * 
   * Raises: HTTPException(404) if hackathon not found or not owned.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Registration, app.models.User, app.auth.require_organizer.
   * Consumers: GET /api/hackathons/{hackathon_id}/registrations/dietary-report, organizer dashboard.
   * Tags: organizer-registrations
   */
  async getDietaryReportApiHackathonsHackathonIdRegistrationsDietaryReportGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/dietary-report`;
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
   * GET /api/hackathons/{hackathon_id}/registrations/emergency-contacts — Get Emergency Contacts
   * Return emergency contact info for all accepted participants. Organizer only.
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Query accepted registrations with their users.
   * 3. Return name, phone, emergency contact name and phone for each.
   * 
   * Raises: HTTPException(404) if hackathon not found or not owned.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Registration, app.models.User, app.auth.require_organizer.
   * Consumers: GET /api/hackathons/{hackathon_id}/registrations/emergency-contacts, organizer dashboard.
   * Tags: organizer-registrations
   */
  async getEmergencyContactsApiHackathonsHackathonIdRegistrationsEmergencyContactsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/emergency-contacts`;
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
   * GET /api/hackathons/{hackathon_id}/registrations/export — Export Registrations Csv
   * Export all hackathon registrations to CSV (organizer only).
   * 
   * Behavior:
   * 1. Verify the hackathon exists and the user is an organizer.
   * 2. Delegate to RegistrationService.export_registrations_csv.
   * 3. Return the CSV as a StreamingResponse download.
   * 
   * Raises: HTTPException(404) if hackathon not found, HTTPException(403) if not organizer.
   * Side Effects: None (read-only, generates CSV in memory).
   * Dependencies: app.services.registration_service.RegistrationService, fastapi.responses.StreamingResponse.
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
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Load the registration by id and hackathon_id.
   * 3. Raise 404 if the registration is not found.
   * 4. Raise 409 if the registration is not pending.
   * 5. Generate a QR token and update status to accepted.
   * 6. Commit and publish a registration.accepted event.
   * 7. Return the updated registration details.
   * 
   * Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not pending.
   * Side Effects: Mutates Registration status, qr_token, accepted_at; publishes event.
   * Dependencies: app.auth.create_qr_token, app.models.Registration, app.services.event_service.publish_event.
   * Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/accept, organizer dashboard.
   * Tags: organizer-registrations
   */
  async organizerAcceptRegistration(hackathon_id: string, registration_id: string): Promise<unknown> {
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
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Load the registration by id and hackathon_id.
   * 3. Raise 404 if the registration is not found.
   * 4. Raise 409 if the registration is not accepted.
   * 5. Update status to checked_in and set checked_in_at.
   * 6. Commit and publish a registration.checked_in event.
   * 7. Return the updated registration details.
   * 
   * Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not accepted.
   * Side Effects: Mutates Registration status and checked_in_at; publishes event.
   * Dependencies: app.services.scan_service.ScanService, app.services.event_service.publish_event.
   * Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/checkin, organizer dashboard.
   * Tags: organizer-registrations
   */
  async organizerCheckinRegistration(hackathon_id: string, registration_id: string): Promise<unknown> {
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
   * GET /api/hackathons/{hackathon_id}/registrations/{registration_id}/notes — List Notes
   * List review notes for a registration. Organizer only.
   * Tags: registration-notes
   */
  async listNotesApiHackathonsHackathonIdRegistrationsRegistrationIdNotesGet(hackathon_id: string, registration_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/notes`;
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
   * POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/notes — Create Note
   * Add a review note to a registration. Organizer only.
   * Tags: registration-notes
   */
  async createNoteApiHackathonsHackathonIdRegistrationsRegistrationIdNotesPost(hackathon_id: string, registration_id: string, body: { note_text: string; rating?: number | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/notes`;
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
   * PUT /api/hackathons/{hackathon_id}/registrations/{registration_id}/notes/{note_id} — Update Note
   * Update a review note. Only the original author can edit.
   * Tags: registration-notes
   */
  async updateNoteApiHackathonsHackathonIdRegistrationsRegistrationIdNotesNoteIdPut(hackathon_id: string, registration_id: string, note_id: string, body: { note_text?: string | null; rating?: number | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/notes/${note_id}`;
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
   * DELETE /api/hackathons/{hackathon_id}/registrations/{registration_id}/notes/{note_id} — Delete Note
   * Delete a review note. Only the original author can delete.
   * Tags: registration-notes
   */
  async deleteNoteApiHackathonsHackathonIdRegistrationsRegistrationIdNotesNoteIdDelete(hackathon_id: string, registration_id: string, note_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/registrations/${registration_id}/notes/${note_id}`;
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
   * POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/reject — Reject Registration
   * Reject a registration. Organizer only.
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Load the registration by id and hackathon_id.
   * 3. Raise 404 if the registration is not found.
   * 4. Raise 409 if the registration is not pending or accepted.
   * 5. Update status to rejected and invalidate the QR token.
   * 6. If the registration was accepted, promote from waitlist.
   * 7. Commit and return the updated registration details.
   * 
   * Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not rejectable.
   * Side Effects: Mutates Registration status and qr_token; may trigger waitlist promotion.
   * Dependencies: app.models.Registration, app.waitlist.promote_from_waitlist.
   * Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/reject, organizer dashboard.
   * Tags: organizer-registrations
   */
  async organizerRejectRegistration(hackathon_id: string, registration_id: string): Promise<unknown> {
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
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Delegate to RegistrationService.unwaitlist_registration.
   * 3. Return the updated registration details.
   * 
   * Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not waitlisted.
   * Side Effects: Mutates Registration status and declined_count.
   * Dependencies: app.services.registration_service.RegistrationService.
   * Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/unwaitlist, organizer dashboard.
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
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Load the registration by id and hackathon_id.
   * 3. Raise 404 if the registration is not found.
   * 4. Raise 409 if the registration is not pending.
   * 5. Update status to waitlisted.
   * 6. Commit and return the updated registration details.
   * 
   * Raises: HTTPException(404) if hackathon or registration not found. HTTPException(409) if registration not pending.
   * Side Effects: Mutates Registration status.
   * Dependencies: app.models.Registration.
   * Consumers: POST /api/hackathons/{hackathon_id}/registrations/{registration_id}/waitlist, organizer dashboard.
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
   * GET /api/hackathons/{hackathon_id}/surveys — List Surveys
   * List active surveys for a hackathon.
   * 
   * Behavior:
   * 1. Query active surveys via SurveyService.
   * 2. Return serialized list.
   * 
   * Raises: None
   * Tags: surveys
   */
  async listSurveysApiHackathonsHackathonIdSurveysGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/surveys`;
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
   * POST /api/hackathons/{hackathon_id}/surveys — Create Survey
   * Create a survey for a hackathon (organizer only).
   * 
   * Behavior:
   * 1. Verify the user is an organizer.
   * 2. Create the survey via SurveyService.
   * 3. Return the created survey.
   * 
   * Raises: HTTPException(403) if not organizer.
   * Tags: surveys
   */
  async createSurveyApiHackathonsHackathonIdSurveysPost(hackathon_id: string, body: { title: string; questions_json: Record<string, unknown> | unknown[] }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/surveys`;
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
   * GET /api/hackathons/{hackathon_id}/team-finder — List Team Finder Posts
   * List active team finder posts for a hackathon.
   * 
   * Behavior:
   * 1. Fetch active posts via TeamFinderService.
   * 2. Return serialized list with owner names.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.team_finder_service.TeamFinderService.
   * Consumers: GET /api/hackathons/{id}/team-finder, team finder page.
   * Tags: team-finder
   */
  async listTeamFinderPostsApiHackathonsHackathonIdTeamFinderGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/team-finder`;
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
   * POST /api/hackathons/{hackathon_id}/team-finder — Create Team Finder Post
   * Create a team finder post for a hackathon.
   * 
   * Behavior:
   * 1. Validate post_type is either 'looking_for_team' or 'looking_for_members'.
   * 2. Create the post via TeamFinderService.
   * 3. Return serialized post details.
   * 
   * Raises: HTTPException(400) if post_type is invalid.
   * Side Effects: Inserts TeamFinderPost row.
   * Dependencies: app.services.team_finder_service.TeamFinderService, app.clerk_auth.require_clerk_user.
   * Consumers: POST /api/hackathons/{id}/team-finder, team finder form.
   * Tags: team-finder
   */
  async createTeamFinderPostApiHackathonsHackathonIdTeamFinderPost(hackathon_id: string, body: { post_type: string; skills_needed?: string[] | null; description?: string | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/team-finder`;
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
   * DELETE /api/hackathons/{hackathon_id}/team-finder/{post_id} — Deactivate Team Finder Post
   * Deactivate a team finder post (owner only).
   * 
   * Behavior:
   * 1. Deactivate the post via TeamFinderService.
   * 2. Return 404 if the post is not found, 403 if not the owner.
   * 3. Return confirmation.
   * 
   * Raises: HTTPException(404) if the post is not found. HTTPException(403) if the requester is not the owner.
   * Side Effects: Updates TeamFinderPost.is_active to False.
   * Dependencies: app.services.team_finder_service.TeamFinderService, app.clerk_auth.require_clerk_user.
   * Consumers: DELETE /api/hackathons/{id}/team-finder/{post_id}.
   * Tags: team-finder
   */
  async deactivateTeamFinderPostApiHackathonsHackathonIdTeamFinderPostIdDelete(hackathon_id: string, post_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/team-finder/${post_id}`;
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
   * GET /api/hackathons/{hackathon_id}/tracks — List Tracks
   * List all tracks for a hackathon.
   * 
   * Behavior:
   * 1. Query Track rows filtered by hackathon_id, ordered by created_at.
   * 2. Serialize each track using _track_to_response.
   * 3. Return a dict with hackathon_id and the tracks list.
   * 
   * Side Effects: None (read-only).
   * Dependencies: app.models.Track.
   * Consumers: GET /api/hackathons/{hackathon_id}/tracks, hackathon details.
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
   * Create a new track for a hackathon (organizer only).
   * 
   * Behavior:
   * 1. Verify the user is an organizer for the hackathon.
   * 2. Create a Track ORM instance from the request body.
   * 3. Persist the track to the database.
   * 4. Reindex hackathon data and bust the tracks cache.
   * 5. Return the created track details.
   * 
   * Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if hackathon not found.
   * Side Effects: Inserts Track row; reindexes hackathon; busts cache.
   * Dependencies: app.models.Track, app.assistant.indexer.DocumentIndexer, app.cache.cache_delete_pattern.
   * Consumers: POST /api/hackathons/{hackathon_id}/tracks, organizer dashboard.
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
   * Update a track (organizer only).
   * 
   * Behavior:
   * 1. Verify the user is an organizer for the hackathon.
   * 2. Load the track by id and hackathon_id.
   * 3. Raise 404 if the track is not found.
   * 4. Update allowed fields from the request body.
   * 5. Commit changes.
   * 6. Reindex hackathon data and bust the tracks cache.
   * 7. Return the updated track details.
   * 
   * Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if track not found.
   * Side Effects: Mutates Track row; reindexes hackathon; busts cache.
   * Dependencies: app.models.Track, app.assistant.indexer.DocumentIndexer, app.cache.cache_delete_pattern.
   * Consumers: PUT /api/hackathons/{hackathon_id}/tracks/{track_id}, organizer dashboard.
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
   * Delete a track (organizer only).
   * 
   * Behavior:
   * 1. Verify the user is an organizer for the hackathon.
   * 2. Load the track by id and hackathon_id.
   * 3. Raise 404 if the track is not found.
   * 4. Delete the track and commit.
   * 5. Reindex hackathon data and bust the tracks cache.
   * 6. Return a confirmation dict.
   * 
   * Raises: HTTPException(403) if user is not an organizer. HTTPException(404) if track not found.
   * Side Effects: Deletes Track row; reindexes hackathon; busts cache.
   * Dependencies: app.models.Track, app.assistant.indexer.DocumentIndexer, app.cache.cache_delete_pattern.
   * Consumers: DELETE /api/hackathons/{hackathon_id}/tracks/{track_id}, organizer dashboard.
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
   * POST /api/hackathons/{hackathon_id}/upload — Upload File
   * Upload a file for registration answers (MinIO/S3).
   * Tags: registration-questions
   */
  async uploadFileApiHackathonsHackathonIdUploadPost(hackathon_id: string, file: File | Blob): Promise<unknown> {
    const formData = new FormData();
    if (file != null) formData.append('file', file);
    const url = `${this.baseUrl}/api/hackathons/${hackathon_id}/upload`;
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
   * GET /api/hackathons/{hackathon_id}/waitlist — List Waitlist
   * List waitlisted registrations with position. Organizer only.
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Delegate to RegistrationService.list_waitlist.
   * 3. Return the waitlist with pagination metadata.
   * 
   * Raises: HTTPException(404) if hackathon not found or not owned.
   * Side Effects: None (read-only).
   * Dependencies: app.services.registration_service.RegistrationService, app.auth.require_organizer.
   * Consumers: GET /api/hackathons/{hackathon_id}/waitlist, organizer dashboard.
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
   * 
   * Behavior:
   * 1. Verify the organizer owns the hackathon.
   * 2. Delegate to RegistrationService.manual_promote_waitlist.
   * 3. Return the promoted registration details.
   * 
   * Raises: HTTPException(404) if hackathon not found. HTTPException(409) if no one to promote or at capacity.
   * Side Effects: Mutates Registration status and offer_expires_at via waitlist promotion.
   * Dependencies: app.services.registration_service.RegistrationService.
   * Consumers: POST /api/hackathons/{hackathon_id}/waitlist/promote, organizer dashboard.
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
   * Return a simple health check response.
   * 
   * Behavior:
   * 1. Return a static JSON payload indicating the API is alive.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: None.
   * Consumers: GET /api/health, load balancers and uptime monitors.
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
   * 
   * Behavior:
   * 1. Fetch open help requests for the hackathon via HelpRequestService.
   * 2. Return serialized list of request dicts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.help_request_service.HelpRequestService.
   * Consumers: GET /api/help-requests, mentor queue view.
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
   * 
   * Behavior:
   * 1. Create the help request via HelpRequestService using the authenticated user's sub as requester_id.
   * 2. Return serialized request details.
   * 
   * Raises: None
   * Side Effects: Inserts help request row.
   * Dependencies: app.services.help_request_service.HelpRequestService, app.clerk_auth.require_clerk_user.
   * Consumers: POST /api/help-requests, hacker support form.
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
   * Get a single help request by ID.
   * 
   * Behavior:
   * 1. Fetch the help request via HelpRequestService.
   * 2. Return 404 if not found.
   * 3. Return serialized request details including claimed_at and resolved_at.
   * 
   * Raises: HTTPException(404) if the help request is not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.help_request_service.HelpRequestService.
   * Consumers: GET /api/help-requests/{request_id}, request detail view.
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
   * 
   * Behavior:
   * 1. Delete the request via HelpRequestService; 404 if not found.
   * 2. Return empty 204 response.
   * 
   * Raises: HTTPException(404) if the help request is not found.
   * Side Effects: Deletes help request row.
   * Dependencies: app.services.help_request_service.HelpRequestService.
   * Consumers: DELETE /api/help-requests/{request_id}, request management.
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
   * 
   * Behavior:
   * 1. Claim the request via HelpRequestService using the user's sub as mentor_id.
   * 2. Return 400 if the request is not claimable (e.g., already claimed).
   * 3. Return serialized request with claimed flag.
   * 
   * Raises: HTTPException(400) if the request is not claimable.
   * Side Effects: Mutates help request status and mentor_id.
   * Dependencies: app.services.help_request_service.HelpRequestService, app.clerk_auth.require_clerk_user.
   * Consumers: POST /api/help-requests/{request_id}/claim, mentor actions.
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
   * 
   * Behavior:
   * 1. Resolve the request via HelpRequestService.
   * 2. Return 400 if the request cannot be resolved.
   * 3. Return serialized request with resolved flag.
   * 
   * Raises: HTTPException(400) if the request cannot be resolved.
   * Side Effects: Mutates help request status and resolved_at.
   * Dependencies: app.services.help_request_service.HelpRequestService.
   * Consumers: POST /api/help-requests/{request_id}/resolve, mentor actions.
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
   * Strips client tool definitions and injects server-authorized ones based
   * on the user's role. Validates JWT token.
   * 
   * Behavior:
   * 1. Get server-authorized tools for the user's role.
   * 2. Determine the model based on the request model selector.
   * 3. Call the LLM with messages and authorized tools.
   * 4. Return the LLM response content.
   * 5. Raise 502 if the LLM service returns an error.
   * 
   * Raises: HTTPException(502) if LLM service returns an error.
   * Side Effects: None (read-only proxy).
   * Dependencies: app.assistant.permissions.get_tools_for_role, app.assistant.llm.llm_client.
   * Consumers: POST /api/llm/chat (mounted in main.py), LLM proxy.
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
   * POST /api/mentorship/{request_id}/accept — Accept Mentorship Request
   * Accept a pending mentorship request.
   * 
   * Behavior:
   * 1. Accept the request via MentorshipService.
   * 2. Return 404 if the request is not found, 400 if not pending.
   * 3. Return updated request details.
   * 
   * Raises: HTTPException(404) if the request is not found. HTTPException(400) if the request is not pending.
   * Side Effects: Updates MentorshipRequest status and mentor_id.
   * Dependencies: app.services.mentorship_service.MentorshipService.
   * Consumers: POST /api/mentorship/{id}/accept.
   * Tags: mentorship
   */
  async acceptMentorshipRequestApiMentorshipRequestIdAcceptPost(request_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/mentorship/${request_id}/accept`;
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
   * POST /api/mentorship/{request_id}/complete — Complete Mentorship Request
   * Mark a mentorship request as completed.
   * 
   * Behavior:
   * 1. Complete the request via MentorshipService.
   * 2. Return 404 if the request is not found, 403 if unauthorized, 400 if not accepted.
   * 3. Return updated request details.
   * 
   * Raises: HTTPException(404) if not found. HTTPException(403) if unauthorized. HTTPException(400) if not accepted.
   * Side Effects: Updates MentorshipRequest status to completed.
   * Dependencies: app.services.mentorship_service.MentorshipService.
   * Consumers: POST /api/mentorship/{id}/complete.
   * Tags: mentorship
   */
  async completeMentorshipRequestApiMentorshipRequestIdCompletePost(request_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/mentorship/${request_id}/complete`;
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
   * GET /api/monitoring/diagnostics — Diagnostics
   * Extended diagnostics for all subsystems.
   * 
   * Behavior:
   * 1. Ping the database and record status.
   * 2. Ping Redis and record version info if available.
   * 3. Check Discord bot readiness and guild count.
   * 4. Check background job scheduler status and job count.
   * 5. Check disk usage on /tmp.
   * 6. Aggregate statuses and return overall state with timestamp.
   * 
   * Raises: None
   * Side Effects: None (read-only probes).
   * Dependencies: app.database.async_session, app.cache.get_redis, app.discord_bot.bot, app.background_jobs.scheduler.
   * Consumers: GET /api/monitoring/diagnostics, admin health panel.
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
   * 
   * Behavior:
   * 1. Ping the database via async SQLAlchemy session.
   * 2. Ping Redis if configured.
   * 3. Check disk usage on /tmp.
   * 4. Aggregate subsystem statuses and determine overall healthy/degraded state.
   * 5. Return HealthStatus with timestamp and per-subsystem checks.
   * 
   * Raises: None
   * Side Effects: None (read-only probes).
   * Dependencies: app.database.async_session, app.cache.get_redis.
   * Consumers: GET /api/monitoring/health, load balancer and uptime checks.
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
   * 
   * Behavior:
   * 1. Return {"alive": True} immediately.
   * 
   * Raises: None
   * Side Effects: None.
   * Dependencies: None.
   * Consumers: GET /api/monitoring/live, Kubernetes liveness probe.
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
   * 
   * Behavior:
   * 1. Compute uptime from process start time.
   * 2. Calculate requests per minute, average response time, and error rate from in-memory counters.
   * 3. Return MetricsResponse with computed metrics.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: None.
   * Consumers: GET /api/monitoring/metrics, internal metrics dashboard.
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
   * 
   * Behavior:
   * 1. Compute uptime from process start time.
   * 2. Build Prometheus exposition lines for uptime, requests, errors, and active connections.
   * 3. Append per-endpoint request count metrics.
   * 4. Return plain-text Prometheus exposition format.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: None.
   * Consumers: GET /api/monitoring/metrics/prometheus, Prometheus scraper.
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
   * 
   * Behavior:
   * 1. Ping the database via async SQLAlchemy session.
   * 2. Return {"ready": True} on success, {"ready": False} on failure.
   * 
   * Raises: None
   * Side Effects: None (read-only probe).
   * Dependencies: app.database.async_session.
   * Consumers: GET /api/monitoring/ready, Kubernetes readiness probe.
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
   * 
   * Behavior:
   * 1. Return static version metadata including app version, Python version, FastAPI version, and placeholder build metadata.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: None.
   * Consumers: GET /api/monitoring/version, deployment info.
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
   * GET /api/notifications — List Notifications
   * List notifications for the current user.
   * 
   * Behavior:
   * 1. Instantiate NotificationService and list notifications for the authenticated user.
   * 2. Optionally filter by hackathon_id or unread_only.
   * 3. Return a paginated list of serialized notification dicts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.notification_service.NotificationService.
   * Consumers: GET /api/notifications, notification inbox UI.
   * Tags: notifications
   */
  async listNotificationsApiNotificationsGet(hackathon_id?: string | null, unread_only?: boolean, limit?: number, offset?: number): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    if (unread_only != null) params.append('unread_only', String(unread_only));
    if (limit != null) params.append('limit', String(limit));
    if (offset != null) params.append('offset', String(offset));
    const url = `${this.baseUrl}/api/notifications` + (params.toString() ? `?${params.toString()}` : '');
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
   * POST /api/notifications/read-all — Mark All As Read
   * Mark all notifications for the current user as read.
   * 
   * Behavior:
   * 1. Instantiate NotificationService and mark all unread notifications as read.
   * 2. Optionally restrict to a specific hackathon.
   * 3. Return the number of notifications marked as read.
   * 
   * Raises: None
   * Side Effects: Updates Notification.read_at for matching rows.
   * Dependencies: app.services.notification_service.NotificationService.
   * Consumers: POST /api/notifications/read-all, mark-all-read button.
   * Tags: notifications
   */
  async markAllAsReadApiNotificationsReadAllPost(hackathon_id?: string | null): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/notifications/read-all` + (params.toString() ? `?${params.toString()}` : '');
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
   * GET /api/notifications/unread-count — Get Unread Count
   * Get the number of unread notifications for the current user.
   * 
   * Behavior:
   * 1. Instantiate NotificationService and count unread notifications.
   * 2. Optionally restrict to a specific hackathon.
   * 3. Return the count.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.notification_service.NotificationService.
   * Consumers: GET /api/notifications/unread-count, notification badge.
   * Tags: notifications
   */
  async getUnreadCountApiNotificationsUnreadCountGet(hackathon_id?: string | null): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/notifications/unread-count` + (params.toString() ? `?${params.toString()}` : '');
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
   * DELETE /api/notifications/{notification_id} — Delete Notification
   * Delete a notification.
   * 
   * Behavior:
   * 1. Instantiate NotificationService and delete the notification.
   * 2. Return 404 if the notification does not exist or is not owned by the user.
   * 3. Return empty 204 response on success.
   * 
   * Raises: HTTPException(404) if the notification is not found or not owned.
   * Side Effects: Deletes a Notification row.
   * Dependencies: app.services.notification_service.NotificationService.
   * Consumers: DELETE /api/notifications/{id}, notification dismissal.
   * Tags: notifications
   */
  async deleteNotificationApiNotificationsNotificationIdDelete(notification_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/notifications/${notification_id}`;
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
   * POST /api/notifications/{notification_id}/read — Mark As Read
   * Mark a notification as read.
   * 
   * Behavior:
   * 1. Instantiate NotificationService and mark the notification as read.
   * 2. Return 404 if the notification does not exist or is not owned by the user.
   * 3. Return the serialized notification with read_at set.
   * 
   * Raises: HTTPException(404) if the notification is not found or not owned.
   * Side Effects: Updates Notification.read_at.
   * Dependencies: app.services.notification_service.NotificationService.
   * Consumers: POST /api/notifications/{id}/read, notification click handler.
   * Tags: notifications
   */
  async markAsReadApiNotificationsNotificationIdReadPost(notification_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/notifications/${notification_id}/read`;
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
   * GET /api/plugins — List Plugins
   * List all registered plugins.
   * 
   * Behavior:
   * 1. Query all registered plugins via PluginService.
   * 2. Serialize each plugin to a dict with full details.
   * 3. Return the list.
   * 
   * Side Effects: None (read-only).
   * Dependencies: app.services.plugin_service.PluginService.
   * Consumers: GET /api/plugins, plugin registry.
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
   * 
   * Behavior:
   * 1. Call PluginService to register the plugin with the given fields.
   * 2. Catch ValueError and raise 400 for duplicate names.
   * 3. Return the created plugin details.
   * 
   * Raises: HTTPException(400) if registration fails (e.g. duplicate name).
   * Side Effects: Inserts Plugin row via PluginService.
   * Dependencies: app.services.plugin_service.PluginService, app.clerk_auth.require_clerk_user.
   * Consumers: POST /api/plugins, plugin registry.
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
   * Get a single plugin by ID.
   * 
   * Behavior:
   * 1. Load the plugin via PluginService.
   * 2. Raise 404 if the plugin does not exist.
   * 3. Return the plugin details.
   * 
   * Raises: HTTPException(404) if plugin not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.plugin_service.PluginService.
   * Consumers: GET /api/plugins/{plugin_id}, plugin registry.
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
   * 
   * Behavior:
   * 1. Call PluginService to update the plugin by UUID with the given fields.
   * 2. Catch ValueError and raise 404 if the plugin is not found.
   * 3. Return the updated plugin id, name, enabled flag, and updated flag.
   * 
   * Raises: HTTPException(404) if plugin not found.
   * Side Effects: Mutates Plugin row via PluginService.
   * Dependencies: app.services.plugin_service.PluginService, app.clerk_auth.require_clerk_user.
   * Consumers: PUT /api/plugins/{plugin_id}, plugin registry.
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
   * 
   * Behavior:
   * 1. Call PluginService to delete the plugin by UUID.
   * 2. Catch ValueError and raise 404 if the plugin is not found.
   * 3. Return None (204 response).
   * 
   * Raises: HTTPException(404) if plugin not found.
   * Side Effects: Deletes Plugin row via PluginService.
   * Dependencies: app.services.plugin_service.PluginService, app.clerk_auth.require_clerk_user.
   * Consumers: DELETE /api/plugins/{plugin_id}, plugin registry.
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
   * 
   * Behavior:
   * 1. Fetch prizes for the hackathon via PrizeService.
   * 2. Return serialized list of prize dicts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.prize_service.PrizeService.
   * Consumers: GET /api/prizes, public prize listing.
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
   * 
   * Behavior:
   * 1. Create the prize via PrizeService using the provided payload fields.
   * 2. Return serialized prize details.
   * 
   * Raises: None
   * Side Effects: Inserts prize row.
   * Dependencies: app.services.prize_service.PrizeService, app.clerk_auth.require_clerk_user.
   * Consumers: POST /api/prizes, prize management.
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
   * Get a single prize by ID.
   * 
   * Behavior:
   * 1. Fetch the prize via PrizeService.
   * 2. Return 404 if not found.
   * 3. Return serialized prize details.
   * 
   * Raises: HTTPException(404) if the prize is not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.prize_service.PrizeService.
   * Consumers: GET /api/prizes/{prize_id}, prize detail view.
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
   * 
   * Behavior:
   * 1. Apply updates via PrizeService; 404 if prize not found.
   * 2. Return updated prize id, name, and updated flag.
   * 
   * Raises: HTTPException(404) if the prize is not found.
   * Side Effects: Mutates prize row.
   * Dependencies: app.services.prize_service.PrizeService.
   * Consumers: PUT /api/prizes/{prize_id}, prize management.
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
   * 
   * Behavior:
   * 1. Delete the prize via PrizeService; 404 if not found.
   * 2. Return empty 204 response.
   * 
   * Raises: HTTPException(404) if the prize is not found.
   * Side Effects: Deletes prize row.
   * Dependencies: app.services.prize_service.PrizeService.
   * Consumers: DELETE /api/prizes/{prize_id}, prize management.
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
   * DELETE /api/prizes/{prize_id}/award — Revoke Award
   * Revoke a prize award.
   * 
   * Behavior:
   * 1. Call PrizeService.revoke_award.
   * 2. Translate ValueError to HTTPException(404).
   * 3. Return empty 204 response.
   * 
   * Raises: HTTPException(404) if award not found.
   * Side Effects: Deletes PrizeAward row.
   * Dependencies: app.services.prize_service.PrizeService.
   * Consumers: DELETE /api/prizes/{prize_id}/award.
   * Tags: prizes
   */
  async revokeAwardApiPrizesPrizeIdAwardDelete(prize_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/prizes/${prize_id}/award`;
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
   * POST /api/prizes/{prize_id}/award/{team_id} — Award Prize
   * Award a prize to a team.
   * 
   * Behavior:
   * 1. Call PrizeService.award_prize.
   * 2. Translate ValueError to HTTPException(400 or 404).
   * 3. Return serialized award details.
   * 
   * Raises: HTTPException(404) if prize not found; HTTPException(400) if already awarded or hackathon mismatch.
   * Side Effects: Inserts PrizeAward row.
   * Dependencies: app.services.prize_service.PrizeService.
   * Consumers: POST /api/prizes/{prize_id}/award/{team_id}.
   * Tags: prizes
   */
  async awardPrizeApiPrizesPrizeIdAwardTeamIdPost(prize_id: string, team_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/prizes/${prize_id}/award/${team_id}`;
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
   * GET /api/qr — Get Qr Image
   * Serve a QR code PNG image for the given data.
   * 
   * Behavior:
   * 1. Generate a PNG QR code from the provided data string.
   * 2. Return it as a FastAPI Response with image/png content type.
   * 
   * Raises: None
   * Side Effects: None (read-only, CPU-bound image generation).
   * Dependencies: app.qr_generator.generate_qr_png.
   * Consumers: GET /api/qr, badge/QR display.
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
   * 
   * Behavior:
   * 1. Load the current user.
   * 2. Raise 401 if the user is not found.
   * 3. Count and query registrations filtered by user_id.
   * 4. Fetch registrations with eager-loaded users.
   * 5. Return the registration list with pagination metadata.
   * 
   * Raises: HTTPException(401) if user not found.
   * Side Effects: None (read-only).
   * Dependencies: app.models.Registration, app.models.User, app.auth.get_current_user.
   * Consumers: GET /api/registrations, participant profile.
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
   * 
   * Behavior:
   * 1. Load the current user.
   * 2. Raise 401 if the user is not found.
   * 3. Delegate to RegistrationService.get_registration.
   * 4. Return the full registration details.
   * 
   * Raises: HTTPException(401) if user not found. HTTPException(404) if registration not found or does not belong to user.
   * Side Effects: None (read-only).
   * Dependencies: app.services.registration_service.RegistrationService, app.auth.get_current_user.
   * Consumers: GET /api/registrations/{registration_id}, participant profile.
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
   * PUT /api/registrations/{registration_id} — Update Registration
   * Update a pending registration and its answers.
   * Tags: registrations
   */
  async updateRegistrationApiRegistrationsRegistrationIdPut(registration_id: string, body: { team_name?: string | null; team_members?: string[] | null; linkedin_url?: string | null; github_url?: string | null; resume_url?: string | null; experience_level?: string | null; t_shirt_size?: string | null; phone?: string | null; dietary_restrictions?: string | null; what_build?: string | null; why_participate?: string | null; age?: number | null; school?: string | null; major?: string | null; pronouns?: string | null; skills?: string[] | null; emergency_contact_name?: string | null; emergency_contact_phone?: string | null; invite_code?: string | null; answers?: unknown[] | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/registrations/${registration_id}`;
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
   * GET /api/sponsors — List Sponsors
   * List sponsors for a hackathon.
   * 
   * Behavior:
   * 1. Fetch sponsors for the hackathon via SponsorService.
   * 2. Return serialized list of sponsor dicts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.sponsor_service.SponsorService.
   * Consumers: GET /api/sponsors, public sponsor listing.
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
   * 
   * Behavior:
   * 1. Create the sponsor via SponsorService using the provided payload fields.
   * 2. Return serialized sponsor details.
   * 
   * Raises: None
   * Side Effects: Inserts sponsor row.
   * Dependencies: app.services.sponsor_service.SponsorService, app.clerk_auth.require_clerk_user.
   * Consumers: POST /api/sponsors, sponsor management.
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
   * Get a single sponsor by ID.
   * 
   * Behavior:
   * 1. Fetch the sponsor via SponsorService.
   * 2. Return 404 if not found.
   * 3. Return serialized sponsor details.
   * 
   * Raises: HTTPException(404) if the sponsor is not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.sponsor_service.SponsorService.
   * Consumers: GET /api/sponsors/{sponsor_id}, sponsor detail view.
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
   * 
   * Behavior:
   * 1. Apply updates via SponsorService; 404 if sponsor not found.
   * 2. Return updated sponsor id, name, and updated flag.
   * 
   * Raises: HTTPException(404) if the sponsor is not found.
   * Side Effects: Mutates sponsor row.
   * Dependencies: app.services.sponsor_service.SponsorService.
   * Consumers: PUT /api/sponsors/{sponsor_id}, sponsor management.
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
   * 
   * Behavior:
   * 1. Delete the sponsor via SponsorService; 404 if not found.
   * 2. Return empty 204 response.
   * 
   * Raises: HTTPException(404) if the sponsor is not found.
   * Side Effects: Deletes sponsor row.
   * Dependencies: app.services.sponsor_service.SponsorService.
   * Consumers: DELETE /api/sponsors/{sponsor_id}, sponsor management.
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
   * 
   * Behavior:
   * 1. Instantiate TeamService and attempt to create a team via the service.
   * 2. Catch ValueError and translate to HTTPException(400).
   * 3. Return the serialized team with id, name, join_code, captain_id, hackathon_id, and created_at.
   * 
   * Raises: HTTPException(400) if the user cannot create a team (no accepted registration or team already exists).
   * Side Effects: Inserts Team row via TeamService.
   * Dependencies: app.services.team_service.TeamService.
   * Consumers: POST /api/teams, team creation form.
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
   * 
   * Behavior:
   * 1. Instantiate TeamService and fetch the team by UUID.
   * 2. Return 404 if the team is not found.
   * 3. Build the members list from the team's member relationships.
   * 4. Return the serialized team with id, name, join_code, captain_id, hackathon_id, created_at, and members.
   * 
   * Raises: HTTPException(404) if the team does not exist.
   * Side Effects: None (read-only).
   * Dependencies: app.services.team_service.TeamService.
   * Consumers: GET /api/teams/{team_id}, team detail page.
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
   * 
   * Behavior:
   * 1. Instantiate TeamService and attempt to update the team name.
   * 2. Catch ValueError as 404 and PermissionError as 403.
   * 3. Return the serialized team with id, name, and updated flag.
   * 
   * Raises: HTTPException(404) if the team is not found. HTTPException(403) if the requesting user is not the captain.
   * Side Effects: Mutates Team.name via TeamService.
   * Dependencies: app.services.team_service.TeamService.
   * Consumers: PUT /api/teams/{team_id}, team settings form.
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
   * 
   * Behavior:
   * 1. Instantiate TeamService and attempt to join the team by code.
   * 2. Catch ValueError and translate to HTTPException(400).
   * 3. Return the serialized team with id, name, and joined flag.
   * 
   * Raises: HTTPException(400) if the join code is invalid or the user is already on the team.
   * Side Effects: Mutates team membership via TeamService.
   * Dependencies: app.services.team_service.TeamService.
   * Consumers: POST /api/teams/{team_id}/join, team join form.
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
   * 
   * Behavior:
   * 1. Instantiate TeamService and attempt to remove the member.
   * 2. Catch ValueError as 400 and PermissionError as 403.
   * 3. Return a confirmation dict with the removed user_id.
   * 
   * Raises: HTTPException(400) if the operation is invalid (e.g. removing self). HTTPException(403) if the requesting user is not the captain.
   * Side Effects: Deletes team membership via TeamService.
   * Dependencies: app.services.team_service.TeamService.
   * Consumers: DELETE /api/teams/{team_id}/members/{user_id}, team management panel.
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
   * GET /api/users/me/profile — Get My Profile
   * Get the current user's public profile.
   * 
   * Behavior:
   * 1. Load the user profile via ProfileService.
   * 2. Return 404 if the user is not found.
   * 3. Return serialized profile fields.
   * 
   * Raises: HTTPException(404) if the user is not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.profile_service.ProfileService, app.clerk_auth.require_clerk_user.
   * Consumers: GET /api/users/me/profile, profile page.
   * Tags: profiles
   */
  async getMyProfileApiUsersMeProfileGet(): Promise<unknown> {
    const url = `${this.baseUrl}/api/users/me/profile`;
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
   * PUT /api/users/me/profile — Update My Profile
   * Update the current user's public profile.
   * 
   * Behavior:
   * 1. Apply updates via ProfileService.
   * 2. Return 404 if the user is not found.
   * 3. Return serialized updated profile fields.
   * 
   * Raises: HTTPException(404) if the user is not found.
   * Side Effects: Mutates User profile fields.
   * Dependencies: app.services.profile_service.ProfileService, app.clerk_auth.require_clerk_user.
   * Consumers: PUT /api/users/me/profile, profile edit form.
   * Tags: profiles
   */
  async updateMyProfileApiUsersMeProfilePut(body: { bio?: string | null; skills?: unknown[] | null; links?: Record<string, unknown> | null; availability?: string | null; looking_for_team?: boolean | null }): Promise<unknown> {
    const url = `${this.baseUrl}/api/users/me/profile`;
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
   * POST /api/webhooks/subscribe — Subscribe
   * Create a new webhook subscription (organizer only).
   * 
   * Behavior:
   * 1. Build a WebhookSubscription from the request body.
   * 2. Persist the subscription to the database.
   * 3. Refresh and return the created subscription.
   * 
   * Side Effects: Inserts WebhookSubscription row.
   * Dependencies: app.models.WebhookSubscription, app.auth.require_organizer.
   * Consumers: POST /api/webhooks/subscribe, organizer dashboard.
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
   * 
   * Behavior:
   * 1. Query all WebhookSubscription rows from the database.
   * 2. Serialize each row to a SubscriptionResponse dict.
   * 3. Return the full list.
   * 
   * Side Effects: None (read-only).
   * Dependencies: app.models.WebhookSubscription, app.auth.require_organizer.
   * Consumers: GET /api/webhooks/subscriptions, organizer dashboard.
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
   * 
   * Behavior:
   * 1. Load the subscription by UUID.
   * 2. Raise 404 if the subscription does not exist.
   * 3. Delete the row and commit.
   * 
   * Raises: HTTPException(404) if subscription not found.
   * Side Effects: Deletes WebhookSubscription row.
   * Dependencies: app.models.WebhookSubscription, app.auth.require_organizer.
   * Consumers: DELETE /api/webhooks/subscriptions/{subscription_id}, organizer dashboard.
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
   * 
   * Behavior:
   * 1. Fetch workshops for the given hackathon via WorkshopService.
   * 2. Return serialized list of workshop dicts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: GET /api/workshops, public schedule view.
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
   * 
   * Behavior:
   * 1. Parse start_time and end_time from ISO strings.
   * 2. Create the workshop via WorkshopService.
   * 3. Return serialized workshop details.
   * 
   * Raises: None
   * Side Effects: Inserts workshop row.
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: POST /api/workshops, schedule management.
   * Tags: workshops
   */
  async createWorkshopApiWorkshopsPost(body: { hackathon_id: string; title: string; description?: string | null; start_time: string; end_time: string; location?: string | null; speaker_name?: string | null; max_capacity?: number | null }): Promise<unknown> {
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
   * GET /api/workshops/hackathons/{hackathon_id}/my-rsvps — List My Rsvps For Hackathon
   * List the current user's RSVPs for a hackathon.
   * 
   * Behavior:
   * 1. Call WorkshopService.list_rsvps_for_user.
   * 2. Return serialized list of RSVP dicts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: GET /api/hackathons/{hackathon_id}/my-rsvps.
   * Tags: workshops
   */
  async listMyRsvpsForHackathonApiWorkshopsHackathonsHackathonIdMyRsvpsGet(hackathon_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/workshops/hackathons/${hackathon_id}/my-rsvps`;
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
   * GET /api/workshops/{workshop_id} — Get Workshop
   * Get a single workshop by ID.
   * 
   * Behavior:
   * 1. Fetch the workshop via WorkshopService.
   * 2. Return 404 if not found.
   * 3. Return serialized workshop details.
   * 
   * Raises: HTTPException(404) if the workshop is not found.
   * Side Effects: None (read-only).
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: GET /api/workshops/{workshop_id}, schedule detail view.
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
   * 
   * Behavior:
   * 1. Parse optional start_time and end_time from ISO strings.
   * 2. Apply updates via WorkshopService; 404 if workshop not found.
   * 3. Return updated workshop id, title, and updated flag.
   * 
   * Raises: HTTPException(404) if the workshop is not found.
   * Side Effects: Mutates workshop row.
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: PUT /api/workshops/{workshop_id}, schedule management.
   * Tags: workshops
   */
  async updateWorkshopApiWorkshopsWorkshopIdPut(workshop_id: string, body: { title?: string | null; description?: string | null; start_time?: string | null; end_time?: string | null; location?: string | null; speaker_name?: string | null; max_capacity?: number | null }): Promise<unknown> {
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
   * 
   * Behavior:
   * 1. Delete the workshop via WorkshopService; 404 if not found.
   * 2. Return empty 204 response.
   * 
   * Raises: HTTPException(404) if the workshop is not found.
   * Side Effects: Deletes workshop row.
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: DELETE /api/workshops/{workshop_id}, schedule management.
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
   * POST /api/workshops/{workshop_id}/rsvp — Register For Workshop
   * Register the current user for a workshop.
   * 
   * Behavior:
   * 1. Call WorkshopService.register_for_workshop.
   * 2. Translate ValueError to HTTPException(400 or 404).
   * 3. Return serialized RSVP details.
   * 
   * Raises: HTTPException(400) if already registered or at capacity; HTTPException(404) if workshop not found.
   * Side Effects: Inserts WorkshopRSVP row.
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: POST /api/workshops/{workshop_id}/rsvp.
   * Tags: workshops
   */
  async registerForWorkshopApiWorkshopsWorkshopIdRsvpPost(workshop_id: string, hackathon_id: string): Promise<unknown> {
    const params = new URLSearchParams();
    if (hackathon_id != null) params.append('hackathon_id', String(hackathon_id));
    const url = `${this.baseUrl}/api/workshops/{workshop_id}/rsvp` + (params.toString() ? `?${params.toString()}` : '');
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
   * DELETE /api/workshops/{workshop_id}/rsvp — Cancel Rsvp
   * Cancel the current user's RSVP for a workshop.
   * 
   * Behavior:
   * 1. Call WorkshopService.cancel_rsvp.
   * 2. Translate ValueError to HTTPException(404).
   * 3. Return serialized RSVP with cancelled status.
   * 
   * Raises: HTTPException(404) if RSVP not found.
   * Side Effects: Updates WorkshopRSVP row.
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: DELETE /api/workshops/{workshop_id}/rsvp.
   * Tags: workshops
   */
  async cancelRsvpApiWorkshopsWorkshopIdRsvpDelete(workshop_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/workshops/${workshop_id}/rsvp`;
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
   * POST /api/workshops/{workshop_id}/rsvp/{user_id}/attended — Mark Attended
   * Mark a participant as attended (organizer only).
   * 
   * Behavior:
   * 1. Call WorkshopService.mark_attended.
   * 2. Translate ValueError to HTTPException(404).
   * 3. Return serialized RSVP with attended status.
   * 
   * Raises: HTTPException(404) if RSVP not found.
   * Side Effects: Updates WorkshopRSVP row.
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: POST /api/workshops/{workshop_id}/rsvp/{user_id}/attended.
   * Tags: workshops
   */
  async markAttendedApiWorkshopsWorkshopIdRsvpUserIdAttendedPost(workshop_id: string, user_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/workshops/${workshop_id}/rsvp/${user_id}/attended`;
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
   * GET /api/workshops/{workshop_id}/rsvps — List Workshop Rsvps
   * List all RSVPs for a workshop (organizer only).
   * 
   * Behavior:
   * 1. Call WorkshopService.list_rsvps_for_workshop.
   * 2. Return serialized list of RSVP dicts.
   * 
   * Raises: None
   * Side Effects: None (read-only).
   * Dependencies: app.services.workshop_service.WorkshopService.
   * Consumers: GET /api/workshops/{workshop_id}/rsvps.
   * Tags: workshops
   */
  async listWorkshopRsvpsApiWorkshopsWorkshopIdRsvpsGet(workshop_id: string): Promise<unknown> {
    const url = `${this.baseUrl}/api/workshops/${workshop_id}/rsvps`;
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
   * 
   * Behavior:
   * 1. Authenticate from the Authorization header.
   * 2. Raise 401 if authentication is missing or invalid.
   * 3. Lock and load the registration by id and user_id.
   * 4. Raise 404 if the registration is not found.
   * 5. Raise 409 if the registration is not in offered status.
   * 6. Raise 410 if the offer has expired.
   * 7. Check capacity one more time; revert to waitlist if the spot is taken.
   * 8. Update status to accepted, set accepted_at, and generate a QR token.
   * 9. Commit and send a confirmation email.
   * 10. Return the updated registration details.
   * 
   * Raises: HTTPException(401) if authentication missing or invalid. HTTPException(404) if registration not found. HTTPException(409) if registration not offered or spot taken. HTTPException(410) if offer expired.
   * Side Effects: Mutates Registration status, accepted_at, offer_expires_at, qr_token; sends email.
   * Dependencies: app.auth.decode_token, app.auth.create_qr_token, app.models.Registration, app.models.Hackathon, app.email_service.send_email.
   * Consumers: POST /api/{registration_id}/accept-offer, participant waitlist action.
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
   * 
   * Behavior:
   * 1. Authenticate from the Authorization header.
   * 2. Delegate to RegistrationService.decline_offer.
   * 3. Return the updated registration details.
   * 
   * Raises: HTTPException(401) if authentication missing or invalid. HTTPException(404) if registration not found. HTTPException(409) if registration not offered.
   * Side Effects: Mutates Registration status, offer_expires_at, declined_count; triggers waitlist promotion.
   * Dependencies: app.auth.decode_token, app.services.registration_service.RegistrationService.
   * Consumers: POST /api/{registration_id}/decline-offer, participant waitlist action.
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