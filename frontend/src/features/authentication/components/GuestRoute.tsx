import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { FullscreenLoader } from '@/components/layout/FullscreenLoader';
import { useAuthStore } from '@/stores/authStore';

/** Opposite of ProtectedRoute: keeps an already-signed-in user off /login, /register, etc. */
export function GuestRoute({ children }: { children: ReactNode }) {
  const status = useAuthStore((state) => state.status);

  if (status === 'idle') return <FullscreenLoader />;
  if (status === 'authenticated') return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}
