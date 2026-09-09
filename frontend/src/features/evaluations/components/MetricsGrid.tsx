import { Card, CardContent, EmptyState } from '@/components/ui';
import type { EvaluationMetrics } from '../types';

type MetricFormat = 'ratio' | 'ms' | 'currency';

const metricConfig: {
  key: keyof EvaluationMetrics;
  label: string;
  format: MetricFormat;
}[] = [
  { key: 'recallAtK', label: 'Recall@K', format: 'ratio' },
  { key: 'precisionAtK', label: 'Precision@K', format: 'ratio' },
  { key: 'mrr', label: 'MRR', format: 'ratio' },
  { key: 'ndcg', label: 'nDCG', format: 'ratio' },
  { key: 'faithfulness', label: 'Faithfulness', format: 'ratio' },
  { key: 'contextRelevance', label: 'Context relevance', format: 'ratio' },
  { key: 'answerCorrectness', label: 'Answer correctness', format: 'ratio' },
  { key: 'citationAccuracy', label: 'Citation accuracy', format: 'ratio' },
  {
    key: 'citationCompleteness',
    label: 'Citation completeness',
    format: 'ratio',
  },
  { key: 'p50LatencyMs', label: 'P50 latency', format: 'ms' },
  { key: 'p95LatencyMs', label: 'P95 latency', format: 'ms' },
  { key: 'p99LatencyMs', label: 'P99 latency', format: 'ms' },
  { key: 'costPerQuery', label: 'Cost / query', format: 'currency' },
];

function formatValue(value: number, format: MetricFormat): string {
  if (format === 'ratio') return value.toFixed(3);
  if (format === 'ms') return `${Math.round(value)} ms`;
  return `$${value.toFixed(4)}`;
}

export function MetricsGrid({
  metrics,
}: {
  metrics: EvaluationMetrics | undefined;
}) {
  const entries = metricConfig.filter((m) => metrics?.[m.key] !== undefined);

  if (!metrics || entries.length === 0) {
    return (
      <EmptyState
        title="No metrics yet"
        description="Metrics appear once this evaluation run completes."
      />
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {entries.map(({ key, label, format }) => (
        <Card key={key}>
          <CardContent className="space-y-1 p-3">
            <p className="text-xs text-fg-subtle">{label}</p>
            <p className="text-lg font-semibold text-fg">
              {formatValue(metrics[key]!, format)}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
