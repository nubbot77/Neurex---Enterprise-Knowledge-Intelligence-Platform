import { EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { DatasetsTable } from '@/features/evaluations/components';
import { useEvaluationDatasets } from '@/features/evaluations/hooks';
import { toUserMessage } from '@/services/api/errors';

export function EvaluationDatasetsPage() {
  const { data, isLoading, isError, error, refetch } = useEvaluationDatasets();

  return (
    <div className="space-y-4 p-6">
      <div>
        <h1 className="text-xl font-semibold text-fg">Evaluation datasets</h1>
        <p className="text-sm text-fg-muted">
          The question/answer sets used to score retrieval and generation.
        </p>
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
          title="No datasets yet"
          description="Datasets you create for evaluation runs will show up here."
        />
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <DatasetsTable datasets={data.items} />
      )}
    </div>
  );
}
