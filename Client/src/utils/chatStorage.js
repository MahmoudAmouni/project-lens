// Keeps the chat in this browser, so a page reload does not lose it. "Clear" empties it.

const STORAGE_KEY = "projectlens-chat";
const MAX_SAVED_MESSAGES = 60;

/** Only finished messages are kept (no error or stopped cards). */
export function loadChat() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(saved) ? saved.filter((m) => m.role === "user" || m.role === "agent") : [];
  } catch {
    return []; // blocked or broken storage: start with an empty chat
  }
}

export function saveChat(messages) {
  try {
    const kept = messages.filter((m) => m.role === "user" || m.role === "agent").slice(-MAX_SAVED_MESSAGES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(kept));
  } catch {
    // full or blocked storage: the chat just won't survive a reload
  }
}
