import { Dialog } from '@/components/ui';
import type { EvaluationRun } from '../types';
import { MetricsGrid } from './MetricsGrid';
import { RunStatusBadge } from './RunStatusBadge';

export interface RunDetailDialogProps {
  run: EvaluationRun | null;
  onOpenChange: (open: boolean) => void;
}

export function RunDetailDialog({ run, onOpenChange }: RunDetailDialogProps) {
  return (
    <Dialog
      open={Boolean(run)}
      onOpenChange={onOpenChange}
      title={run ? run.datasetName : 'Run detail'}
    >
      {run && (
        <div className="space-y-3">
          <RunStatusBadge status={run.status} />
          <MetricsGrid metrics={run.metrics} />
        </div>
      )}
    </Dialog>
  );
}
