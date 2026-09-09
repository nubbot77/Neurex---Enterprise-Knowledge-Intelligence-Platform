import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { searchApi } from './api';
import type { SearchParams } from './types';

export function useSearch(params: SearchParams) {
  return useQuery({
    queryKey: ['search', params] as const,
    queryFn: () => searchApi.search(params),
    enabled: params.query.trim().length > 0,
    placeholderData: keepPreviousData,
  });
}
