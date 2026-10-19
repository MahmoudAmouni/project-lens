// Scroll area with all messages; scrolls to the newest one.

import { useEffect, useRef } from "react";
import AgentMessage from "./AgentMessage";
import OutOfScopeMessage from "./OutOfScopeMessage";
import StoppedMessage from "./StoppedMessage";
import EmptyState from "./EmptyState";
import ErrorMessage from "./ErrorMessage";
import ThinkingIndicator from "./ThinkingIndicator";
import UserMessage from "./UserMessage";

const FIXED_REPLY_KINDS = ["out_of_scope", "greeting"];

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
            if (message.role === "stopped") {
              return <StoppedMessage key={message.id} onAskAgain={() => chat.retry(message.id)} />;
            }
            if (message.role === "error") {
              return (
                <ErrorMessage
                  key={message.id}
                  error={{ code: message.code, message: message.text }}
                  onRetry={() => chat.retry(message.id)}
                />
              );
            }
            if (FIXED_REPLY_KINDS.includes(message.answer.kind)) {
              return <OutOfScopeMessage key={message.id} answer={message.answer} onAsk={chat.send} />;
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
