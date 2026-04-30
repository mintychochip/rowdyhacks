import { useEffect, useState } from 'react';

function hasMatchMedia() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function';
}

function getInitial() {
  if (!hasMatchMedia()) return { isMobile: false, isTablet: false };
  return {
    isMobile: window.matchMedia('(max-width: 768px)').matches,
    isTablet: window.matchMedia('(min-width: 769px) and (max-width: 1024px)').matches,
  };
}

export function useMediaQuery() {
  const [isMobile, setIsMobile] = useState(() => getInitial().isMobile);
  const [isTablet, setIsTablet] = useState(() => getInitial().isTablet);

  useEffect(() => {
    if (!hasMatchMedia()) return;

    const mobileQuery = window.matchMedia('(max-width: 768px)');
    const tabletQuery = window.matchMedia('(min-width: 769px) and (max-width: 1024px)');

    const update = () => {
      setIsMobile(mobileQuery.matches);
      setIsTablet(tabletQuery.matches);
    };

    mobileQuery.addEventListener('change', update);
    tabletQuery.addEventListener('change', update);

    return () => {
      mobileQuery.removeEventListener('change', update);
      tabletQuery.removeEventListener('change', update);
    };
  }, []);

  return { isMobile, isTablet };
}
