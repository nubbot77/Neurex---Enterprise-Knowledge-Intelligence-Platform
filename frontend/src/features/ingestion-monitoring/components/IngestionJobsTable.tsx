import { FileText, RotateCw } from 'lucide-react';
import {
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';
import { DocumentStatusBadge } from '@/features/document-management/components';
import { formatDate } from '@/utils/format';
import { useRetryIngestionJob } from '../hooks';
import type { IngestionJob } from '../types';
import { IngestionProgressBar } from './IngestionProgressBar';

export interface IngestionJobsTableProps {
  jobs: IngestionJob[];
  onViewLogs: (jobId: string) => void;
}

export function IngestionJobsTable({
  jobs,
  onViewLogs,
}: IngestionJobsTableProps) {
  const retryJob = useRetryIngestionJob();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Document</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Stage</TableHead>
          <TableHead>Progress</TableHead>
          <TableHead>Started</TableHead>
          <TableHead className="w-24" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.map((job) => (
          <TableRow key={job.id}>
            <TableCell className="font-medium">{job.documentName}</TableCell>
            <TableCell>
              <DocumentStatusBadge status={job.status} />
            </TableCell>
            <TableCell className="capitalize">{job.stage}</TableCell>
            <TableCell className="w-32">
              <IngestionProgressBar progress={job.progress} />
            </TableCell>
            <TableCell>{formatDate(job.startedAt)}</TableCell>
            <TableCell>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`View logs for ${job.documentName}`}
                  onClick={() => onViewLogs(job.id)}
                >
                  <FileText className="size-4" />
                </Button>
                {job.status === 'failed' && (
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Retry ${job.documentName}`}
                    onClick={() => retryJob.mutate(job.id)}
                    loading={retryJob.isPending}
                  >
                    <RotateCw className="size-4" />
                  </Button>
                )}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
