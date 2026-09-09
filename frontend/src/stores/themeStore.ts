import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'system',
      setTheme: (theme) => {
        set({ theme });
      },
    }),
    { name: 'theme' },
  ),
);

function resolveIsDark(theme: Theme): boolean {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  return theme === 'dark';
}

/** Applies the `.dark` class to <html> for the current theme, and keeps it in sync. */
export function applyThemeClass(): () => void {
  const apply = () => {
    document.documentElement.classList.toggle(
      'dark',
      resolveIsDark(useThemeStore.getState().theme),
    );
  };

  apply();

  const unsubscribeStore = useThemeStore.subscribe(apply);

  const media = window.matchMedia('(prefers-color-scheme: dark)');
  media.addEventListener('change', apply);

  return () => {
    unsubscribeStore();
    media.removeEventListener('change', apply);
  };
}
