// Shown when the Server has no Groq key, so the user knows why questions cannot be answered yet.

import { KeyRound } from "lucide-react";

export default function AiKeyBanner() {
  return (
    <div
      role="alert"
      className="flex items-center gap-2 border-b border-status-warn/30 bg-status-warn/10 px-4 py-2 text-[13px] text-ink"
    >
      <KeyRound size={16} className="shrink-0 text-status-warn" aria-hidden="true" />
      <span>
        The AI is not set up: add your <code className="font-semibold">GROQ_API_KEY</code> to the{" "}
        <code className="font-semibold">.env</code> file, then restart the server.
      </span>
    </div>
  );
}
