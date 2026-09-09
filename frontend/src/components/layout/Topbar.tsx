import { Menu } from 'lucide-react';
import { Button } from '@/components/ui';
import { useUiStore } from '@/stores/uiStore';
import { Breadcrumbs, type BreadcrumbItem } from './Breadcrumbs';
import { ThemeToggle } from './ThemeToggle';
import { UserMenu } from './UserMenu';

export interface TopbarProps {
  breadcrumbs?: BreadcrumbItem[];
}

export function Topbar({ breadcrumbs }: TopbarProps) {
  const { openMobileNav } = useUiStore();

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface px-4">
      <Button
        variant="ghost"
        size="icon"
        aria-label="Open navigation"
        className="md:hidden"
        onClick={openMobileNav}
      >
        <Menu className="size-4" />
      </Button>

      <Breadcrumbs items={breadcrumbs} />

      <div className="ml-auto flex items-center gap-1.5">
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
