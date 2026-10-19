// Picks the AI model for the next questions and shows how much of each model's free limit is left today.

import { Check, ChevronDown, Cpu, RefreshCw } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatNumber } from "../../utils/formatters";

/** "openai/gpt-oss-120b" -> "gpt-oss-120b" */
const shortName = (name = "") => name.split("/").pop();

/** Gemini's free tier limits requests per day, not tokens: the Server sends no daily token limit for it. */
const countsRequests = (model) => model?.daily_token_limit == null;
const leftToday = (model) => (countsRequests(model) ? model.requests_left_today : model.tokens_left_today);

function percentLeft(model) {
  const limit = countsRequests(model) ? model?.daily_request_limit : model?.daily_token_limit;
  if (!limit || leftToday(model) == null) return 100;
  return Math.round((100 * leftToday(model)) / limit);
}

function barColor(model) {
  if (model.limited_for_seconds > 0 || leftToday(model) === 0) return "bg-status-error";
  return percentLeft(model) < 15 ? "bg-status-warn" : "bg-brand-teal";
}

function ModelOption({ model, selected, onPick }) {
  const { t } = useTranslation();
  return (
    <li>
      <button
        onClick={() => onPick(model.name)}
        className={`w-full rounded-button px-2.5 py-2 text-start hover:bg-page ${selected ? "bg-page" : ""}`}
        role="option"
        aria-selected={selected}
      >
        <span className="flex items-center gap-2 text-sm font-medium text-ink">
          <span dir="ltr">{shortName(model.name)}</span>
          {selected && <Check size={14} className="ms-auto text-brand-teal" />}
        </span>
        <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-line">
          <span className={`block h-full ${barColor(model)}`} style={{ width: `${percentLeft(model)}%` }} />
        </span>
        {countsRequests(model) ? (
          <span className="mt-1 block text-xs text-ink-quiet">
            {model.requests_left_today != null &&
              `${t("models.requestsLeftOf", {
                left: formatNumber(model.requests_left_today),
                limit: formatNumber(model.daily_request_limit),
              })} · `}
            {t("models.tokensUsed", { count: model.tokens_used_today })}
          </span>
        ) : (
          <span className="mt-1 block text-xs text-ink-quiet">
            {t("models.tokensLeft", {
              left: formatNumber(model.tokens_left_today),
              limit: formatNumber(model.daily_token_limit),
            })}
          </span>
        )}
        {!countsRequests(model) && model.requests_left_today != null && (
          <span className="block text-xs text-ink-quiet">
            {t("models.requestsLeft", { count: model.requests_left_today })}
            {model.tokens_left_this_minute != null &&
              ` · ${t("models.minuteLeft", { count: model.tokens_left_this_minute })}`}
          </span>
        )}
        {model.limited_for_seconds > 0 && (
          <span className="block text-xs text-status-error">
            {t("models.limited", { minutes: Math.max(1, Math.ceil(model.limited_for_seconds / 60)) })}
          </span>
        )}
      </button>
    </li>
  );
}

export default function ModelPicker({ models, current, onPick, onRefresh, checking }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const box = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const closeOutside = (event) => !box.current?.contains(event.target) && setOpen(false);
    const closeOnEscape = (event) => event.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", closeOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  if (models.length === 0) return null;
  const selected = models.find((model) => model.name === current) ?? models[0];

  return (
    <div className="relative" ref={box}>
      <button
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-1.5 rounded-full bg-page px-2.5 py-1 text-xs text-ink-quiet hover:text-ink"
        aria-haspopup="listbox"
        aria-expanded={open}
        title={t("models.pick")}
      >
        <Cpu size={14} />
        <span dir="ltr" className="hidden sm:inline">
          {shortName(selected.name)}
        </span>
        <span className="hidden sm:inline">
          · {t("models.percentLeft", { percent: percentLeft(selected) })}
        </span>
        <ChevronDown size={14} />
      </button>

      {open && (
        <div className="absolute end-0 top-full z-40 mt-2 w-72 animate-fade-in rounded-card border border-line bg-surface p-2 shadow-lg">
          <div className="flex items-center px-2.5 pb-1.5 pt-1">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
              {t("models.title")}
            </h2>
            <button
              onClick={() => onRefresh(true)}
              disabled={checking}
              className="ms-auto rounded-button p-1 text-ink-quiet hover:bg-page hover:text-ink disabled:opacity-50"
              aria-label={t("models.refresh")}
              title={t("models.refresh")}
            >
              <RefreshCw size={14} className={checking ? "animate-spin" : ""} />
            </button>
          </div>
          <ul role="listbox" aria-label={t("models.title")} className="space-y-0.5">
            {models.map((model) => (
              <ModelOption
                key={model.name}
                model={model}
                selected={model.name === selected.name}
                onPick={(name) => {
                  onPick(name);
                  setOpen(false);
                }}
              />
            ))}
          </ul>
          <p className="px-2.5 pb-1 pt-2 text-xs leading-relaxed text-ink-quiet">{t("models.note")}</p>
        </div>
      )}
    </div>
  );
}
