// Scroll area with all messages; scrolls to the newest one.

import { useEffect, useRef } from "react";
import AgentMessage from "./AgentMessage";
import EmptyState from "./EmptyState";
import ErrorMessage from "./ErrorMessage";
import ThinkingIndicator from "./ThinkingIndicator";
import UserMessage from "./UserMessage";

export default function ChatWindow({ chat, documents, onAskAgain, onOpenMenu }) {
  const end = useRef(null);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chat.messages.length, chat.sending]);

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto max-w-[860px] space-y-4">
        {chat.messages.length === 0 && !chat.sending ? (
          <EmptyState
            documents={documents.documents}
            readableCount={documents.readable_count}
            loading={documents.loading}
            onAsk={chat.send}
            onOpenMenu={onOpenMenu}
          />
        ) : (
          chat.messages.map((message) => {
            if (message.role === "user") return <UserMessage key={message.id} text={message.text} />;
            if (message.role === "error") {
              return (
                <ErrorMessage key={message.id} text={message.text} onRetry={() => chat.retry(message.id)} />
              );
            }
            return (
              <AgentMessage
                key={message.id}
                answer={message.answer}
                onAskAgain={() => onAskAgain(message.question)}
              />
            );
          })
        )}
        {chat.sending && <ThinkingIndicator />}
        <div ref={end} />
      </div>
    </div>
  );
}
