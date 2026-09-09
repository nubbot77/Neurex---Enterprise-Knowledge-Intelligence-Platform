import type { HTMLAttributes } from 'react';
import { cn } from '@/utils/cn';

export function Skeleton({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-surface-hover', className)}
      aria-hidden="true"
      {...props}
    />
  );
}
