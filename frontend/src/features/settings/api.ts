import { apiClient } from '@/services/api/client';
import type { SettingsBundle, SettingsSection } from './types';

export const settingsApi = {
  get: () => apiClient.get<SettingsBundle>('/settings'),

  update: <K extends SettingsSection>(
    section: K,
    data: Partial<SettingsBundle[K]>,
  ) => apiClient.patch<SettingsBundle[K]>(`/settings/${section}`, data),
};
