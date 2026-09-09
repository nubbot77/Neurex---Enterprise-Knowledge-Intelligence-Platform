import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from './api';
import type { SettingsBundle, SettingsSection } from './types';

export const settingsKeys = {
  all: ['settings'] as const,
};

export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.all,
    queryFn: () => settingsApi.get(),
  });
}

export function useUpdateSettingsSection<K extends SettingsSection>(
  section: K,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<SettingsBundle[K]>) =>
      settingsApi.update(section, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: settingsKeys.all });
    },
  });
}
