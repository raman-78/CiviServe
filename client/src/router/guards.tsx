import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { LoadingState } from "@/components/shared/LoadingState";
import { useAuth } from "@/features/auth/AuthContext";

/** Full-viewport loading state shown while auth/profile state resolves. */
function AuthLoading() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <LoadingState />
    </div>
  );
}

/** Redirects to /login when unauthenticated (docs/architecture/08). */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, initializing } = useAuth();
  const location = useLocation();

  if (initializing) return <AuthLoading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <>{children}</>;
}

/** Blocks eligibility screens until the profile exists (redirects to setup). */
export function RequireProfile({ children }: { children: ReactNode }) {
  const { user, initializing, completion, profileLoading } = useAuth();
  const location = useLocation();

  if (initializing) return <AuthLoading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (profileLoading) return <AuthLoading />;
  if (!completion?.isComplete) {
    return <Navigate to="/profile/setup" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}

/** For the setup flow only: bounces users with a complete profile to /profile. */
export function RequireIncompleteProfile({ children }: { children: ReactNode }) {
  const { user, initializing, completion, profileLoading } = useAuth();

  if (initializing) return <AuthLoading />;
  if (!user) return <Navigate to="/login" replace />;
  if (profileLoading) return <AuthLoading />;
  if (completion?.isComplete) return <Navigate to="/profile" replace />;
  return <>{children}</>;
}

/** Blocks a route unless the signed-in account holds one of `roles` (e.g. admin). */
export function RequireRole({ roles, children }: { roles: string[]; children: ReactNode }) {
  const { user, me, initializing } = useAuth();
  const location = useLocation();

  if (initializing) return <AuthLoading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!me || !roles.includes(me.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}
