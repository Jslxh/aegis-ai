import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout.jsx";
import { ProtectedRoute } from "./components/layout/ProtectedRoute.jsx";
import { ErrorBoundary } from "./components/shared/ErrorBoundary.jsx";
import { PageLoading } from "./components/shared/LoadingSkeleton.jsx";
import Login from "./pages/Login.jsx";

const Dashboard = lazy(() => import("./pages/Dashboard.jsx"));
const Policies = lazy(() => import("./pages/Policies.jsx"));
const Approvals = lazy(() => import("./pages/Approvals.jsx"));
// const RuntimeMonitor = lazy(() => import("./pages/RuntimeMonitor.jsx"));
const AuditCenter = lazy(() => import("./pages/AuditCenter.jsx"));
const Simulation = lazy(() => import("./pages/Simulation.jsx"));
const Analytics = lazy(() => import("./pages/Analytics.jsx"));
// const Architecture = lazy(() => import("./pages/Architecture.jsx"));
const AIExplainability = lazy(() => import("./pages/AIExplainability.jsx"));
const Chatbot = lazy(() => import("./pages/Chatbot.jsx"));
const Settings = lazy(() => import("./pages/Settings.jsx"));
const ResetPassword = lazy(() => import("./pages/ResetPassword.jsx"));

export default function App() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoading />}>
        <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        <Route element={<ProtectedRoute requiredRole="viewer" />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/policies" element={<Policies />} />
            <Route path="/approvals" element={<Approvals />} />
            {/* <Route path="/runtime" element={<RuntimeMonitor />} /> */}
            <Route path="/audit" element={<AuditCenter />} />
            <Route path="/simulation" element={<Simulation />} />
            <Route path="/analytics" element={<Analytics />} />
            {/* <Route path="/architecture" element={<Architecture />} /> */}
            <Route path="/ai" element={<AIExplainability />} />
            <Route path="/chat" element={<Chatbot />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}
