import { useEffect, useRef } from 'react';
import { PRIMARY } from '../theme';

interface QRCodeDisplayProps {
  token: string;
  size?: number;
}

export default function QRCodeDisplay({ token, size = 280 }: QRCodeDisplayProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !token) return;
    const baseUrl = window.location.origin;
    const qrUrl = `${baseUrl}/api/qr?data=${encodeURIComponent(token)}`;

    const canvas = canvasRef.current;
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, size, size);

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, size, size);
    };
    img.onerror = () => {
      ctx.fillStyle = '#000';
      ctx.font = '12px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('QR unavailable', size / 2, size / 2);
    };
    img.src = qrUrl;
  }, [token, size]);

  return (
    <div style={{
      background: '#fff',
      borderRadius: 12,
      padding: 16,
      display: 'inline-block',
      boxShadow: `0 4px 24px ${PRIMARY}26`,
    }}>
      <canvas ref={canvasRef} width={size} height={size} style={{ display: 'block', borderRadius: 8 }} />
    </div>
  );
}
