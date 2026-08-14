import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";
import { ChatBubble } from "@/features/chat/components/ChatBubble";
import { AssistantActions } from "@/features/chat/components/AssistantActions";
import { AssistantRichExtras } from "@/features/chat/components/AssistantRichExtras";
import { RepeatPrompt } from "@/features/chat/components/RepeatPrompt";
import { TypewriterBubble } from "@/features/chat/components/bubbles/TypewriterBubble";

interface MessageListProps {
  messages: ChatMessage[];
  className?: string;
  onPickQuestion?: (text: string) => void;
  onRegenerate?: (message: ChatMessage) => void;
  onRetry?: (message: ChatMessage) => void;
}

/** Vertical list of chat turns. Assistant messages get actions + rich extras. */
export function MessageList({
  messages,
  className,
  onPickQuestion,
  onRegenerate,
  onRetry,
}: MessageListProps) {
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {messages.map((message) => (
        <MessageBlock
          key={message.id}
          message={message}
          onPickQuestion={onPickQuestion}
          onRegenerate={onRegenerate}
          onRetry={onRetry}
        />
      ))}
    </div>
  );
}

function MessageBlock(props: {
  message: ChatMessage;
  onPickQuestion?: (text: string) => void;
  onRegenerate?: (message: ChatMessage) => void;
  onRetry?: (message: ChatMessage) => void;
}) {
  if (props.message.contentType === "text" && props.message.status === "processing" && !props.message.content) {
    return <TypewriterBubble />;
  }

  if (props.message.contentType === "text" && props.message.role === "assistant") {
    return (
      <div className="group flex w-full items-end gap-2">
        <div className="flex max-w-[85%] flex-col">
          <ChatBubble message={props.message} />
          <AssistantRichExtras message={props.message} onPickQuestion={props.onPickQuestion} />
          <AssistantActions
            message={props.message}
            onRegenerate={props.onRegenerate}
            onRetry={props.onRetry}
          />
          {props.message.status === "complete" ? <RepeatPrompt message={props.message} /> : null}
        </div>
      </div>
    );
  }

  if (props.message.status === "processing" && !props.message.content) {
    return <TypewriterBubble className="max-w-[85%]" />;
  }

  return <ChatBubble message={props.message} />;
}