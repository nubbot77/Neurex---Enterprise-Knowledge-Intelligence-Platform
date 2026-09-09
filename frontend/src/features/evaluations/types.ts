export interface EvaluationDataset {
  id: string;
  name: string;
  description: string;
  questionCount: number;
  createdAt: string;
}

export type EvaluationRunStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface EvaluationMetrics {
  recallAtK?: number;
  precisionAtK?: number;
  mrr?: number;
  ndcg?: number;
  faithfulness?: number;
  contextRelevance?: number;
  answerCorrectness?: number;
  citationAccuracy?: number;
  citationCompleteness?: number;
  p50LatencyMs?: number;
  p95LatencyMs?: number;
  p99LatencyMs?: number;
  costPerQuery?: number;
}

export interface EvaluationRun {
  id: string;
  datasetId: string;
  datasetName: string;
  status: EvaluationRunStatus;
  startedAt: string;
  completedAt?: string;
  metrics?: EvaluationMetrics;
}
