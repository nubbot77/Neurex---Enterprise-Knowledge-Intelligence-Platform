import { apiClient } from '@/services/api/client';
import type { PaginatedResponse } from '@/types/api';
import type {
  DocumentItem,
  DocumentListParams,
  DocumentVersion,
} from './types';

export const documentsApi = {
  list: (params: DocumentListParams = {}) =>
    apiClient.get<PaginatedResponse<DocumentItem>>('/documents', {
      params: {
        page: params.page,
        pageSize: params.pageSize,
        search: params.search,
        type: params.type,
        status: params.status,
        sortBy: params.sortBy,
        sortDirection: params.sortDirection,
      },
    }),

  get: (id: string) => apiClient.get<DocumentItem>(`/documents/${id}`),

  versions: (id: string) =>
    apiClient.get<DocumentVersion[]>(`/documents/${id}/versions`),

  upload: (file: File, tags?: string[]) => {
    const formData = new FormData();
    formData.append('file', file);
    if (tags && tags.length > 0) {
      formData.append('tags', tags.join(','));
    }
    return apiClient.post<DocumentItem>('/documents', formData);
  },

  delete: (id: string) => apiClient.delete<void>(`/documents/${id}`),

  reingest: (id: string) =>
    apiClient.post<DocumentItem>(`/documents/${id}/reingest`),
};
