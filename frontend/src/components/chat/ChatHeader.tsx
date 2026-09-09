import { Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui';

export function ChatHeader({ title }: { title: string }) {
  return (
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-border px-4">
      <h1 className="truncate text-sm font-medium text-fg">{title}</h1>
      <Link to="/chat">
        <Button variant="ghost" size="sm">
          <Plus className="size-4" />
          New chat
        </Button>
      </Link>
    </div>
  );
}
