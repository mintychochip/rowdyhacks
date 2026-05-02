import { useState, useRef, useCallback } from 'react';
import * as api from '../services/api';

interface CheckProgress {
  completed: string[];
  pending: string[];
  current: string | null;
}

interface AnalysisResult {
  id: string;
  project_title?: string;
  status: string;
  stage?: string;
  check_progress?: CheckProgress;
  risk_score: number | null;
  verdict: string | null;
  check_results: Array<{
    check_name: string;
    check_category: string;
    score: number;
    status: string;
    details: Record<string, any>;
    evidence: string[];
  }>;
}

const CHECK_LABELS: Record<string, string> = {
  timeline: 'Commit analysis',
  commit_quality: 'Commit quality',
  devpost_alignment_ai: 'AI claim verification',
  dead_deps: 'Dead dependencies',
  submission_history: 'Submission history',
  contributor_audit: 'Contributor audit',
  asset_integrity: 'Asset integrity',
  ai_detection: 'AI pattern detection',
  cross_hackathon: 'Cross-hackathon check',
  repeat_offender: 'Repeat offender',
};

export function useAnalysis() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'polling' | 'done' | 'error'>('idle');
  const [stage, setStage] = useState<string>('');
  const [checkProgress, setCheckProgress] = useState<CheckProgress | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string>('');
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const submit = useCallback(async (url: string) => {
    setStatus('loading');
    setError('');
    try {
      const data = await api.submitUrl(url);
      const submissionId = data.id;
      const accessToken = data.access_token;
      if (accessToken) localStorage.setItem('anonymous_token', accessToken);

      setStatus('polling');
      pollingRef.current = setInterval(async () => {
        try {
          const statusData = await api.getCheckStatus(submissionId, accessToken);
          if (statusData.stage) setStage(statusData.stage);
          if (statusData.check_progress) setCheckProgress(statusData.check_progress);
          if (statusData.status === 'completed' || statusData.status === 'failed') {
            if (pollingRef.current) clearInterval(pollingRef.current);
            setResult(statusData);
            setStatus('done');
          }
        } catch (err: any) {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setStatus('error');
          setError(err?.message || 'Failed to check status');
        }
      }, 2000);
    } catch (err: any) {
      setStatus('error');
      setError(err.message || 'Failed to submit');
    }
  }, []);

  const reset = useCallback(() => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    setStatus('idle');
    setStage('');
    setCheckProgress(null);
    setResult(null);
    setError('');
  }, []);

  const hasGithub = result?.github_url != null;

  return { submit, reset, result, status, stage, checkProgress, CHECK_LABELS, error, hasGithub };
}
