// A short message that disappears by itself, e.g. "6 documents ready, 1 could not be read".

import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { useEffect } from "react";

const SHOW_MS = 4500;

export default function Toast({ notice, onDone }) {
  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(onDone, SHOW_MS);
    return () => clearTimeout(timer);
  }, [notice, onDone]);

  if (!notice) return null;
  const Icon = notice.tone === "warn" ? AlertTriangle : CheckCircle2;
  return (
    <div
      role="status"
      className="fixed bottom-24 left-1/2 z-40 flex -translate-x-1/2 animate-fade-in items-center gap-2 rounded-card bg-ink px-4 py-2.5 text-white shadow-lg"
    >
      <Icon
        size={16}
        className={notice.tone === "warn" ? "text-status-warn" : "text-brand-teal"}
        aria-hidden="true"
      />
      {notice.text}
    </div>
  );
}
