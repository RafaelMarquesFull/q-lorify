import { lazy, Suspense } from "react"
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { useAuthStore } from "@/store/auth"
import { GoogleOAuthProvider } from "@react-oauth/google"

// Layouts loaded eagerly (always needed)
import DashboardLayout from "@/layouts/DashboardLayout"
import AdminLayout from "@/layouts/AdminLayout"

// Pages loaded lazily (on demand)
const LandingPage = lazy(() => import("@/pages/LandingPage"))
const LoginPage = lazy(() => import("@/pages/LoginPage"))
const RegisterPage = lazy(() => import("@/pages/RegisterPage"))
const ForgotPasswordPage = lazy(() => import("@/pages/ForgotPasswordPage"))
const ResetPasswordPage = lazy(() => import("@/pages/ResetPasswordPage"))
const VerifyEmailPage = lazy(() => import("@/pages/VerifyEmailPage"))

// Dashboard pages
const DashboardOverview = lazy(() => import("@/pages/dashboard/Overview"))
const Playground = lazy(() => import("@/pages/dashboard/Playground"))
const BillingPage = lazy(() => import("@/pages/dashboard/BillingPage"))
const UserFunctionsPage = lazy(() => import("@/pages/dashboard/UserFunctionsPage"))
const ClientModelsPage = lazy(() => import("@/pages/dashboard/ModelsPage"))
const SettingsPage = lazy(() => import("@/pages/dashboard/SettingsPage"))
const ApiKeysPage = lazy(() => import("@/pages/dashboard/ApiKeysPage"))
const AnalyticsPage = lazy(() => import("@/pages/dashboard/AnalyticsPage"))

// Admin pages
const AdminOverview = lazy(() => import("@/pages/admin/AdminOverview"))
const ProvidersPage = lazy(() => import("@/pages/admin/ProvidersPage"))
const ModelsPage = lazy(() => import("@/pages/admin/ModelsPage"))
const UsersPage = lazy(() => import("@/pages/admin/UsersPage"))
const OrchestratorFunctionsPage = lazy(() => import("@/pages/admin/OrchestratorFunctionsPage"))
const OrchestratorClientsPage = lazy(() => import("@/pages/admin/OrchestratorClientsPage"))
const AdminSentimentPage = lazy(() => import("@/pages/admin/AdminSentimentPage"))

// Loading fallback
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-full min-h-[200px]">
      <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((state) => state.token)
  const isAuthenticated = !!token
  return isAuthenticated ? children : <Navigate to="/login" />
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((state) => state.user)
  const token = useAuthStore((state) => state.token)

  const isAuthenticated = !!token
  const isAdmin = user?.role === 'ADMIN'

  if (!isAuthenticated) return <Navigate to="/login" />
  if (!isAdmin) return <Navigate to="/dashboard" />

  return children
}

function App() {
  const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ""

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />

            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Suspense fallback={<PageLoader />}>
                    <Outlet />
                  </Suspense>
                </DashboardLayout>
              </ProtectedRoute>
            }>
              <Route index element={<DashboardOverview />} />
              <Route path="playground" element={<Playground />} />
              <Route path="analytics" element={<AnalyticsPage />} />
              <Route path="functions" element={<UserFunctionsPage />} />
              <Route path="keys" element={<ApiKeysPage />} />
              <Route path="billing" element={<BillingPage />} />
              <Route path="models" element={<ClientModelsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            <Route path="/admin" element={
              <AdminRoute>
                <AdminLayout>
                  <Suspense fallback={<PageLoader />}>
                    <Outlet />
                  </Suspense>
                </AdminLayout>
              </AdminRoute>
            }>
              <Route index element={<AdminOverview />} />
              <Route path="providers" element={<ProvidersPage />} />
              <Route path="models" element={<ModelsPage />} />
              <Route path="users" element={<UsersPage />} />
              <Route path="orchestrator/functions" element={<OrchestratorFunctionsPage />} />
              <Route path="orchestrator/clients" element={<OrchestratorClientsPage />} />
              <Route path="sentiment" element={<AdminSentimentPage />} />
              <Route path="settings" element={<div className="p-8 text-white"><h1>Settings (WIP)</h1></div>} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
      <Toaster />
    </GoogleOAuthProvider>
  )
}

export default App
