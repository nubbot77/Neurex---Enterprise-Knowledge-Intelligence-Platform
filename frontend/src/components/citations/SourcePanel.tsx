import { Dialog } from '@/components/ui';
import type { Citation } from '@/features/conversations/types';
import { SourcePreview } from './SourcePreview';

export interface SourcePanelProps {
  citation: Citation | null;
  onOpenChange: (open: boolean) => void;
}

export function SourcePanel({ citation, onOpenChange }: SourcePanelProps) {
  return (
    <Dialog open={Boolean(citation)} onOpenChange={onOpenChange} title="Source">
      {citation && <SourcePreview citation={citation} />}
    </Dialog>
  );
}
