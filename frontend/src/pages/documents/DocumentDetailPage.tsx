import { RefreshCw, Trash2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Button,
  Card,
  CardContent,
  ErrorState,
  Skeleton,
} from '@/components/ui';
import { DocumentStatusBadge } from '@/features/document-management/components';
import {
  useDeleteDocument,
  useDocument,
  useDocumentVersions,
  useReingestDocument,
} from '@/features/document-management/hooks';
import { toUserMessage } from '@/services/api/errors';
import { formatBytes, formatDate } from '@/utils/format';

export function DocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();

  const {
    data: doc,
    isLoading,
    isError,
    error,
    refetch,
  } = useDocument(documentId ?? '');
  const { data: versions } = useDocumentVersions(documentId ?? '');
  const reingest = useReingestDocument();
  const deleteDocument = useDeleteDocument();

  if (isLoading) {
    return (
      <div className="space-y-3 p-6">
        <Skeleton className="h-6 w-64" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (isError || !doc) {
    return (
      <div className="p-6">
        <ErrorState
          title="Couldn't load document"
          description={error ? toUserMessage(error) : 'Document not found.'}
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-fg">{doc.name}</h1>
          <div className="mt-1 flex items-center gap-2">
            <DocumentStatusBadge status={doc.status} />
            <span className="text-sm text-fg-muted">
              {doc.type.toUpperCase()} · {formatBytes(doc.sizeBytes)} · v
              {doc.version}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => reingest.mutate(doc.id)}
            loading={reingest.isPending}
          >
            <RefreshCw className="size-4" />
            Re-ingest
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              deleteDocument.mutate(doc.id, {
                onSuccess: () => void navigate('/documents'),
              });
            }}
            loading={deleteDocument.isPending}
          >
            <Trash2 className="size-4" />
            Delete
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
          <div>
            <p className="text-fg-subtle">Uploaded</p>
            <p className="text-fg">{formatDate(doc.uploadedAt)}</p>
          </div>
          <div>
            <p className="text-fg-subtle">Last updated</p>
            <p className="text-fg">{formatDate(doc.updatedAt)}</p>
          </div>
          <div>
            <p className="text-fg-subtle">Tags</p>
            <p className="text-fg">
              {doc.tags.length > 0 ? doc.tags.join(', ') : '—'}
            </p>
          </div>
        </CardContent>
      </Card>

      {versions && versions.length > 0 && (
        <Card>
          <CardContent className="space-y-2">
            <p className="text-sm font-medium text-fg">Versions</p>
            <ul className="space-y-1.5">
              {versions.map((version) => (
                <li
                  key={version.id}
                  className="flex items-center justify-between text-sm text-fg-muted"
                >
                  <span>v{version.version}</span>
                  <DocumentStatusBadge status={version.status} />
                  <span>{formatDate(version.createdAt)}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
