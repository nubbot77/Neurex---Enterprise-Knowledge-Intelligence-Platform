import { AnimatePresence, motion } from 'motion/react';
import { LayoutGrid, X } from 'lucide-react';
import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { NavLink } from 'react-router-dom';
import { useUiStore } from '@/stores/uiStore';
import { cn } from '@/utils/cn';
import { navGroups } from './nav-config';

export function MobileNavigation() {
  const { mobileNavOpen, closeMobileNav } = useUiStore();

  useEffect(() => {
    if (!mobileNavOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeMobileNav();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [mobileNavOpen, closeMobileNav]);

  return createPortal(
    <AnimatePresence>
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-black/40"
            onClick={closeMobileNav}
            aria-hidden="true"
          />
          <motion.nav
            aria-label="Primary"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="relative flex h-full w-72 flex-col bg-surface-raised shadow-xl"
          >
            <div className="flex h-14 items-center justify-between border-b border-border px-4">
              <span className="flex items-center gap-2 text-sm font-semibold text-fg">
                <LayoutGrid className="size-5 text-accent" aria-hidden="true" />
                Neurex
              </span>
              <button
                type="button"
                onClick={closeMobileNav}
                aria-label="Close navigation"
                className="rounded-md p-1.5 text-fg-muted hover:bg-surface-hover"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto p-3">
              {navGroups.map((group, index) => (
                <div key={group.label ?? `group-${index}`}>
                  {group.label && (
                    <p className="px-2 pb-1 text-xs font-medium tracking-wide text-fg-subtle uppercase">
                      {group.label}
                    </p>
                  )}
                  <ul className="space-y-0.5">
                    {group.items.map((item) => (
                      <li key={item.to}>
                        <NavLink
                          to={item.to}
                          onClick={closeMobileNav}
                          className={({ isActive }) =>
                            cn(
                              'flex items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium transition-colors',
                              isActive
                                ? 'bg-accent/10 text-accent'
                                : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                            )
                          }
                        >
                          <item.icon
                            className="size-4 shrink-0"
                            aria-hidden="true"
                          />
                          <span className="truncate">{item.label}</span>
                        </NavLink>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </motion.nav>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
