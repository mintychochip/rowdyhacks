const BASE = '/api';

async function request(path: string, options: RequestInit = {}) {
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
export const createHackathon = (data: { name: string; start_date: string; end_date: string }) =>
  request('/hackathons', { method: 'POST', body: JSON.stringify(data) });

export const getHackathons = () => request('/hackathons');

export const getHackathonStats = (id: string) => request(`/hackathons/${id}/stats`);

export const runSimilarity = (hackathonId: string) =>
  request(`/hackathons/${hackathonId}/similarity`, { method: 'POST' });

// Registrations
export const registerForHackathon = (hackathonId: string, data?: { team_name?: string; team_members?: string[] }) => {
  return request('/registrations', {
    method: 'POST',
    body: JSON.stringify({ hackathon_id: hackathonId, ...data }),
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

export const getApplePassUrl = (registrationId: string) => `${BASE}/registrations/${registrationId}/wallet/apple`;
export const getGoogleWalletLink = (registrationId: string) => request(`/registrations/${registrationId}/wallet/google`);

// Judging
export const createJudgingSession = (hackathonId: string, data: {
  start_time: string; end_time: string; per_project_seconds: number; criteria: Array<{ name: string; description?: string; max_score: number; weight: number; sort_order?: number }>;
}) => request(`/hackathons/${hackathonId}/judging/session`, { method: 'POST', body: JSON.stringify(data) });

export const getJudgingSession = (hackathonId: string) => request(`/hackathons/${hackathonId}/judging/session`);

export const assignJudges = (hackathonId: string, judgeIds: string[], submissionIds: string[]) =>
  request(`/hackathons/${hackathonId}/judging/assign`, { method: 'POST', body: JSON.stringify({ judge_ids: judgeIds, submission_ids: submissionIds }) });

export const getJudgeAssignments = (hackathonId: string, judgeId?: string) => {
  const params = judgeId ? `?judge_id=${judgeId}` : '';
  return request(`/hackathons/${hackathonId}/judging/assignments${params}`);
};

export const getAssignmentDetail = (assignmentId: string) => request(`/judging/assignments/${assignmentId}`);

export const openAssignment = (assignmentId: string) => request(`/judging/assignments/${assignmentId}/open`, { method: 'POST' });

export const submitScores = (assignmentId: string, scores: Array<{ criterion_id: string; score: number | null }>) =>
  request(`/judging/assignments/${assignmentId}/score`, { method: 'POST', body: JSON.stringify({ scores }) });

export const getJudgingResults = (hackathonId: string) => request(`/hackathons/${hackathonId}/judging/results`);

export const activateJudging = (hackathonId: string) => request(`/hackathons/${hackathonId}/judging/activate`, { method: 'POST' });

export const closeJudging = (hackathonId: string) => request(`/hackathons/${hackathonId}/judging/close`, { method: 'POST' });
