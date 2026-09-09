import { MessageSquare, Plus, Trash2 } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { Button, Skeleton } from '@/components/ui';
import {
  useConversations,
  useDeleteConversation,
} from '@/features/conversations/hooks';
import { cn } from '@/utils/cn';

export function ConversationSidebar() {
  const { data, isLoading } = useConversations();
  const deleteConversation = useDeleteConversation();

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border md:flex">
      <div className="p-3">
        <NavLink to="/chat" end>
          <Button variant="outline" className="w-full justify-start">
            <Plus className="size-4" />
            New chat
          </Button>
        </NavLink>
      </div>

      <nav
        aria-label="Conversations"
        className="flex-1 space-y-0.5 overflow-y-auto px-3 pb-3"
      >
        {isLoading &&
          Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}

        {data?.items.map((conversation) => (
          <div key={conversation.id} className="group flex items-center gap-1">
            <NavLink
              to={`/chat/${conversation.id}`}
              className={({ isActive }) =>
                cn(
                  'flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                  isActive
                    ? 'bg-accent/10 text-accent'
                    : 'text-fg-muted hover:bg-surface-hover hover:text-fg',
                )
              }
            >
              <MessageSquare className="size-3.5 shrink-0" aria-hidden="true" />
              <span className="truncate">{conversation.title}</span>
            </NavLink>
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Delete conversation ${conversation.title}`}
              className="size-7 shrink-0 opacity-0 group-hover:opacity-100"
              onClick={() => deleteConversation.mutate(conversation.id)}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        ))}
      </nav>
    </aside>
  );
}
