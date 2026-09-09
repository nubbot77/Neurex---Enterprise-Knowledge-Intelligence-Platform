import { Monitor, Moon, Sun } from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui';
import { useThemeStore, type Theme } from '@/stores/themeStore';

const options: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

export function AppearanceForm() {
  const { theme, setTheme } = useThemeStore();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>Applies immediately — no save needed.</CardDescription>
      </CardHeader>
      <CardContent className="flex gap-2">
        {options.map(({ value, label, icon: Icon }) => (
          <Button
            key={value}
            type="button"
            variant={theme === value ? 'primary' : 'outline'}
            onClick={() => setTheme(value)}
          >
            <Icon className="size-4" />
            {label}
          </Button>
        ))}
      </CardContent>
    </Card>
  );
}
