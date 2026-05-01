const BASE = '/api';

export async function request(path: string, options: RequestInit = {}) {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

// Auth
export const register = (data: { email: string; name: string; password: string }) =>
  request('/auth/register', { method: 'POST', body: JSON.stringify(data) });

export const login = (data: { email: string; password: string }) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify(data) });

export const getMe = () => request('/auth/me');

// Checks
export const submitUrl = (url: string) =>
  request('/check', { method: 'POST', body: JSON.stringify({ url }) });

export const getCheckStatus = (id: string, token?: string) => {
  const query = token ? `?token=${token}` : '';
  return request(`/check/${id}${query}`);
};

export const getCheckReport = (id: string, token?: string) => {
  const query = token ? `?token=${token}` : '';
  return request(`/check/${id}/report${query}`);
};

export const retryCheck = (id: string) =>
  request(`/check/${id}/retry`, { method: 'POST' });

// Dashboard
export const getDashboard = (params?: { hackathon_id?: string; status?: string; verdict?: string; page?: number }) => {
  const searchParams = new URLSearchParams();
  if (params?.hackathon_id) searchParams.set('hackathon_id', params.hackathon_id);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.verdict) searchParams.set('verdict', params.verdict);
  if (params?.page) searchParams.set('page', String(params.page));
  const query = searchParams.toString();
  return request(`/dashboard${query ? `?${query}` : ''}`);
};

// Hackathons
export const createHackathon = (data: { name: string; start_date: string; end_date: string; description?: string }) =>
  request('/hackathons', { method: 'POST', body: JSON.stringify(data) });

export const getHackathons = () => request('/hackathons');

export const getHackathon = (id: string) => request(`/hackathons/${id}`);
export const updateHackathon = (id: string, data: Record<string, any>) =>
  request(`/hackathons/${id}`, { method: 'PUT', body: JSON.stringify(data) });
export const getHackathonSubmissions = (id: string) => request(`/hackathons/${id}/submissions`);
export const getHackathonStats = (id: string) => request(`/hackathons/${id}/stats`);
export const getHackathonTracks = (id: string) => request(`/hackathons/${id}/tracks`);
export const getHackerDashboard = (id: string) => request(`/hackathons/${id}/hacker-dashboard`);

export const runSimilarity = (hackathonId: string) =>
  request(`/hackathons/${hackathonId}/similarity`, { method: 'POST' });

// Registrations
export const registerForHackathon = (hackathonId: string, data?: {
  team_name?: string;
  team_members?: string[];
  linkedin_url?: string;
  github_url?: string;
  resume_url?: string;
  experience_level?: string;
  t_shirt_size?: string;
  phone?: string;
  dietary_restrictions?: string;
  what_build?: string;
  why_participate?: string;
  age?: number;
  school?: string;
  major?: string;
  pronouns?: string;
  skills?: string[];
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
}) => {
  return request(`/hackathons/${hackathonId}/register`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  });
};

export const getRegistrations = (params?: { hackathon_id?: string; status?: string }) => {
  const searchParams = new URLSearchParams();
  if (params?.hackathon_id) searchParams.set('hackathon_id', params.hackathon_id);
  if (params?.status) searchParams.set('status', params.status);
  const query = searchParams.toString();
  return request(`/registrations${query ? `?${query}` : ''}`);
};

export const updateRegistrationStatus = (id: string, status: string) =>
  request(`/registrations/${id}?status=${status}`, { method: 'PATCH' });

export const checkIn = (qrToken: string) =>
  request(`/registrations/check-in?qr_token=${qrToken}`, { method: 'POST' });

export const getRegistrationStats = (hackathonId: string) =>
  request(`/registrations/stats?hackathon_id=${hackathonId}`);

export const getMyRegistrations = (params?: { offset?: number; limit?: number }) => {
  const searchParams = new URLSearchParams();
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  const query = searchParams.toString();
  return request(`/registrations${query ? `?${query}` : ''}`);
};

export const getRegistration = (id: string) => request(`/registrations/${id}`);

export const getOrganizerRegistrations = (hackathonId: string, params?: { status?: string; offset?: number; limit?: number }) => {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  const query = searchParams.toString();
  return request(`/hackathons/${hackathonId}/registrations${query ? `?${query}` : ''}`);
};

export const acceptRegistration = (hackathonId: string, registrationId: string) =>
  request(`/hackathons/${hackathonId}/registrations/${registrationId}/accept`, { method: 'POST' });

export const rejectRegistration = (hackathonId: string, registrationId: string) =>
  request(`/hackathons/${hackathonId}/registrations/${registrationId}/reject`, { method: 'POST' });

export const checkinRegistration = (hackathonId: string, registrationId: string) =>
  request(`/hackathons/${hackathonId}/registrations/${registrationId}/checkin`, { method: 'POST' });


// Bulk Operations
export const bulkAcceptRegistrations = (hackathonId: string, registrationIds: string[]) =>
  request(`/hackathons/${hackathonId}/registrations/bulk-accept`, { method: 'POST', body: JSON.stringify(registrationIds) });

