// "How I found this": the tool steps the agent took, collapsed by default.

import { ChevronRight, Wrench } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export default function ToolSteps({ steps }) {
  const { t } = useTranslation();
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
          className={`transition-transform ${open ? "rotate-90" : "rtl:rotate-180"}`}
          aria-hidden="true"
        />
        {t("answer.howFound", { count: steps.length })}
      </button>
      {open && (
        <ol className="mt-2 animate-fade-in space-y-1 border-s-2 border-line ps-4">
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
