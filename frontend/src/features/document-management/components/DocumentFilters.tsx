import { Search } from 'lucide-react';
import { Input, Select } from '@/components/ui';
import type { DocumentListParams } from '../types';

export interface DocumentFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  type: DocumentListParams['type'] | '';
  onTypeChange: (value: DocumentListParams['type'] | '') => void;
  status: DocumentListParams['status'] | '';
  onStatusChange: (value: DocumentListParams['status'] | '') => void;
}

export function DocumentFilters({
  search,
  onSearchChange,
  type,
  onTypeChange,
  status,
  onStatusChange,
}: DocumentFiltersProps) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Search
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-fg-subtle"
          aria-hidden="true"
        />
        <Input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search documents…"
          className="pl-9"
          aria-label="Search documents"
        />
      </div>

      <Select
        value={type}
        onChange={(event) =>
          onTypeChange(event.target.value as DocumentListParams['type'] | '')
        }
        className="sm:w-36"
        aria-label="Filter by type"
      >
        <option value="">All types</option>
        <option value="pdf">PDF</option>
        <option value="docx">DOCX</option>
        <option value="html">HTML</option>
        <option value="markdown">Markdown</option>
        <option value="csv">CSV</option>
        <option value="web">Web page</option>
      </Select>

      <Select
        value={status}
        onChange={(event) =>
          onStatusChange(
            event.target.value as DocumentListParams['status'] | '',
          )
        }
        className="sm:w-36"
        aria-label="Filter by status"
      >
        <option value="">All statuses</option>
        <option value="queued">Queued</option>
        <option value="processing">Processing</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
        <option value="retrying">Retrying</option>
      </Select>
    </div>
  );
}
