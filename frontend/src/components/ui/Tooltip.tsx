import { AnimatePresence, motion } from 'motion/react';
import type { ReactElement, ReactNode } from 'react';
import { cloneElement, useId, useState } from 'react';
import { cn } from '@/utils/cn';

export interface TooltipProps {
  content: ReactNode;
  children: ReactElement<{
    'aria-describedby'?: string;
    onFocus?: () => void;
    onBlur?: () => void;
    onMouseEnter?: () => void;
    onMouseLeave?: () => void;
  }>;
  side?: 'top' | 'bottom';
  className?: string;
}

/** Hover/focus-triggered tooltip. Positioned relative to its trigger; no collision detection. */
export function Tooltip({
  content,
  children,
  side = 'top',
  className,
}: TooltipProps) {
  const [open, setOpen] = useState(false);
  const id = useId();

  const show = () => setOpen(true);
  const hide = () => setOpen(false);

  return (
    <span className="relative inline-flex">
      {cloneElement(children, {
        'aria-describedby': open ? id : undefined,
        onFocus: show,
        onBlur: hide,
        onMouseEnter: show,
        onMouseLeave: hide,
      })}
      <AnimatePresence>
        {open && (
          <motion.span
            role="tooltip"
            id={id}
            initial={{ opacity: 0, y: side === 'top' ? 4 : -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: side === 'top' ? 4 : -4 }}
            transition={{ duration: 0.12 }}
            className={cn(
              'pointer-events-none absolute left-1/2 z-50 -translate-x-1/2 rounded-md bg-fg px-2 py-1 text-xs text-nowrap text-surface',
              side === 'top' ? 'bottom-full mb-1.5' : 'top-full mt-1.5',
              className,
            )}
          >
            {content}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}
