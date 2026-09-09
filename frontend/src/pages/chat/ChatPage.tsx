import { useParams } from 'react-router-dom';
import { ErrorState, Skeleton } from '@/components/ui';
import {
  ChatHeader,
  ConversationSidebar,
  MessageInput,
  MessageList,
} from '@/components/chat';
import { useChatConversation } from '@/features/conversations/hooks';
import { toUserMessage } from '@/services/api/errors';

export function ChatPage() {
  const { conversationId } = useParams<{ conversationId: string }>();

  const {
    messages,
    isLoadingHistory,
    isHistoryError,
    historyError,
    refetchHistory,
    isStreaming,
    sendMessage,
    regenerate,
    stop,
  } = useChatConversation(conversationId);

  return (
    <div className="flex h-full">
      <ConversationSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          title={conversationId ? 'Conversation' : 'New conversation'}
        />

        {isLoadingHistory ? (
          <div className="flex-1 space-y-3 p-4">
            <Skeleton className="h-16 w-2/3" />
            <Skeleton className="h-16 w-1/2 self-end" />
          </div>
        ) : isHistoryError ? (
          <div className="flex flex-1 items-center justify-center p-6">
            <ErrorState
              description={toUserMessage(historyError)}
              onRetry={() => void refetchHistory()}
            />
          </div>
        ) : (
          <MessageList messages={messages} onRegenerate={regenerate} />
        )}

        <MessageInput
          onSend={sendMessage}
          onStop={stop}
          isStreaming={isStreaming}
        />
      </div>
    </div>
  );
}
