export interface Citation {
  id: string;
  documentId: string;
  documentTitle: string;
  chunkId: string;
  snippet: string;
  pageNumber?: number;
}

export type MessageRole = 'user' | 'assistant';
export type MessageStatus = 'sending' | 'streaming' | 'complete' | 'error';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  citations?: Citation[];
  status: MessageStatus;
  error?: string;
  createdAt: string;
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
}
