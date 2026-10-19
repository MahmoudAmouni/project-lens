// Puts the sidebar (documents) and the chat together.

import { useCallback, useEffect, useState } from "react";
import { getHealth } from "./api/serverApi";
import ChatInput from "./components/chat/ChatInput";
import ChatWindow from "./components/chat/ChatWindow";
import AiKeyBanner from "./components/layout/AiKeyBanner";
import Sidebar from "./components/layout/Sidebar";
import Toast from "./components/layout/Toast";
import TopBar from "./components/layout/TopBar";
import { useChat } from "./hooks/useChat";
import { useDocuments } from "./hooks/useDocuments";

export default function App() {
  const documents = useDocuments();
  const chat = useChat();
  const [model, setModel] = useState("");
  const [aiKeySet, setAiKeySet] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [prefill, setPrefill] = useState(null);

  // The model name and whether the AI key is set; retried while the Server is still starting.
  useEffect(() => {
    let timer;
    const check = (triesLeft) =>
      getHealth()
        .then((health) => {
          setModel(health.model);
          setAiKeySet(health.ai_key_set);
        })
        .catch(() => {
          if (triesLeft > 0) timer = setTimeout(() => check(triesLeft - 1), 2000);
        });
    check(15);
    return () => clearTimeout(timer);
  }, []);

  const loadFolder = useCallback(
    async (path) => {
      if (await documents.load(path)) setMenuOpen(false);
    },
    [documents],
  );
  const uploadFiles = useCallback(
    async (files) => {
      if (await documents.upload(files)) setMenuOpen(false);
    },
    [documents],
  );

  const noDocuments = documents.readable_count === 0;
  const hint = documents.loading
    ? "Reading your documents…"
    : "Load a folder with PDF or Excel files to start";

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        documents={{ ...documents, load: loadFolder, upload: uploadFiles }}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
      />
      <main className="flex min-w-0 flex-1 flex-col">
        <TopBar
          model={model}
          canClear={chat.messages.length > 0}
          onClear={chat.clear}
          onOpenMenu={() => setMenuOpen(true)}
        />
        {!aiKeySet && <AiKeyBanner />}
        <ChatWindow
          chat={chat}
          documents={documents}
          onAskAgain={(question) => setPrefill({ text: question })}
          onOpenMenu={() => setMenuOpen(true)}
        />
        <ChatInput
          disabled={noDocuments}
          disabledHint={hint}
          sending={chat.sending}
          onSend={chat.send}
          prefill={prefill}
        />
      </main>
      <Toast notice={documents.notice} onDone={documents.clearNotice} />
    </div>
  );
}
