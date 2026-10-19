// "How I found this": the tool steps the agent took, collapsed by default.

import { ChevronRight, Wrench } from "lucide-react";
import { useState } from "react";

export default function ToolSteps({ steps }) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;

  return (
    <div className="text-xs text-ink-quiet">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center gap-1 hover:text-ink"
      >
        <ChevronRight
          size={14}
          className={`transition-transform ${open ? "rotate-90" : ""}`}
          aria-hidden="true"
        />
        How I found this ({steps.length} step{steps.length === 1 ? "" : "s"})
      </button>
      {open && (
        <ol className="mt-2 animate-fade-in space-y-1 border-l-2 border-line pl-4">
          {steps.map((step, index) => (
            <li key={index} className="flex gap-2">
              <Wrench size={12} className="mt-0.5 shrink-0 text-brand-teal" aria-hidden="true" />
              <span>{step}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
