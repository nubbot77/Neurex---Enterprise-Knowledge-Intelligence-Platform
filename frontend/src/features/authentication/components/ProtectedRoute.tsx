import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { FullscreenLoader } from '@/components/layout/FullscreenLoader';
import { useAuthStore } from '@/stores/authStore';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const status = useAuthStore((state) => state.status);
  const location = useLocation();

  if (status === 'idle') return <FullscreenLoader />;
  if (status === 'unauthenticated') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <>{children}</>;
}
