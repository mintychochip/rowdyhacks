import ScoreCircle from './ScoreCircle';
import { SUCCESS, WARNING, ERROR, TEXT_PRIMARY, TEXT_SECONDARY, CARD_BG, BORDER, INPUT_BG } from '../theme';

interface Props {
  projectTitle?: string;
  riskScore: number;
  verdict: string;
  categories: Array<{ category: string; score: number }>;
}

export default function ReportCard({ projectTitle, riskScore, verdict, categories }: Props) {
  return (
    <div style={{ background: CARD_BG, border: `1px solid ${BORDER}`, borderRadius: 12, padding: 32, marginBottom: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 40, flexWrap: 'wrap' }}>
        <ScoreCircle score={riskScore} verdict={verdict} />
        <div style={{ flex: 1, minWidth: 250 }}>
          {projectTitle && <h3 style={{ fontSize: 22, marginBottom: 16 }}>{projectTitle}</h3>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {categories.map(cat => (
              <div key={cat.category} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, color: TEXT_SECONDARY, width: 140, textTransform: 'capitalize' }}>{cat.category.replace('_', ' ')}</span>
                <div style={{ flex: 1, height: 8, background: INPUT_BG, borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${cat.score}%`, background: cat.score <= 30 ? SUCCESS : cat.score <= 60 ? WARNING : ERROR, borderRadius: 4, transition: 'width 0.5s ease' }} />
                </div>
                <span style={{ fontSize: 12, color: TEXT_PRIMARY, minWidth: 28, textAlign: 'right' }}>{cat.score}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
