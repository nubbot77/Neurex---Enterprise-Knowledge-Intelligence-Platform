import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';
import { formatDate } from '@/utils/format';
import type { EvaluationDataset } from '../types';

export function DatasetsTable({ datasets }: { datasets: EvaluationDataset[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Description</TableHead>
          <TableHead>Questions</TableHead>
          <TableHead>Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {datasets.map((dataset) => (
          <TableRow key={dataset.id}>
            <TableCell className="font-medium">{dataset.name}</TableCell>
            <TableCell className="text-fg-muted">
              {dataset.description}
            </TableCell>
            <TableCell>{dataset.questionCount}</TableCell>
            <TableCell>{formatDate(dataset.createdAt)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
