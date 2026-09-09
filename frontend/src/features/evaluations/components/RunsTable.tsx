import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';
import { formatDate } from '@/utils/format';
import type { EvaluationRun } from '../types';
import { RunStatusBadge } from './RunStatusBadge';

export interface RunsTableProps {
  runs: EvaluationRun[];
  onSelectRun: (run: EvaluationRun) => void;
}

export function RunsTable({ runs, onSelectRun }: RunsTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Dataset</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Started</TableHead>
          <TableHead>Completed</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => (
          <TableRow
            key={run.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelectRun(run)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelectRun(run);
              }
            }}
            className="cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-inset"
          >
            <TableCell className="font-medium">{run.datasetName}</TableCell>
            <TableCell>
              <RunStatusBadge status={run.status} />
            </TableCell>
            <TableCell>{formatDate(run.startedAt)}</TableCell>
            <TableCell>
              {run.completedAt ? formatDate(run.completedAt) : '—'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
