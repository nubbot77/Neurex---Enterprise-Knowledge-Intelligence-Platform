import { Outlet } from 'react-router-dom';
import { MobileNavigation } from './MobileNavigation';
import { NavigationProgress } from './NavigationProgress';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export function AppShell() {
  return (
    <div className="relative flex h-screen overflow-hidden bg-surface">
      <NavigationProgress />
      <Sidebar />
      <MobileNavigation />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
