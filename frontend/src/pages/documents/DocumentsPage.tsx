import { Upload } from 'lucide-react';
import { useState } from 'react';
import {
  Button,
  EmptyState,
  ErrorState,
  Pagination,
  Skeleton,
  Tabs,
  TabsList,
  TabsPanel,
  TabsTrigger,
} from '@/components/ui';
import {
  DocumentFilters,
  DocumentsTable,
  DocumentUploadDialog,
} from '@/features/document-management/components';
import { useDocuments } from '@/features/document-management/hooks';
import type { DocumentListParams } from '@/features/document-management/types';
import { IngestionJobsPanel } from '@/features/ingestion-monitoring/components';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { toUserMessage } from '@/services/api/errors';

const PAGE_SIZE = 20;

export function DocumentsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [type, setType] = useState<DocumentListParams['type'] | ''>('');
  const [status, setStatus] = useState<DocumentListParams['status'] | ''>('');
  const [uploadOpen, setUploadOpen] = useState(false);

  const debouncedSearch = useDebouncedValue(search, 300);

  const { data, isLoading, isError, error, refetch } = useDocuments({
    page,
    pageSize: PAGE_SIZE,
    search: debouncedSearch.length > 0 ? debouncedSearch : undefined,
    type: type !== '' ? type : undefined,
    status: status !== '' ? status : undefined,
  });

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-fg">Documents</h1>
          <p className="text-sm text-fg-muted">
            Upload, search, and manage ingested documents.
          </p>
        </div>
        <Button onClick={() => setUploadOpen(true)}>
          <Upload className="size-4" />
          Upload
        </Button>
      </div>

      <Tabs defaultValue="documents">
        <TabsList>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="ingestion">Ingestion jobs</TabsTrigger>
        </TabsList>

        <TabsPanel value="documents" className="space-y-4">
          <DocumentFilters
            search={search}
            onSearchChange={(value) => {
              setSearch(value);
              setPage(1);
            }}
            type={type}
            onTypeChange={(value) => {
              setType(value);
              setPage(1);
            }}
            status={status}
            onStatusChange={(value) => {
              setStatus(value);
              setPage(1);
            }}
          />

          {isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          )}

          {isError && (
            <ErrorState
              description={toUserMessage(error)}
              onRetry={() => void refetch()}
            />
          )}

          {!isLoading && !isError && data?.items.length === 0 && (
            <EmptyState
              title="No documents yet"
              description="Upload a PDF, DOCX, HTML, Markdown, or CSV file to get started."
              action={
                <Button onClick={() => setUploadOpen(true)}>
                  Upload a document
                </Button>
              }
            />
          )}

          {!isLoading && !isError && data && data.items.length > 0 && (
            <>
              <DocumentsTable documents={data.items} />
              <Pagination
                page={data.page}
                totalPages={Math.max(1, Math.ceil(data.total / data.pageSize))}
                onPageChange={setPage}
                className="pt-2"
              />
            </>
          )}
        </TabsPanel>

        <TabsPanel value="ingestion" className="space-y-4">
          <IngestionJobsPanel />
        </TabsPanel>
      </Tabs>

      <DocumentUploadDialog open={uploadOpen} onOpenChange={setUploadOpen} />
    </div>
  );
}
