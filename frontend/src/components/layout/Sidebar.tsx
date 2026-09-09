import { ChevronsLeft, ChevronsRight, LayoutGrid } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { Tooltip } from '@/components/ui';
import { useUiStore } from '@/stores/uiStore';
import { cn } from '@/utils/cn';
import { navGroups } from './nav-config';

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useUiStore();

  return (
    <aside
      className={cn(
        'hidden shrink-0 flex-col border-r border-border bg-surface-raised transition-[width] duration-200 md:flex',
        sidebarCollapsed ? 'w-16' : 'w-60',
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <LayoutGrid
          className="size-5 shrink-0 text-accent"
          aria-hidden="true"
        />
        {!sidebarCollapsed && (
          <span className="truncate text-sm font-semibold text-fg">Neurex</span>
        )}
      </div>

      <nav
        aria-label="Primary"
        className="flex-1 space-y-4 overflow-y-auto p-3"
      >
        {navGroups.map((group, index) => (
          <div key={group.label ?? `group-${index}`}>
            {group.label && !sidebarCollapsed && (
              <p className="px-2 pb-1 text-xs font-medium tracking-wide text-fg-subtle uppercase">
                {group.label}
              </p>
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const link = (
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium transition-colors',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
                        isActive
                          ? 'bg-accent/10 text-accent'
                          : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                        sidebarCollapsed && 'justify-center',
                      )
                    }
                  >
                    <item.icon className="size-4 shrink-0" aria-hidden="true" />
                    {!sidebarCollapsed && (
                      <span className="truncate">{item.label}</span>
                    )}
                  </NavLink>
                );

                return (
                  <li key={item.to}>
                    {sidebarCollapsed ? (
                      <Tooltip content={item.label} side="top">
                        {link}
                      </Tooltip>
                    ) : (
                      link
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <button
        type="button"
        onClick={toggleSidebar}
        aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className="flex h-11 items-center justify-center gap-2 border-t border-border text-sm text-fg-muted transition-colors hover:bg-surface-hover hover:text-fg"
      >
        {sidebarCollapsed ? (
          <ChevronsRight className="size-4" aria-hidden="true" />
        ) : (
          <>
            <ChevronsLeft className="size-4" aria-hidden="true" />
            Collapse
          </>
        )}
      </button>
    </aside>
  );
}
