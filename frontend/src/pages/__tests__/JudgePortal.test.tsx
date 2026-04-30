import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as matchers from '@testing-library/jest-dom/matchers';
expect.extend(matchers);
import JudgePortal from '../JudgePortal';

const { mockNavigate, mockParams, mockGetQueue } = vi.hoisted(() => ({
  mockNavigate: vi.fn(),
  mockParams: { id: 'mock-hackathon-id' },
  mockGetQueue: vi.fn(),
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
  getJudgingQueue: (...args: any[]) => mockGetQueue(...args),
}));

describe('JudgePortal', () => {
  afterEach(() => cleanup());
  beforeEach(() => vi.clearAllMocks());

  it('shows loading text on mount', () => {
    mockGetQueue.mockReturnValue(new Promise(() => {}));
    render(<JudgePortal />);
    expect(screen.getByText('Loading next project...')).toBeInTheDocument();
  });

  it('shows empty state when queue is empty', async () => {
    mockGetQueue.mockResolvedValue({ queue: [] });
    render(<JudgePortal />);
    await waitFor(() => {
      expect(screen.getByText('All Caught Up!')).toBeInTheDocument();
    });
  });

  it('shows the first project from the queue for scoring', async () => {
    mockGetQueue.mockResolvedValue({
      queue: [
        {
          assignment_id: 'asgn-1',
          submission_id: 'sub-a',
          project_title: 'Project Alpha',
          devpost_url: 'https://devpost.com/alpha',
          github_url: null,
          reasons: ['needs_coverage'],
        },
        {
          assignment_id: 'asgn-2',
          submission_id: 'sub-b',
          project_title: 'Project Beta',
          devpost_url: 'https://devpost.com/beta',
          github_url: null,
          reasons: ['needs_coverage'],
        },
      ],
    });

    render(<JudgePortal />);

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    // Only shows first project, not second
    expect(screen.queryByText('Project Beta')).not.toBeInTheDocument();

    // Submit button
    expect(screen.getByText('Submit Scores')).toBeInTheDocument();

    // Controls
    expect(screen.getByText('Refresh')).toBeInTheDocument();
    expect(screen.getByText('View Results')).toBeInTheDocument();
  });

  it('navigates to results when View Results clicked', async () => {
    mockGetQueue.mockResolvedValue({ queue: [] });
    render(<JudgePortal />);
    await waitFor(() => {
      expect(screen.getByText('View Results')).toBeInTheDocument();
    });
    screen.getByText('View Results').click();
    expect(mockNavigate).toHaveBeenCalledWith('/hackathons/mock-hackathon-id/judging/results');
  });
});
