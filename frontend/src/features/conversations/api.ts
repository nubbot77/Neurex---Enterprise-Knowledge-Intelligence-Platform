import { apiClient } from '@/services/api/client';
import type { PaginatedResponse } from '@/types/api';
import type { Conversation, Message } from './types';

export const conversationsApi = {
  list: () =>
    apiClient.get<PaginatedResponse<Conversation>>('/chat/conversations'),

  messages: (conversationId: string) =>
    apiClient.get<Message[]>(`/chat/conversations/${conversationId}/messages`),

  delete: (conversationId: string) =>
    apiClient.delete<void>(`/chat/conversations/${conversationId}`),
};
