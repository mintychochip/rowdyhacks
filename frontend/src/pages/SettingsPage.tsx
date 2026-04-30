import LinkedAccounts from '../components/LinkedAccounts';
import { TEXT_PRIMARY, TYPO, SPACE } from '../theme';
import { useMediaQuery } from '../hooks/useMediaQuery';

export default function SettingsPage() {
  const { isMobile } = useMediaQuery();
  return (
    <div style={{ maxWidth: 600, margin: isMobile ? '20px auto' : '40px auto', padding: isMobile ? 14 : 24 }}>
      <h1 style={{ ...TYPO.h1, color: TEXT_PRIMARY, marginBottom: SPACE.lg }}>Account Settings</h1>
      <LinkedAccounts />
    </div>
  );
}
