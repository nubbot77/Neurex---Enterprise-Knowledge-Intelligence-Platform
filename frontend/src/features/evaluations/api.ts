import { apiClient } from '@/services/api/client';
import type { PaginatedResponse } from '@/types/api';
import type { EvaluationDataset, EvaluationRun } from './types';

export const evaluationsApi = {
  listDatasets: () =>
    apiClient.get<PaginatedResponse<EvaluationDataset>>(
      '/evaluations/datasets',
    ),

  listRuns: () =>
    apiClient.get<PaginatedResponse<EvaluationRun>>('/evaluations/runs'),

  getRun: (id: string) =>
    apiClient.get<EvaluationRun>(`/evaluations/runs/${id}`),
};
