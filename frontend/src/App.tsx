import { Link, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Grain } from "./components/Grain";
import { Scanlines } from "./components/Scanlines";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { RunComparisonPage } from "./pages/RunComparisonPage";
import { MetricsPage } from "./pages/MetricsPage";
import { ResearchExportPage } from "./pages/ResearchExportPage";
import { AnalysisPage } from "./pages/AnalysisPage";

function TopNav() {
  const { isAuthenticated, logout } = useAuth();
  return (
    <header className="topnav">
      <h1 className="brand-title">Forensic Enhancement Assistant</h1>
      {isAuthenticated ? (
        <nav className="row nav-actions">
          <Link className="nav-link" to="/">Dashboard</Link>
          <Link className="nav-link" to="/experiments">Experiments</Link>
          <button className="nav-link" onClick={() => void logout()}>Logout</button>
        </nav>
      ) : null}
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
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Protected><DashboardPage /></Protected>} />
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
