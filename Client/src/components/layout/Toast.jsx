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
      className="fixed inset-x-0 bottom-24 z-40 mx-auto flex w-fit animate-fade-in items-center gap-2 rounded-card bg-brand-navy px-4 py-2.5 text-white shadow-lg dark:shadow-none"
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
