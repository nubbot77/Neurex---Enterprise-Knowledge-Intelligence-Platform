import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ingestionApi } from './api';
import type { IngestionJob, IngestionJobListParams } from './types';

const ACTIVE_STATUSES: IngestionJob['status'][] = [
  'queued',
  'processing',
  'retrying',
];

export const ingestionKeys = {
  all: ['ingestion-jobs'] as const,
  lists: () => [...ingestionKeys.all, 'list'] as const,
  list: (params: IngestionJobListParams) =>
    [...ingestionKeys.lists(), params] as const,
  logs: (jobId: string) => [...ingestionKeys.all, 'logs', jobId] as const,
};

export function useIngestionJobs(params: IngestionJobListParams) {
  return useQuery({
    queryKey: ingestionKeys.list(params),
    queryFn: () => ingestionApi.list(params),
    // Poll only while something is actually in flight — no point hammering the API
    // once every job has settled into completed/failed.
    refetchInterval: (query) => {
      const hasActiveJob = query.state.data?.items.some((job) =>
        ACTIVE_STATUSES.includes(job.status),
      );
      return hasActiveJob ? 4000 : false;
    },
  });
}

export function useIngestionJobLogs(jobId: string, enabled: boolean) {
  return useQuery({
    queryKey: ingestionKeys.logs(jobId),
    queryFn: () => ingestionApi.logs(jobId),
    enabled: enabled && Boolean(jobId),
  });
}

export function useRetryIngestionJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => ingestionApi.retry(jobId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ingestionKeys.lists() });
    },
  });
}