export const bulkRejectRegistrations = (hackathonId: string, registrationIds: string[]) =>
  request(`/hackathons/${hackathonId}/registrations/bulk-reject`, { method: 'POST', body: JSON.stringify(registrationIds) });

export const bulkWaitlistRegistrations = (hackathonId: string, registrationIds: string[]) =>
  request(`/hackathons/${hackathonId}/registrations/bulk-waitlist`, { method: 'POST', body: JSON.stringify(registrationIds) });

export const exportRegistrationsCSV = (hackathonId: string) =>
  `${BASE}/hackathons/${hackathonId}/registrations/export`;

export const getSwagCounts = (hackathonId: string) =>
  request(`/hackathons/${hackathonId}/swag-counts`);

// Announcements
export const createAnnouncement = (hackathonId: string, data: { title: string; content: string; priority?: string }) =>
  request(`/hackathons/${hackathonId}/announcements`, { method: 'POST', body: JSON.stringify(data) });

export const getAnnouncements = (hackathonId: string) =>
  request(`/hackathons/${hackathonId}/announcements`);

// Conflict of Interest
export const declareConflictOfInterest = (hackathonId: string, submissionId: string, reason?: string) =>
  request(`/hackathons/${hackathonId}/conflicts-of-interest`, { method: 'POST', body: JSON.stringify({ submission_id: submissionId, reason }) });

export const getConflictsOfInterest = (hackathonId: string) =>
  request(`/hackathons/${hackathonId}/conflicts-of-interest`);

export const removeConflictOfInterest = (hackathonId: string, coiId: string) =>
  request(`/hackathons/${hackathonId}/conflicts-of-interest/${coiId}`, { method: 'DELETE' });

// Judging
export const createJudgingSession = (hackathonId: string, data: {
  start_time: string; end_time: string; per_project_seconds: number; criteria: Array<{ name: string; description?: string; max_score: number; weight: number; sort_order?: number }>;
}) => request(`/hackathons/${hackathonId}/judging/session`, { method: 'POST', body: JSON.stringify(data) });

export const getJudgingSession = (hackathonId: string) => request(`/hackathons/${hackathonId}/judging/session`);

export const assignJudges = (hackathonId: string, judgeIds: string[], submissionIds: string[]) =>
  request(`/hackathons/${hackathonId}/judging/assign`, { method: 'POST', body: JSON.stringify({ judge_ids: judgeIds, submission_ids: submissionIds }) });

export const getJudgeAssignments = (hackathonId: string, judgeId?: string) => {
  const params = new URLSearchParams();
  if (judgeId) params.set('judge_id', judgeId);
  params.set('include_completed', 'true');
  return request(`/hackathons/${hackathonId}/judging/assignments?${params}`);
};

export const getAssignmentDetail = (assignmentId: string) => request(`/judging/assignments/${assignmentId}`);

export const openAssignment = (assignmentId: string) => request(`/judging/assignments/${assignmentId}/open`, { method: 'POST' });

export const submitScores = (assignmentId: string, scores: Array<{ criterion_id: string; score: number | null }>) =>
  request(`/judging/assignments/${assignmentId}/score`, { method: 'POST', body: JSON.stringify({ scores }) });

export const getJudgingResults = (hackathonId: string) => request(`/hackathons/${hackathonId}/judging/results`);

export const activateJudging = (hackathonId: string) => request(`/hackathons/${hackathonId}/judging/activate`, { method: 'POST' });

export const closeJudging = (hackathonId: string) => request(`/hackathons/${hackathonId}/judging/close`, { method: 'POST' });

export const getJudgingQueue = (hackathonId: string, judgeId: string, minJudges?: number) => {
  const params = new URLSearchParams({ judge_id: judgeId });
  if (minJudges !== undefined) params.set('min_judges', String(minJudges));
  return request(`/hackathons/${hackathonId}/judging/queue?${params}`);
};

export const rerunJudging = (hackathonId: string) =>
  request(`/hackathons/${hackathonId}/judging/rerun`, { method: 'POST' });

// OAuth
export const getOAuthAuthorizeUrl = (provider: string) =>
  `${BASE}/auth/oauth/${provider}/authorize`;

export const getOAuthLinkUrl = (provider: string) =>
  `${BASE}/auth/me/oauth/link/${provider}`;

export const getLinkedAccounts = () =>
  request('/auth/me/oauth');

export const unlinkProvider = (provider: string) =>
  request(`/auth/me/oauth/${provider}`, { method: 'DELETE' });

// Co-Organizers
export const getOrganizers = (hackathonId: string) =>
  request(`/hackathons/${hackathonId}/organizers`);

export const addOrganizer = (hackathonId: string, email: string) =>
  request(`/hackathons/${hackathonId}/organizers`, { method: 'POST', body: JSON.stringify({ email }) });

export const removeOrganizer = (hackathonId: string, userId: string) =>
  request(`/hackathons/${hackathonId}/organizers/${userId}`, { method: 'DELETE' });
