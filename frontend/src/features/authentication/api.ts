import { apiClient } from '@/services/api/client';
import type {
  AuthResponse,
  ForgotPasswordRequest,
  LoginRequest,
  RegisterRequest,
  ResetPasswordRequest,
  User,
} from './types';

// Backend contract assumed pending the FastAPI auth router; adjust paths once it lands.
export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<AuthResponse>('/auth/login', data, { skipAuth: true }),

  register: (data: RegisterRequest) =>
    apiClient.post<AuthResponse>('/auth/register', data, { skipAuth: true }),

  forgotPassword: (data: ForgotPasswordRequest) =>
    apiClient.post<void>('/auth/forgot-password', data, { skipAuth: true }),

  resetPassword: (data: ResetPasswordRequest) =>
    apiClient.post<void>('/auth/reset-password', data, { skipAuth: true }),

  logout: () => apiClient.post<void>('/auth/logout'),

  getCurrentUser: () => apiClient.get<User>('/auth/me'),
};
