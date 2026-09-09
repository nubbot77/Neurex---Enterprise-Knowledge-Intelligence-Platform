import { apiClient } from '@/services/api/client';
import type { PaginatedResponse } from '@/types/api';
import type {
  IngestionJob,
  IngestionJobListParams,
  IngestionLogEntry,
} from './types';

export const ingestionApi = {
  list: (params: IngestionJobListParams = {}) =>
    apiClient.get<PaginatedResponse<IngestionJob>>('/ingestion/jobs', {
      params: {
        page: params.page,
        pageSize: params.pageSize,
        status: params.status,
      },
    }),

  logs: (jobId: string) =>
    apiClient.get<IngestionLogEntry[]>(`/ingestion/jobs/${jobId}/logs`),

  retry: (jobId: string) =>
    apiClient.post<IngestionJob>(`/ingestion/jobs/${jobId}/retry`),
};
