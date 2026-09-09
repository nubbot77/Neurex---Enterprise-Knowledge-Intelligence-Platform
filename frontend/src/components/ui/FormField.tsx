import type { ReactNode } from 'react';
import { useId } from 'react';
import { cn } from '@/utils/cn';

export interface FormFieldProps {
  label: string;
  error?: string;
  className?: string;
  children: (fieldProps: {
    id: string;
    invalid: boolean;
    'aria-describedby'?: string;
  }) => ReactNode;
}

/** Labels + wires aria-describedby/invalid for a single form control; error text renders below it. */
export function FormField({
  label,
  error,
  className,
  children,
}: FormFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;

  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="text-sm font-medium text-fg">
        {label}
      </label>
      {children({
        id,
        invalid: Boolean(error),
        'aria-describedby': error ? errorId : undefined,
      })}
      {error && (
        <p id={errorId} role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
