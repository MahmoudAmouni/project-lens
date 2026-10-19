// Chat state: the messages, sending a question, retrying after an error, clearing the chat.

import { useCallback, useRef, useState } from "react";
import { askQuestion } from "../api/serverApi";

const HISTORY_MESSAGES = 6; // the Server also keeps only the last 6

let nextId = 1;
const newId = () => nextId++;

/** Messages look like: { id, role: "user" | "agent" | "error", text, answer?, question? } */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const history = () =>
    messagesRef.current
      .filter((message) => message.role !== "error")
      .slice(-HISTORY_MESSAGES)
      .map((message) => ({ role: message.role === "user" ? "user" : "assistant", content: message.text }));

  const send = useCallback(async (question) => {
    const text = question.trim();
    if (!text) return;
    const past = history();
    setMessages((current) => [...current, { id: newId(), role: "user", text }]);
    setSending(true);
    try {
      const answer = await askQuestion(text, past);
      setMessages((current) => [
        ...current,
        { id: newId(), role: "agent", text: answer.answer, answer, question: text },
      ]);
    } catch (err) {
      setMessages((current) => [
        ...current,
        { id: newId(), role: "error", text: err.message, code: err.code, question: text },
      ]);
    } finally {
      setSending(false);
    }
  }, []);

  /** Ask the question of an error card again: the error and its question bubble are replaced. */
  const retry = useCallback(
    (errorId) => {
      const all = messagesRef.current;
      const index = all.findIndex((message) => message.id === errorId);
      if (index < 0) return;
      const question = all[index].question;
      setMessages(all.slice(0, Math.max(0, index - 1)));
      messagesRef.current = all.slice(0, Math.max(0, index - 1));
      send(question);
    },
    [send],
  );

  const clear = useCallback(() => setMessages([]), []);

  return { messages, sending, send, retry, clear };
}
