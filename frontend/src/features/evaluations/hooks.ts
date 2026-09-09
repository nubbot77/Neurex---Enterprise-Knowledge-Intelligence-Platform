import { useQuery } from '@tanstack/react-query';
import { evaluationsApi } from './api';

export const evaluationKeys = {
  datasets: ['evaluation-datasets'] as const,
  runs: ['evaluation-runs'] as const,
  run: (id: string) => ['evaluation-runs', id] as const,
};

export function useEvaluationDatasets() {
  return useQuery({
    queryKey: evaluationKeys.datasets,
    queryFn: () => evaluationsApi.listDatasets(),
  });
}

export function useEvaluationRuns() {
  return useQuery({
    queryKey: evaluationKeys.runs,
    queryFn: () => evaluationsApi.listRuns(),
  });
}

export function useEvaluationRun(id: string) {
  return useQuery({
    queryKey: evaluationKeys.run(id),
    queryFn: () => evaluationsApi.getRun(id),
    enabled: Boolean(id),
  });
}
