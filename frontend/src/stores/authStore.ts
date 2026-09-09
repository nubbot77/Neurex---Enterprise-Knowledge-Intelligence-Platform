import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '@/services/api/client';
import type { User } from '@/features/authentication/types';

export type AuthStatus = 'idle' | 'authenticated' | 'unauthenticated';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  status: AuthStatus;
  setSession: (user: User, accessToken: string) => void;
  clearSession: () => void;
  setStatus: (status: AuthStatus) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      status: 'idle',
      setSession: (user, accessToken) => {
        set({ user, accessToken, status: 'authenticated' });
      },
      clearSession: () => {
        set({ user: null, accessToken: null, status: 'unauthenticated' });
      },
      setStatus: (status) => {
        set({ status });
      },
    }),
    {
      name: 'auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
      }),
    },
  ),
);

apiClient.setAuthTokenProvider(() => useAuthStore.getState().accessToken);

// Dev-only escape hatch for local UI work without a backend — stripped from prod
// builds since it's behind import.meta.env.DEV. In devtools:
//   __authStore.getState().setSession({ id: '1', name: 'Dev User', email: 'dev@neurex.dev' }, 'dev-token')
if (import.meta.env.DEV) {
  (window as unknown as { __authStore: typeof useAuthStore }).__authStore = useAuthStore;
}
