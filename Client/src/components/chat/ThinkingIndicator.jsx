// Shown while the agent works: animated dots, rotating labels and the seconds waited (answers can take a while).

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const LABELS = ["thinking.step1", "thinking.step2", "thinking.step3", "thinking.step4", "thinking.step5"];
const LABEL_EVERY_SECONDS = 3;
const SLOW_AFTER_SECONDS = 25;

export default function ThinkingIndicator() {
  const { t } = useTranslation();
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const label = t(LABELS[Math.min(Math.floor(seconds / LABEL_EVERY_SECONDS), LABELS.length - 1)]);
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
      <span className="numbers ms-auto text-xs text-ink-quiet/70">
        {seconds}s{seconds >= SLOW_AFTER_SECONDS && ` · ${t("thinking.slow")}`}
      </span>
    </div>
  );
}
