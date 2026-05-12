import {
  WARNING, WARNING_BG10,
  SUCCESS, SUCCESS_BG10,
  ERROR, ERROR_BG10,
  INFO, INFO_BG10,
  TEXT_MUTED, INPUT_BG,
} from '../theme';

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  pending: { bg: WARNING_BG10, text: WARNING },
  accepted: { bg: SUCCESS_BG10, text: SUCCESS },
  rejected: { bg: ERROR_BG10, text: ERROR },
  checked_in: { bg: INFO_BG10, text: INFO },
};

export default function StatusBadge({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] || { bg: INPUT_BG, text: TEXT_MUTED };
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
