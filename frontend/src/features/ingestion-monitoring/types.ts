import type { IngestionStatus } from '@/features/document-management/types';

export type IngestionStage =
  'uploading' | 'parsing' | 'chunking' | 'embedding' | 'indexing' | 'done';

export interface IngestionJob {
  id: string;
  documentId: string;
  documentName: string;
  status: IngestionStatus;
  stage: IngestionStage;
  progress: number;
  startedAt: string;
  completedAt?: string;
  error?: string;
  retryCount: number;
}

export interface IngestionLogEntry {
  timestamp: string;
  level: 'info' | 'warn' | 'error';
  message: string;
}

export interface IngestionJobListParams {
  page?: number;
  pageSize?: number;
  status?: IngestionStatus;
}
