import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import AnalyzePage from './pages/AnalyzePage';
import ReportPage from './pages/ReportPage';
import Dashboard from './pages/Dashboard';
import HackathonSetup from './pages/HackathonSetup';
import AuthPage from './pages/AuthPage';
import RegisterPage from './pages/RegisterPage';
import RegistrationsPage from './pages/RegistrationsPage';
import RegistrationDetailPage from './pages/RegistrationDetailPage';
import OrganizerRegistrationsPage from './pages/OrganizerRegistrationsPage';
import CheckInPage from './pages/CheckInPage';
import RubricBuilderPage from './pages/RubricBuilderPage';
import JudgePortal from './pages/JudgePortal';
import JudgingResultsPage from './pages/JudgingResultsPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<AnalyzePage />} />
            <Route path="/report/:id" element={<ReportPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/hackathons" element={<HackathonSetup />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/hackathons/:id/register" element={<RegisterPage />} />
            <Route path="/registrations" element={<RegistrationsPage />} />
            <Route path="/registrations/:id" element={<RegistrationDetailPage />} />
            <Route path="/hackathons/:id/registrations" element={<OrganizerRegistrationsPage />} />
            <Route path="/check-in" element={<CheckInPage />} />
            <Route path="/hackathons/:id/judging/setup" element={<RubricBuilderPage />} />
            <Route path="/hackathons/:id/judging" element={<JudgePortal />} />
            <Route path="/hackathons/:id/judging/results" element={<JudgingResultsPage />} />
            <Route path="/auth" element={<AuthPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
