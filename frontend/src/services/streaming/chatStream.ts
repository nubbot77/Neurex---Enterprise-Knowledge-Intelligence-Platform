import { useAuthStore } from '@/stores/authStore';
import type { Citation } from '@/features/conversations/types';

export type ChatStreamEvent =
  | { type: 'conversation'; id: string }
  | { type: 'token'; content: string }
  | { type: 'citations'; citations: Citation[] }
  | { type: 'done' }
  | { type: 'error'; message: string };

const baseUrl = import.meta.env.VITE_API_URL.replace(/\/+$/, '');

/**
 * Streams a chat response as newline-delimited SSE ("data: {...}\n\n" frames).
 * A raw fetch + ReadableStream reader, not EventSource — EventSource can't send
 * a POST body or custom headers, both of which a chat turn needs (message + auth).
 */
export async function* streamChatMessage(
  conversationId: string | undefined,
  message: string,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const token = useAuthStore.getState().accessToken;

  const response = await fetch(`${baseUrl}/chat/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ conversationId, message }),
    signal,
  });

  if (!response.ok || !response.body) {
    yield { type: 'error', message: `Request failed (${response.status})` };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        const payload = frame.replace(/^data:\s*/, '').trim();
        if (!payload) continue;
        yield JSON.parse(payload) as ChatStreamEvent;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
