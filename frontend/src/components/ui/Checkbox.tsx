import type { InputHTMLAttributes } from 'react';
import { forwardRef, useId } from 'react';
import { cn } from '@/utils/cn';

export interface CheckboxProps extends Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'type'
> {
  label?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id ?? generatedId;

    const input = (
      <input
        ref={ref}
        id={inputId}
        type="checkbox"
        className={cn(
          'size-4 shrink-0 rounded-sm border border-border-strong bg-surface accent-[var(--color-accent)]',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        {...props}
      />
    );

    if (!label) {
      return input;
    }

    return (
      <label
        htmlFor={inputId}
        className="inline-flex select-none items-center gap-2 text-sm text-fg"
      >
        {input}
        {label}
      </label>
    );
  },
);
Checkbox.displayName = 'Checkbox';
