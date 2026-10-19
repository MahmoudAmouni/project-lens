// Chat state: the messages, sending a question, stopping it, retrying after an error, clearing the chat.
// The chat is kept in the browser, so it survives a reload.

import { useCallback, useEffect, useRef, useState } from "react";
import { askQuestion } from "../api/serverApi";
import { toHistory } from "../utils/chatHistory";
import { loadChat, saveChat } from "../utils/chatStorage";

const savedMessages = loadChat();
let nextId = Math.max(0, ...savedMessages.map((message) => message.id)) + 1;

/** The screen language ("ar" or "en"), a hint the Server uses for very short questions like "BOQ?". */
const screenLanguage = () => (document.documentElement.lang === "ar" ? "ar" : "en");
const newId = () => nextId++;

/** Messages look like: { id, role: "user" | "agent" | "error" | "stopped", text, answer?, question? } */
/** `model` is the AI model the user picked; each question is sent with it. */
export function useChat(model = "") {
  const [messages, setMessages] = useState(savedMessages);
  const [sending, setSending] = useState(false);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const controller = useRef(null);
  const modelRef = useRef(model);
  modelRef.current = model;

  useEffect(() => saveChat(messages), [messages]);

  const history = () => toHistory(messagesRef.current);

  const send = useCallback(async (question) => {
    const text = question.trim();
    if (!text) return;
    const past = history();
    setMessages((current) => [...current, { id: newId(), role: "user", text }]);
    setSending(true);
    controller.current = new AbortController();
    try {
      const answer = await askQuestion(
        text,
        past,
        screenLanguage(),
        modelRef.current,
        controller.current.signal,
      );
      setMessages((current) => [
        ...current,
        { id: newId(), role: "agent", text: answer.answer, answer, question: text },
      ]);
    } catch (err) {
      const role = err.code === "STOPPED" ? "stopped" : "error";
      setMessages((current) => [
        ...current,
        { id: newId(), role, text: err.message, code: err.code, question: text },
      ]);
    } finally {
      controller.current = null;
      setSending(false);
    }
  }, []);

  /** Stop the question being answered: the request is cancelled and the Server stops the agent. */
  const stop = useCallback(() => controller.current?.abort(), []);

  /** Ask again after an error or a stop: that card and its question bubble are replaced. */
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

  return { messages, sending, send, stop, retry, clear };
}
