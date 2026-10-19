// Shown while the agent works: animated dots, rotating labels and the seconds waited (answers can take a while).

import { useEffect, useState } from "react";

const LABELS = [
  "Reading the question",
  "Searching documents",
  "Reading tables",
  "Checking the numbers",
  "Writing the answer",
];
const LABEL_EVERY_SECONDS = 3;
const SLOW_AFTER_SECONDS = 25;

export default function ThinkingIndicator() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const label = LABELS[Math.min(Math.floor(seconds / LABEL_EVERY_SECONDS), LABELS.length - 1)];
  return (
    <div
      className="flex animate-fade-in items-center gap-3 rounded-card border border-line bg-surface px-4 py-3"
      role="status"
    >
      <span className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="h-2 w-2 animate-dot-pulse rounded-full bg-brand-teal"
            style={{ animationDelay: `${dot * 0.2}s` }}
          />
        ))}
      </span>
      <span className="text-ink-quiet">{label}…</span>
      <span className="numbers ml-auto text-xs text-ink-quiet/70">
        {seconds}s{seconds >= SLOW_AFTER_SECONDS && " · free AI tier, waiting for its rate limit"}
      </span>
    </div>
  );
}
