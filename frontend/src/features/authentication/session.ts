import { useAuthStore } from '@/stores/authStore';
import { authApi } from './api';

let initialized = false;

/**
 * Resolves whether the persisted access token (if any) is still valid.
 * Call once at app startup; safe to call more than once (idempotent after the first run).
 */
export async function initializeSession(): Promise<void> {
  if (initialized) return;
  initialized = true;

  const { accessToken } = useAuthStore.getState();
  if (!accessToken) {
    useAuthStore.getState().setStatus('unauthenticated');
    return;
  }

  try {
    const user = await authApi.getCurrentUser();
    useAuthStore.getState().setSession(user, accessToken);
  } catch {
    useAuthStore.getState().clearSession();
  }
}
