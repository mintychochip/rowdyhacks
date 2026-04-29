import { useState, useRef, useCallback } from 'react';
import * as api from '../services/api';

interface AnalysisResult {
  id: string;
  project_title?: string;
  status: string;
  stage?: string;
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

export function useAnalysis() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'polling' | 'done' | 'error'>('idle');
  const [stage, setStage] = useState<string>('');
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
    setResult(null);
    setError('');
  }, []);

  return { submit, reset, result, status, stage, error };
}
