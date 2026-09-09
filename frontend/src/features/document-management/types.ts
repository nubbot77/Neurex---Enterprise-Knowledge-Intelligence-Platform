export type DocumentType = 'pdf' | 'docx' | 'html' | 'markdown' | 'csv' | 'web';

export type IngestionStatus =
  'queued' | 'processing' | 'completed' | 'failed' | 'retrying';

export interface DocumentItem {
  id: string;
  name: string;
  type: DocumentType;
  sizeBytes: number;
  status: IngestionStatus;
  uploadedAt: string;
  updatedAt: string;
  version: number;
  tags: string[];
}

export interface DocumentVersion {
  id: string;
  version: number;
  status: IngestionStatus;
  createdAt: string;
}

export interface DocumentListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  type?: DocumentType;
  status?: IngestionStatus;
  sortBy?: 'name' | 'uploadedAt' | 'sizeBytes';
  sortDirection?: 'asc' | 'desc';
}
