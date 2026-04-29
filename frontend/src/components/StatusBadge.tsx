const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  pending: { bg: '#f59e0b20', text: '#f59e0b' },
  accepted: { bg: '#10b98120', text: '#10b981' },
  rejected: { bg: '#ef444420', text: '#ef4444' },
  checked_in: { bg: '#3b82f620', text: '#3b82f6' },
};

export default function StatusBadge({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] || { bg: '#333', text: '#999' };
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      background: colors.bg,
      color: colors.text,
      textTransform: 'capitalize',
    }}>
      {status.replace('_', ' ')}
    </span>
  );
}
