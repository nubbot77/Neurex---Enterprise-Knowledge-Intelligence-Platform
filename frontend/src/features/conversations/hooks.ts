import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { streamChatMessage } from '@/services/streaming/chatStream';
import { conversationsApi } from './api';
import type { Message } from './types';

export const conversationKeys = {
  all: ['conversations'] as const,
  lists: () => [...conversationKeys.all, 'list'] as const,
  messages: (id: string) => [...conversationKeys.all, id, 'messages'] as const,
};

export function useConversations() {
  return useQuery({
    queryKey: conversationKeys.lists(),
    queryFn: () => conversationsApi.list(),
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => conversationsApi.delete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: conversationKeys.lists(),
      });
    },
  });
}

function newId(): string {
  return crypto.randomUUID();
}

/**
 * Owns the message list + streaming lifecycle for one conversation.
 * Message history is TanStack Query state (server truth); the array is copied into
 * local state so streamed tokens can mutate it turn-by-turn without fighting the
 * query cache mid-stream — the cache is only patched back in once a turn completes.
 */
export function useChatConversation(conversationId: string | undefined) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);
  const lastUserMessageRef = useRef<string | null>(null);

  const historyQuery = useQuery({
    queryKey: conversationId
      ? conversationKeys.messages(conversationId)
      : ['conversations', 'new'],
    queryFn: () => conversationsApi.messages(conversationId ?? ''),
    enabled: Boolean(conversationId),
  });

  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Adjust local state during render (React's documented pattern for "reset state when
  // a value changes") instead of an effect — no extra render-then-setState round trip.
  // Skipped while streaming so a background refetch can't clobber in-flight tokens.
  const [syncedConversationId, setSyncedConversationId] =
    useState(conversationId);
  const [syncedData, setSyncedData] = useState(historyQuery.data);
  if (
    !isStreaming &&
    (syncedConversationId !== conversationId ||
      syncedData !== historyQuery.data)
  ) {
    setSyncedConversationId(conversationId);
    setSyncedData(historyQuery.data);
    setMessages(historyQuery.data ?? []);
  }

  const runStream = useCallback(
    async (text: string) => {
      lastUserMessageRef.current = text;
      const controller = new AbortController();
      abortRef.current = controller;

      const userMessage: Message = {
        id: newId(),
        role: 'user',
        content: text,
        status: 'complete',
        createdAt: new Date().toISOString(),
      };
      const assistantId = newId();
      const assistantMessage: Message = {
        id: assistantId,
        role: 'assistant',
        content: '',
        status: 'streaming',
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsStreaming(true);

      let resolvedConversationId = conversationId;
      let hadError = false;

      try {
        for await (const event of streamChatMessage(
          conversationId,
          text,
          controller.signal,
        )) {
          if (event.type === 'conversation') {
            resolvedConversationId = event.id;
          } else if (event.type === 'token') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + event.content }
                  : m,
              ),
            );
          } else if (event.type === 'citations') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, citations: event.citations } : m,
              ),
            );
          } else if (event.type === 'error') {
            hadError = true;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, status: 'error', error: event.message }
                  : m,
              ),
            );
          }
        }
      } catch (err) {
        hadError = true;
        const message = err instanceof Error ? err.message : 'Connection lost.';
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, status: 'error', error: message }
              : m,
          ),
        );
      } finally {
        setIsStreaming(false);
        if (!hadError) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, status: 'complete' } : m,
            ),
          );
        }
        if (
          resolvedConversationId &&
          resolvedConversationId !== conversationId
        ) {
          void navigate(`/chat/${resolvedConversationId}`, { replace: true });
        }
        if (resolvedConversationId) {
          void queryClient.invalidateQueries({
            queryKey: conversationKeys.messages(resolvedConversationId),
          });
          void queryClient.invalidateQueries({
            queryKey: conversationKeys.lists(),
          });
        }
      }
    },
    [conversationId, navigate, queryClient],
  );

  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim() || isStreaming) return;
      void runStream(text.trim());
    },
    [isStreaming, runStream],
  );

  const regenerate = useCallback(() => {
    if (!lastUserMessageRef.current || isStreaming) return;
    setMessages((prev) => prev.slice(0, -1));
    void runStream(lastUserMessageRef.current);
  }, [isStreaming, runStream]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    isLoadingHistory: historyQuery.isLoading,
    isHistoryError: historyQuery.isError,
    historyError: historyQuery.error,
    refetchHistory: historyQuery.refetch,
    isStreaming,
    sendMessage,
    regenerate,
    stop,
  };
}
