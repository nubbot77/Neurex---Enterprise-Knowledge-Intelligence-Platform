import { LayoutGrid } from 'lucide-react';
import { Outlet } from 'react-router-dom';

/** Full-page layout for /login, /register, /forgot-password — intentionally has no Sidebar/Topbar. */
export function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-surface p-4">
      <div className="flex items-center gap-2">
        <LayoutGrid className="size-6 text-accent" aria-hidden="true" />
        <span className="text-lg font-semibold text-fg">Neurex</span>
      </div>
      <div className="w-full max-w-sm">
        <Outlet />
      </div>
    </div>
  );
}
