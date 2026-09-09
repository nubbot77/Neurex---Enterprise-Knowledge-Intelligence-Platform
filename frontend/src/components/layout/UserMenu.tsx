import { LogOut, Settings, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { DropdownMenu } from '@/components/ui';
import { useLogout } from '@/features/authentication/hooks';
import { useAuthStore } from '@/stores/authStore';

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : '';
  return (first + last).toUpperCase();
}

export function UserMenu() {
  const user = useAuthStore((state) => state.user);
  const logout = useLogout();
  const navigate = useNavigate();

  if (!user) return null;

  return (
    <DropdownMenu
      align="end"
      trigger={
        <button
          type="button"
          aria-label={`Account menu for ${user.name} (${user.email})`}
          className="flex size-8 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
        >
          {initials(user.name)}
        </button>
      }
      items={[
        {
          label: 'Settings',
          icon: Settings,
          onSelect: () => {
            void navigate('/settings');
          },
        },
        {
          label: 'View profile',
          icon: User,
          onSelect: () => {
            void navigate('/settings');
          },
        },
        { separator: true },
        {
          label: 'Log out',
          icon: LogOut,
          destructive: true,
          onSelect: () => {
            void logout.mutateAsync().finally(() => {
              void navigate('/login');
            });
          },
        },
      ]}
    />
  );
}
