import { SUCCESS, WARNING, ERROR, INPUT_BG, TEXT_WHITE } from '../theme';

interface Props { score: number; verdict: string; size?: number; }

function getColor(score: number): string {
  if (score <= 30) return SUCCESS;
  if (score <= 60) return WARNING;
  return ERROR;
}

function getVerdictLabel(verdict: string): string {
  if (verdict === 'clean') return 'Clean';
  if (verdict === 'review') return 'Needs Review';
  if (verdict === 'flagged') return 'Flagged';
  return verdict;
}

export default function ScoreCircle({ score, verdict, size = 160 }: Props) {
  const color = getColor(score);
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div style={{ textAlign: 'center' }}>
      <svg width={size} height={size} viewBox="0 0 160 160">
        <circle cx={80} cy={80} r={radius} fill="none" stroke={INPUT_BG} strokeWidth={10} />
        <circle cx={80} cy={80} r={radius} fill="none" stroke={color} strokeWidth={10}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" transform="rotate(-90 80 80)"
          style={{ transition: 'stroke-dashoffset 1s ease' }} />
        <text x={80} y={72} textAnchor="middle" fill="#fff" fontSize={36} fontWeight={700}>{score}</text>
        <text x={80} y={96} textAnchor="middle" fill={color} fontSize={13} fontWeight={600}>{getVerdictLabel(verdict)}</text>
      </svg>
    </div>
  );
}
