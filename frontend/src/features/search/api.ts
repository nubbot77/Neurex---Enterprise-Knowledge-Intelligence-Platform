import { apiClient } from '@/services/api/client';
import type { PaginatedResponse } from '@/types/api';
import type { SearchParams, SearchResult } from './types';

export const searchApi = {
  search: (params: SearchParams) =>
    apiClient.get<PaginatedResponse<SearchResult>>('/search', {
      params: { q: params.query, page: params.page, pageSize: params.pageSize },
    }),
};
