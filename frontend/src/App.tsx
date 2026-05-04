import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import AnalyzePage from './pages/AnalyzePage';
import ReportPage from './pages/ReportPage';
import AssistantPage from './pages/AssistantPage';
import Dashboard from './pages/Dashboard';
import AuthPage from './pages/AuthPage';
import RegisterPage from './pages/RegisterPage';
import ApplyPage from './pages/ApplyPage';
import RegistrationsPage from './pages/RegistrationsPage';
import RegistrationDetailPage from './pages/RegistrationDetailPage';
import OrganizerRegistrationsPage from './pages/OrganizerRegistrationsPage';
import CheckInPage from './pages/CheckInPage';
import RubricBuilderPage from './pages/RubricBuilderPage';
import TracksEditorPage from './pages/TracksEditorPage';
import JudgePortal from './pages/JudgePortal';
import JudgingResultsPage from './pages/JudgingResultsPage';
import HackathonDetailPage from './pages/HackathonDetailPage';
import HackerDashboard from './pages/HackerDashboard';
import HackathonSettings from './pages/HackathonSettings';
import JudgeRedirect from './pages/JudgeRedirect';
import ProjectGallery from './pages/ProjectGallery';
import PublicLeaderboard from './pages/PublicLeaderboard';
import TracksPage from './pages/TracksPage';
import CrawledDataPage from './pages/CrawledDataPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/analyze" element={<AnalyzePage />} />
            <Route path="/report/:id" element={<ReportPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/hackathons" element={<Navigate to="/" replace />} />
            <Route path="/apply" element={<ApplyPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/hackathons/:id/register" element={<ApplyPage />} />
            <Route path="/registrations" element={<RegistrationsPage />} />
            <Route path="/registrations/:id" element={<RegistrationDetailPage />} />
            <Route path="/hackathons/:id/registrations" element={<OrganizerRegistrationsPage />} />
            <Route path="/check-in" element={<CheckInPage />} />
            <Route path="/hackathons/:id/judging/setup" element={<RubricBuilderPage />} />
            <Route path="/hackathons/:id/judging" element={<JudgePortal />} />
            <Route path="/hackathons/:id/judging/results" element={<JudgingResultsPage />} />
            <Route path="/hackathons/:id/projects" element={<ProjectGallery />} />
            <Route path="/hackathons/:id/leaderboard" element={<PublicLeaderboard />} />
            <Route path="/hackathons/:id/tracks" element={<TracksPage />} />
            <Route path="/hackathons/:id/tracks/edit" element={<TracksEditorPage />} />
            <Route path="/tracks" element={<TracksPage />} />
            <Route path="/crawled-data" element={<CrawledDataPage />} />
            <Route path="/hackathons/:id/hacker-dashboard" element={<HackerDashboard />} />
            <Route path="/hackathons/:id/settings" element={<HackathonSettings />} />
            <Route path="/hackathons/:id" element={<HackathonDetailPage />} />
            <Route path="/judge" element={<JudgeRedirect />} />
            <Route path="/auth" element={<AuthPage />} />
          </Route>
        </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
