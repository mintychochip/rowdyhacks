import { useEffect, useState } from 'react';

interface CountdownState {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  isExpired: boolean;
  elapsedPercent: number;
}

export function useCountdown(targetDate: string, startDate?: string): CountdownState {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const target = new Date(targetDate).getTime();
  const start = startDate ? new Date(startDate).getTime() : null;

  const total = start != null ? target - start : null;
  const remaining = target - now;

  if (remaining <= 0) {
    return { days: 0, hours: 0, minutes: 0, seconds: 0, isExpired: true, elapsedPercent: 100 };
  }

  const days = Math.floor(remaining / (1000 * 60 * 60 * 24));
  const hours = Math.floor((remaining % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((remaining % (1000 * 60)) / 1000);

  let elapsedPercent = 0;
  if (total && total > 0) {
    const elapsed = now - start!;
    elapsedPercent = Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)));
  }

  return { days, hours, minutes, seconds, isExpired: false, elapsedPercent };
}
