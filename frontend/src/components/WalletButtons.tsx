import { getApplePassUrl } from '../services/api';

interface WalletButtonsProps {
  registrationId: string;
  googleSaveUrl?: string;
}

export default function WalletButtons({ registrationId, googleSaveUrl }: WalletButtonsProps) {
  if (!registrationId) return null;

  const appleUrl = getApplePassUrl(registrationId);

  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
      <a href={appleUrl} style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 20px',
        background: '#000',
        color: '#fff',
        borderRadius: 10,
        textDecoration: 'none',
        fontSize: 14,
        fontWeight: 600,
        border: 'none',
        cursor: 'pointer',
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
        Add to Apple Wallet
      </a>
      {googleSaveUrl && (
        <a href={googleSaveUrl} target="_blank" rel="noopener noreferrer" style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 20px',
          background: '#4285F4',
          color: '#fff',
          borderRadius: 10,
          textDecoration: 'none',
          fontSize: 14,
          fontWeight: 600,
          border: 'none',
          cursor: 'pointer',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-.15 15.5H9.5v-4.5h2.35v4.5zm0-5.85H9.5V9.5h2.35v2.15zM17 15.5h-2.35v-1.5H17v1.5zm0-3h-2.35v-1.5H17v1.5z" fill="white"/></svg>
          Add to Google Wallet
        </a>
      )}
    </div>
  );
}
