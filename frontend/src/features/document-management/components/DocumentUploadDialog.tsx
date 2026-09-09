import { AlertCircle, CheckCircle2, Upload as UploadIcon } from 'lucide-react';
import { useRef, useState } from 'react';
import { Button, Dialog, Spinner } from '@/components/ui';
import { toUserMessage } from '@/services/api/errors';
import { cn } from '@/utils/cn';
import { formatBytes } from '@/utils/format';
import { useUploadDocument } from '../hooks';

const ACCEPTED_TYPES = '.pdf,.docx,.html,.htm,.md,.csv';
const MAX_SIZE_BYTES = 50 * 1024 * 1024;

interface FileUploadState {
  file: File;
  status: 'uploading' | 'done' | 'error';
  error?: string;
}

export interface DocumentUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DocumentUploadDialog({
  open,
  onOpenChange,
}: DocumentUploadDialogProps) {
  const [items, setItems] = useState<FileUploadState[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadDocument();

  const startUploads = (files: FileList | File[]) => {
    const list = Array.from(files);
    const validated = list.map((file): FileUploadState => {
      if (file.size > MAX_SIZE_BYTES) {
        return {
          file,
          status: 'error',
          error: `Exceeds ${formatBytes(MAX_SIZE_BYTES)} limit`,
        };
      }
      return { file, status: 'uploading' };
    });
    setItems((prev) => [...prev, ...validated]);

    for (const entry of validated) {
      if (entry.status === 'error') continue;
      upload.mutate(
        { file: entry.file },
        {
          onSuccess: () => {
            setItems((prev) =>
              prev.map((it) =>
                it.file === entry.file ? { ...it, status: 'done' } : it,
              ),
            );
          },
          onError: (error) => {
            setItems((prev) =>
              prev.map((it) =>
                it.file === entry.file
                  ? { ...it, status: 'error', error: toUserMessage(error) }
                  : it,
              ),
            );
          },
        },
      );
    }
  };

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen) setItems([]);
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose} title="Upload documents">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragActive(false);
          if (event.dataTransfer.files.length > 0)
            startUploads(event.dataTransfer.files);
        }}
        className={cn(
          'flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors',
          dragActive ? 'border-accent bg-accent/5' : 'border-border',
        )}
      >
        <UploadIcon className="size-6 text-fg-subtle" aria-hidden="true" />
        <p className="text-sm text-fg-muted">
          Drag & drop files, or{' '}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="text-accent hover:underline"
          >
            browse
          </button>
        </p>
        <p className="text-xs text-fg-subtle">
          PDF, DOCX, HTML, Markdown, CSV — up to 50 MB
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={(event) => {
            if (event.target.files && event.target.files.length > 0) {
              startUploads(event.target.files);
              event.target.value = '';
            }
          }}
        />
      </div>

      {items.length > 0 && (
        <ul className="mt-4 max-h-48 space-y-2 overflow-y-auto">
          {items.map((item, index) => (
            <li
              key={`${item.file.name}-${index}`}
              className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm"
            >
              <span className="flex-1 truncate text-fg">{item.file.name}</span>
              <span className="text-xs text-fg-subtle">
                {formatBytes(item.file.size)}
              </span>
              {item.status === 'uploading' && <Spinner size={14} />}
              {item.status === 'done' && (
                <CheckCircle2
                  className="size-4 text-success"
                  aria-label="Uploaded"
                />
              )}
              {item.status === 'error' && (
                <span
                  className="flex items-center gap-1 text-danger"
                  title={item.error}
                >
                  <AlertCircle className="size-4" aria-hidden="true" />
                  <span className="max-w-32 truncate text-xs">
                    {item.error}
                  </span>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex justify-end">
        <Button variant="outline" onClick={() => handleClose(false)}>
          Done
        </Button>
      </div>
    </Dialog>
  );
}
