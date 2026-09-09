import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  buttonVariants,
  EmptyState,
  ErrorState,
  Skeleton,
} from '@/components/ui';
import { RunDetailDialog, RunsTable } from '@/features/evaluations/components';
import { useEvaluationRuns } from '@/features/evaluations/hooks';
import type { EvaluationRun } from '@/features/evaluations/types';
import { toUserMessage } from '@/services/api/errors';

export function EvaluationsPage() {
  const { data, isLoading, isError, error, refetch } = useEvaluationRuns();
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-fg">Evaluations</h1>
          <p className="text-sm text-fg-muted">
            Retrieval, generation, and citation metrics across evaluation runs.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/evaluations/datasets"
            className={buttonVariants({ variant: 'outline' })}
          >
            Datasets
          </Link>
          <Link
            to="/evaluations/runs"
            className={buttonVariants({ variant: 'outline' })}
          >
            All runs
          </Link>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <ErrorState
          description={toUserMessage(error)}
          onRetry={() => void refetch()}
        />
      )}

      {!isLoading && !isError && data?.items.length === 0 && (
        <EmptyState
          title="No evaluation runs yet"
          description="Create a dataset and run an evaluation to see metrics here."
        />
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <RunsTable
          runs={data.items.slice(0, 10)}
          onSelectRun={setSelectedRun}
        />
      )}

      <RunDetailDialog
        run={selectedRun}
        onOpenChange={(open) => !open && setSelectedRun(null)}
      />
    </div>
  );
}
