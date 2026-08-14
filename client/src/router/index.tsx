import { lazy, type ComponentType } from "react";
import { createBrowserRouter } from "react-router-dom";
import { PublicLayout } from "@/components/layouts/PublicLayout";
import { AuthLayout } from "@/components/layouts/AuthLayout";
import { AppLayout } from "@/components/layouts/AppLayout";
import { RequireAuth, RequireIncompleteProfile, RequireRole } from "@/router/guards";
import { ErrorElement } from "@/router/ErrorElement";

const load = <T,>(importer: () => Promise<T>, pick: (mod: T) => ComponentType) =>
  lazy(() => importer().then((mod) => ({ default: pick(mod) })));

const LandingPage = load(() => import("@/pages/LandingPage"), (m) => m.LandingPage);
const LoginPage = load(() => import("@/pages/LoginPage"), (m) => m.LoginPage);
const RegisterPage = load(() => import("@/pages/RegisterPage"), (m) => m.RegisterPage);
const ForgotPasswordPage = load(() => import("@/pages/ForgotPasswordPage"), (m) => m.ForgotPasswordPage);
const VerifyEmailPage = load(() => import("@/pages/VerifyEmailPage"), (m) => m.VerifyEmailPage);
const ChatPage = load(() => import("@/pages/ChatPage"), (m) => m.ChatPage);
const SchemesPage = load(() => import("@/pages/SchemesPage"), (m) => m.SchemesPage);
const SchemeDetailPage = load(() => import("@/pages/SchemeDetailPage"), (m) => m.SchemeDetailPage);
const CentersPage = load(() => import("@/pages/CentersPage"), (m) => m.CentersPage);
const DocumentsPage = load(() => import("@/pages/DocumentsPage"), (m) => m.DocumentsPage);
const EligibilityPage = load(
  () => import("@/features/eligibility/EligibilityPage"),
  (m) => m.EligibilityPage,
);
const ProfilePage = load(() => import("@/pages/ProfilePage"), (m) => m.ProfilePage);
const EditProfilePage = load(() => import("@/pages/EditProfilePage"), (m) => m.EditProfilePage);
const ProfileSetupPage = load(() => import("@/pages/ProfileSetupPage"), (m) => m.ProfileSetupPage);
const SettingsPage = load(() => import("@/pages/SettingsPage"), (m) => m.SettingsPage);
const HelpPage = load(() => import("@/pages/HelpPage"), (m) => m.HelpPage);
const NotFoundPage = load(() => import("@/pages/NotFoundPage"), (m) => m.NotFoundPage);
const AdminDashboardPage = load(
  () => import("@/features/admin/AdminDashboardPage"),
  (m) => m.AdminDashboardPage,
);

/**
 * Lazy route table (docs/architecture/08). Each page is its own chunk;
 * the AppLayout wraps them in Suspense. Account-scoped routes are behind
 * `RequireAuth`; the setup flow is guarded by `RequireIncompleteProfile`.
 */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <PublicLayout />,
    errorElement: <ErrorElement />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    path: "/login",
    element: <AuthLayout />,
    errorElement: <ErrorElement />,
    children: [{ index: true, element: <LoginPage /> }],
  },
  {
    path: "/register",
    element: <AuthLayout />,
    errorElement: <ErrorElement />,
    children: [{ index: true, element: <RegisterPage /> }],
  },
  {
    path: "/forgot-password",
    element: <AuthLayout />,
    errorElement: <ErrorElement />,
    children: [{ index: true, element: <ForgotPasswordPage /> }],
  },
  {
    path: "/verify-email",
    element: <AuthLayout />,
    errorElement: <ErrorElement />,
    children: [
      {
        index: true,
        element: (
          <RequireAuth>
            <VerifyEmailPage />
          </RequireAuth>
        ),
      },
    ],
  },
  {
    element: <AppLayout />,
    errorElement: <ErrorElement />,
    children: [
      { path: "/chat", element: <ChatPage /> },
      { path: "/chat/:sessionId", element: <ChatPage /> },
      { path: "/schemes", element: <SchemesPage /> },
      { path: "/schemes/:code", element: <SchemeDetailPage /> },
      { path: "/centers", element: <CentersPage /> },
      { path: "/help", element: <HelpPage /> },
      {
        path: "/eligibility",
        element: (
          <RequireAuth>
            <EligibilityPage />
          </RequireAuth>
        ),
      },
      {
        path: "/documents",
        element: (
          <RequireAuth>
            <DocumentsPage />
          </RequireAuth>
        ),
      },
      {
        path: "/profile",
        element: (
          <RequireAuth>
            <ProfilePage />
          </RequireAuth>
        ),
      },
      {
        path: "/profile/edit",
        element: (
          <RequireAuth>
            <EditProfilePage />
          </RequireAuth>
        ),
      },
      {
        path: "/profile/setup",
        element: (
          <RequireIncompleteProfile>
            <ProfileSetupPage />
          </RequireIncompleteProfile>
        ),
      },
      {
        path: "/settings",
        element: (
          <RequireAuth>
            <SettingsPage />
          </RequireAuth>
        ),
      },
      {
        path: "/admin",
        element: (
          <RequireRole roles={["admin"]}>
            <AdminDashboardPage />
          </RequireRole>
        ),
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
