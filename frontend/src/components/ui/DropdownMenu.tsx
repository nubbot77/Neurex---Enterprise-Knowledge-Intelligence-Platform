import { AnimatePresence, motion } from 'motion/react';
import type { LucideIcon } from 'lucide-react';
import type { ReactElement } from 'react';
import { cloneElement, useEffect, useId, useRef, useState } from 'react';
import { cn } from '@/utils/cn';

export interface DropdownMenuItem {
  label: string;
  icon?: LucideIcon;
  onSelect: () => void;
  destructive?: boolean;
  disabled?: boolean;
}

export type DropdownMenuEntry = DropdownMenuItem | { separator: true };

export interface DropdownMenuProps {
  trigger: ReactElement<{
    onClick?: () => void;
    'aria-haspopup'?: boolean;
    'aria-expanded'?: boolean;
  }>;
  items: DropdownMenuEntry[];
  align?: 'start' | 'end';
}

function isSeparator(entry: DropdownMenuEntry): entry is { separator: true } {
  return 'separator' in entry;
}

export function DropdownMenu({
  trigger,
  items,
  align = 'start',
}: DropdownMenuProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      const enabledRefs = itemRefs.current.filter(
        (el): el is HTMLButtonElement => !!el,
      );
      const currentIndex = enabledRefs.indexOf(
        document.activeElement as HTMLButtonElement,
      );

      if (event.key === 'Escape') {
        setOpen(false);
        containerRef.current?.querySelector('button')?.focus();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        enabledRefs[(currentIndex + 1) % enabledRefs.length]?.focus();
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        enabledRefs[
          (currentIndex - 1 + enabledRefs.length) % enabledRefs.length
        ]?.focus();
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    itemRefs.current[0]?.focus();

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative inline-block">
      {cloneElement(trigger, {
        onClick: () => setOpen((prev) => !prev),
        'aria-haspopup': true,
        'aria-expanded': open,
      })}
      <AnimatePresence>
        {open && (
          <motion.div
            id={menuId}
            role="menu"
            initial={{ opacity: 0, scale: 0.97, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -4 }}
            transition={{ duration: 0.12 }}
            className={cn(
              'absolute z-50 mt-1.5 min-w-40 rounded-md border border-border bg-surface-raised p-1 shadow-lg',
              align === 'end' ? 'right-0' : 'left-0',
            )}
          >
            {items.map((entry, index) => {
              if (isSeparator(entry)) {
                return (
                  <div
                    key={`separator-${index}`}
                    role="separator"
                    className="my-1 h-px bg-border"
                  />
                );
              }

              const Icon = entry.icon;
              return (
                <button
                  key={entry.label}
                  ref={(el) => {
                    itemRefs.current[index] = el;
                  }}
                  role="menuitem"
                  disabled={entry.disabled}
                  onClick={() => {
                    entry.onSelect();
                    setOpen(false);
                  }}
                  className={cn(
                    'flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm transition-colors',
                    'hover:bg-surface-hover focus-visible:bg-surface-hover focus-visible:outline-none',
                    'disabled:pointer-events-none disabled:opacity-50',
                    entry.destructive ? 'text-danger' : 'text-fg',
                  )}
                >
                  {Icon && <Icon className="size-4" aria-hidden="true" />}
                  {entry.label}
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
