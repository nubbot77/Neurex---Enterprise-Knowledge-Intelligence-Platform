import { Badge, type BadgeProps } from '@/components/ui';
import type { IngestionStatus } from '../types';

const statusConfig: Record<
  IngestionStatus,
  { label: string; variant: BadgeProps['variant'] }
> = {
  queued: { label: 'Queued', variant: 'default' },
  processing: { label: 'Processing', variant: 'info' },
  completed: { label: 'Completed', variant: 'success' },
  failed: { label: 'Failed', variant: 'danger' },
  retrying: { label: 'Retrying', variant: 'warning' },
};

export function DocumentStatusBadge({ status }: { status: IngestionStatus }) {
  const config = statusConfig[status];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
