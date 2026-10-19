// Shown where an answer would have been, after the user pressed Stop.

import { CircleStop, RefreshCw } from "lucide-react";

export default function StoppedMessage({ onAskAgain }) {
  return (
    <div className="flex animate-fade-in items-center gap-2 px-1 text-[13px] text-ink-quiet">
      <CircleStop size={15} aria-hidden="true" />
      <span>You stopped this answer.</span>
      <button
        onClick={onAskAgain}
        className="flex items-center gap-1 font-medium text-brand-teal-dark hover:underline"
      >
        <RefreshCw size={13} aria-hidden="true" /> Ask again
      </button>
    </div>
  );
}
