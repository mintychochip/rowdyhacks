import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as matchers from '@testing-library/jest-dom/matchers';
expect.extend(matchers);
import JudgingResultsPage from '../JudgingResultsPage';

const { mockNavigate, mockParams, mockGetResults } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockParams: { id: 'mock-hackathon-id' },
  mockGetResults: vi.fn(),
}));

vi.mock('react-router-dom', () => ({
  useParams: () => mockParams,
  useNavigate: () => mockNavigate,
}));

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'u1', email: 'j@t.com', name: 'Judge', role: 'judge' },
    token: 'tok',
    isLoading: false,
  }),
}));

vi.mock('../../services/api', () => ({
  getJudgingResults: (...args: any[]) => mockGetResults(...args),
}));

describe('JudgingResultsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading text on mount', () => {
    mockGetResults.mockReturnValue(new Promise(() => {}));
    render(<JudgingResultsPage />);
    expect(screen.getByText('Computing rankings...')).toBeInTheDocument();
  });

  it('renders Bradley-Terry rankings and judge stats', async () => {
    mockGetResults.mockResolvedValue({
      hackathon_id: 'h',
      rankings: [
        { rank: 1, submission_id: 'a', project_title: 'Alpha', score: 8.5, score_se: 1.2, raw_avg: 75.0, judges: 3 },
        { rank: 2, submission_id: 'b', project_title: 'Beta', score: 3.1, score_se: 2.8, raw_avg: 68.0, judges: 3 },
        { rank: 3, submission_id: 'g', project_title: 'Gamma', score: -11.6, score_se: 1.5, raw_avg: 45.0, judges: 2 },
      ],
      judge_stats: [
        { judge_id: 'j1', name: 'Alice', severity: 15.2, precision: 0.45, sigma: 2.2, n_projects: 3 },
        { judge_id: 'j2', name: 'Bob', severity: -12.8, precision: 0.38, sigma: 2.6, n_projects: 3 },
        { judge_id: 'j3', name: 'Noisy', severity: -2.4, precision: 0.12, sigma: 8.3, n_projects: 2 },
      ],
    });

    render(<JudgingResultsPage />);

    // Use findByText which waits for async resolution
    expect(await screen.findByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('Beta')).toBeInTheDocument();
    expect(screen.getByText('Gamma')).toBeInTheDocument();

    // Scores (not ELO) + standard errors
    expect(screen.getByText('8.5')).toBeInTheDocument();
    expect(screen.getByText('±1.2')).toBeInTheDocument();
    expect(screen.getByText('-11.6')).toBeInTheDocument();

    // Columns
    expect(screen.getByText('Score')).toBeInTheDocument();
    expect(screen.getByText('±SE')).toBeInTheDocument();

    // Judge stats
    expect(screen.getByText('Judge Analysis')).toBeInTheDocument();
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Noisy')).toBeInTheDocument();

    // Severity values
    expect(screen.getByText('+15.2')).toBeInTheDocument();
    expect(screen.getByText('-12.8')).toBeInTheDocument();

    // Noisy judge has sigma=8.3
    expect(screen.getByText('8.3')).toBeInTheDocument();
    // And lowest precision
    expect(screen.getByText('0.12')).toBeInTheDocument();
  });

  it('shows error on API failure', async () => {
    mockGetResults.mockRejectedValue(new Error('Boom'));
    render(<JudgingResultsPage />);
    expect(await screen.findByText('Boom')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });
});
