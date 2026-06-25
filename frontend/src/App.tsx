import { Link, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Grain } from "./components/Grain";
import { Scanlines } from "./components/Scanlines";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { RunComparisonPage } from "./pages/RunComparisonPage";
import { MetricsPage } from "./pages/MetricsPage";
import { ResearchExportPage } from "./pages/ResearchExportPage";
import { AnalysisPage } from "./pages/AnalysisPage";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return isActive ? "nav-link nav-link-active" : "nav-link";
}

function TopNav() {
  const { isAuthenticated, logout, userEmail } = useAuth();
  return (
    <header className="topnav">
      <Link className="brand-title" to="/">ForensicX</Link>
      {isAuthenticated ? (
        <nav className="row nav-actions">
          <NavLink className={navLinkClass} to="/dashboard">Dashboard</NavLink>
          <NavLink className={navLinkClass} to="/experiments">Experiments</NavLink>
          <span className="user-chip">{userEmail}</span>
          <button className="nav-link" onClick={() => void logout()}>Logout</button>
        </nav>
      ) : (
        <nav className="row nav-actions">
          <Link className="nav-link nav-link-cta" to="/login">Launch Application</Link>
        </nav>
      )}
    </header>
  );
}

function Protected({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div className="loading-spinner">Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <>
      <Grain />
      <Scanlines />
      <TopNav />
      <main className="container app-shell">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<Protected><DashboardPage /></Protected>} />
          <Route path="/cases/:caseId" element={<Protected><CaseDetailPage /></Protected>} />
          <Route path="/cases/:caseId/run" element={<Protected><RunComparisonPage /></Protected>} />
          <Route path="/runs/:runId/metrics" element={<Protected><MetricsPage /></Protected>} />
          <Route path="/cases/:caseId/analysis" element={<Protected><AnalysisPage /></Protected>} />
          <Route path="/experiments" element={<Protected><ResearchExportPage /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ErrorBoundary>
        <AppRoutes />
      </ErrorBoundary>
    </AuthProvider>
  );
}
