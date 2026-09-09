export interface SearchResult {
  id: string;
  documentId: string;
  documentTitle: string;
  chunkId: string;
  snippet: string;
  pageNumber?: number;
  score: number;
  lexicalScore?: number;
  denseScore?: number;
  fusedScore?: number;
  rerankerScore?: number;
}

export interface SearchParams {
  query: string;
  page?: number;
  pageSize?: number;
}
