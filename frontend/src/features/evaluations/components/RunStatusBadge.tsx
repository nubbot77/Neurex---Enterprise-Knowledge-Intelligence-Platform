import { Badge, type BadgeProps } from '@/components/ui';
import type { EvaluationRunStatus } from '../types';

const config: Record<
  EvaluationRunStatus,
  { label: string; variant: BadgeProps['variant'] }
> = {
  queued: { label: 'Queued', variant: 'default' },
  running: { label: 'Running', variant: 'info' },
  completed: { label: 'Completed', variant: 'success' },
  failed: { label: 'Failed', variant: 'danger' },
};

export function RunStatusBadge({ status }: { status: EvaluationRunStatus }) {
  const { label, variant } = config[status];
  return <Badge variant={variant}>{label}</Badge>;
}
