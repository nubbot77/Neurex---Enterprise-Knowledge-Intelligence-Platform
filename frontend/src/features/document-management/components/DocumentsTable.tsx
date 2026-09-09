import { Eye, MoreHorizontal, RefreshCw, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  DropdownMenu,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';
import { formatBytes, formatDate } from '@/utils/format';
import { useDeleteDocument, useReingestDocument } from '../hooks';
import type { DocumentItem } from '../types';
import { DocumentStatusBadge } from './DocumentStatusBadge';

export interface DocumentsTableProps {
  documents: DocumentItem[];
}

export function DocumentsTable({ documents }: DocumentsTableProps) {
  const navigate = useNavigate();
  const deleteDocument = useDeleteDocument();
  const reingestDocument = useReingestDocument();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Size</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Uploaded</TableHead>
          <TableHead className="w-10" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {documents.map((doc) => (
          <TableRow key={doc.id}>
            <TableCell className="font-medium">{doc.name}</TableCell>
            <TableCell className="uppercase">{doc.type}</TableCell>
            <TableCell>{formatBytes(doc.sizeBytes)}</TableCell>
            <TableCell>
              <DocumentStatusBadge status={doc.status} />
            </TableCell>
            <TableCell>{formatDate(doc.uploadedAt)}</TableCell>
            <TableCell>
              <DropdownMenu
                align="end"
                trigger={
                  <button
                    type="button"
                    aria-label={`Actions for ${doc.name}`}
                    className="rounded-md p-1.5 text-fg-muted hover:bg-surface-hover hover:text-fg"
                  >
                    <MoreHorizontal className="size-4" />
                  </button>
                }
                items={[
                  {
                    label: 'View',
                    icon: Eye,
                    onSelect: () => {
                      void navigate(`/documents/${doc.id}`);
                    },
                  },
                  {
                    label: 'Re-ingest',
                    icon: RefreshCw,
                    onSelect: () => reingestDocument.mutate(doc.id),
                  },
                  {
                    label: 'Delete',
                    icon: Trash2,
                    destructive: true,
                    onSelect: () => deleteDocument.mutate(doc.id),
                  },
                ]}
              />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
