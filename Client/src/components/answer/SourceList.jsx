// Teal source chips under each answer ("Contract_A.pdf · p. 14"). Clicking one shows its snippet.

import { FileText, Quote } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { shortLocation } from "../../utils/formatters";

export default function SourceList({ sources }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(null);
  const area = useRef(null);

  useEffect(() => {
    if (open === null) return undefined;
    const close = (event) => {
      if (event.key === "Escape" || (event.type === "mousedown" && !area.current?.contains(event.target)))
        setOpen(null);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  if (!sources.length) return null;
  const active = open !== null ? sources[open] : null;

  return (
    <div ref={area} className="space-y-2">
      <div className="flex flex-wrap gap-1.5" aria-label={t("answer.sources")}>
        {sources.map((source, index) => (
          <button
            key={`${source.document}-${source.location}-${index}`}
            onClick={() => setOpen(open === index ? null : index)}
            aria-expanded={open === index}
            className={`flex max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
              open === index
                ? "border-brand-teal bg-brand-teal text-on-teal"
                : "border-brand-teal/30 bg-brand-teal-soft text-brand-teal-dark hover:border-brand-teal"
            }`}
          >
            <FileText size={12} aria-hidden="true" className="shrink-0" />
            <span className="truncate">
              {source.document}
              {source.location && ` · ${shortLocation(source.location)}`}
            </span>
          </button>
        ))}
      </div>
      {active && (
        <div className="flex animate-fade-in gap-2 rounded-button border border-brand-teal/30 bg-brand-teal-soft/60 px-3 py-2 text-[13px]">
          <Quote size={14} className="mt-0.5 shrink-0 text-brand-teal" aria-hidden="true" />
          <p dir="auto" className="leading-relaxed text-ink">
            {active.snippet ||
              t("answer.seeSource", { document: active.document, location: active.location })}
          </p>
        </div>
      )}
    </div>
  );
}
