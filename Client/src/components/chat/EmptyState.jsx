// Welcome screen. Suggested questions match the loaded files (BOQ tables -> the cost question, etc.).

import { FolderOpen } from "lucide-react";
import { useTranslation } from "react-i18next";
import Logo from "../layout/Logo";

function suggestions(t, documents) {
  const readable = documents.filter((document) => document.status === "ok");
  const hasTables = readable.some((document) => document.tables.length > 0);
  const hasText = readable.some((document) => document.pages > 0);
  const list = [];
  if (hasTables) list.push(t("suggestions.cost"));
  if (hasText) list.push(t("suggestions.scope"), t("suggestions.dates"));
  if (hasTables) list.push(t("suggestions.totals"));
  return list.slice(0, 4);
}

export default function EmptyState({ documents, readableCount, loading, onAsk, onOpenMenu }) {
  const { t } = useTranslation();
  if (readableCount === 0) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
        <Logo />
        <h2 className="text-lg font-semibold text-heading">
          {loading ? t("empty.loadingTitle") : t("empty.loadTitle")}
        </h2>
        <p className="leading-relaxed text-ink-quiet">
          {loading ? t("empty.loadingText") : t("empty.loadText")}
        </p>
        <button
          onClick={onOpenMenu}
          className="flex items-center gap-2 rounded-button bg-brand-navy px-4 py-2 text-white lg:hidden"
        >
          <FolderOpen size={16} /> {t("empty.openDocuments")}
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-5 py-14 text-center">
      <Logo />
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-heading">
          {t("empty.askTitle", { count: readableCount })}
        </h2>
        <p className="text-ink-quiet">{t("empty.subtitle")}</p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {suggestions(t, documents).map((question) => (
          <button
            key={question}
            onClick={() => onAsk(question)}
            className="rounded-full border border-line bg-surface px-4 py-2 text-ink hover:border-brand-teal hover:text-brand-teal-dark"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
