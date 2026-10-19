// Question box: Enter sends, Shift+Enter adds a new line. Disabled (with a hint) until documents are loaded.
// While an answer is coming, the send button becomes a Stop button (Esc also stops).

import { SendHorizontal, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

const MAX_HEIGHT_PX = 160;

export default function ChatInput({ disabled, disabledHint, sending, onSend, onStop, prefill }) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const box = useRef(null);

  useEffect(() => {
    if (prefill) {
      setText(prefill.text);
      box.current?.focus();
    }
  }, [prefill]);

  useEffect(() => {
    const element = box.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [text]);

  useEffect(() => {
    if (!sending) return undefined;
    const stopOnEscape = (event) => event.key === "Escape" && onStop();
    document.addEventListener("keydown", stopOnEscape);
    return () => document.removeEventListener("keydown", stopOnEscape);
  }, [sending, onStop]);

  const blocked = disabled || sending;

  function send() {
    if (blocked || !text.trim()) return;
    onSend(text.trim());
    setText("");
  }

  function onKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      send();
    }
  }

  return (
    <div className="border-t border-line bg-surface px-4 py-3">
      <div className="mx-auto flex max-w-[860px] items-end gap-2 rounded-card border border-line bg-surface p-2 focus-within:border-brand-teal">
        <textarea
          ref={box}
          rows={1}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled}
          placeholder={disabled ? disabledHint : t("chat.placeholder")}
          aria-label={t("chat.question")}
          dir="auto"
          className="max-h-40 min-h-[36px] flex-1 resize-none bg-transparent px-2 py-1.5 leading-6 outline-none placeholder:text-ink-quiet/70 disabled:cursor-not-allowed"
        />
        {sending ? (
          <button
            onClick={onStop}
            aria-label={t("chat.stop")}
            title={t("chat.stopTitle")}
            className="rounded-button bg-status-error p-2.5 text-white hover:opacity-90"
          >
            <Square size={18} strokeWidth={1.75} fill="currentColor" />
          </button>
        ) : (
          <button
            onClick={send}
            disabled={blocked || !text.trim()}
            aria-label={t("chat.send")}
            className="rounded-button bg-brand-navy p-2.5 text-white hover:bg-brand-navy-light disabled:cursor-not-allowed disabled:opacity-40"
          >
            <SendHorizontal size={18} strokeWidth={1.75} className="rtl:rotate-180" />
          </button>
        )}
      </div>
    </div>
  );
}
