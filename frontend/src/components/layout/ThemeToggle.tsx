import { Monitor, Moon, Sun } from 'lucide-react';
import { Button, DropdownMenu } from '@/components/ui';
import { useThemeStore, type Theme } from '@/stores/themeStore';

const themeIcons: Record<Theme, typeof Sun> = {
  light: Sun,
  dark: Moon,
  system: Monitor,
};

export function ThemeToggle() {
  const { theme, setTheme } = useThemeStore();
  const Icon = themeIcons[theme];

  return (
    <DropdownMenu
      align="end"
      trigger={
        <Button variant="ghost" size="icon" aria-label="Change theme">
          <Icon className="size-4" aria-hidden="true" />
        </Button>
      }
      items={[
        { label: 'Light', icon: Sun, onSelect: () => setTheme('light') },
        { label: 'Dark', icon: Moon, onSelect: () => setTheme('dark') },
        { label: 'System', icon: Monitor, onSelect: () => setTheme('system') },
      ]}
    />
  );
}
