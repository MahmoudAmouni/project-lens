// The loaded files, skeleton rows while a folder is read, and a note about skipped files.

import { useTranslation } from "react-i18next";
import DocumentItem from "./DocumentItem";

function SkeletonRows() {
  return (
    <ul className="space-y-1" aria-hidden="true">
      {[70, 55, 80, 60].map((width) => (
        <li key={width} className="flex items-center gap-2.5 px-2 py-2.5">
          <span className="h-4 w-4 animate-pulse rounded bg-white/15" />
          <span className="h-3 animate-pulse rounded bg-white/15" style={{ width: `${width}%` }} />
        </li>
      ))}
    </ul>
  );
}

function fileTypes(skipped) {
  const types = [...new Set(skipped.map((file) => file.name.split(".").pop().toLowerCase()))];
  return `.${types.slice(0, 3).join(", .")}`;
}

/** The Server reports progress as "Reading BOQ.xlsx" or "Building the search index"; shown in the screen language. */
function progressText(t, progress) {
  if (!progress) return t("progress.reading");
  if (progress.startsWith("Reading ") && !progress.endsWith("…")) {
    return t("progress.readingFile", { name: progress.slice(8) });
  }
  if (progress.startsWith("Building")) return t("progress.indexing");
  return progress;
}

export default function DocumentList({ documents, skipped, loading, progress }) {
  const { t } = useTranslation();
  return (
    <section className="flex min-h-0 flex-1 flex-col" aria-label={t("sidebar.documents")}>
      <h2 className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-white/50">
        {t("sidebar.documents")} {documents.length > 0 && `(${documents.length})`}
      </h2>

      {loading && (
        <p className="truncate px-2 pb-2 text-xs text-brand-teal" role="status" aria-live="polite">
          {progressText(t, progress)}
        </p>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto pe-1">
        {loading && documents.length === 0 ? (
          <SkeletonRows />
        ) : documents.length === 0 ? (
          <p className="px-2 py-3 text-xs leading-relaxed text-white/50">{t("sidebar.noDocuments")}</p>
        ) : (
          <ul className={`space-y-0.5 ${loading ? "opacity-50" : ""}`}>
            {documents.map((document) => (
              <DocumentItem key={document.name} document={document} />
            ))}
          </ul>
        )}
      </div>

      {skipped.length > 0 && (
        <p
          className="truncate px-2 pt-2 text-xs text-white/50"
          title={skipped.map((f) => `${f.name}: ${f.reason}`).join("\n")}
        >
          {t("sidebar.skipped", { count: skipped.length, types: fileTypes(skipped) })}
        </p>
      )}
    </section>
  );
}
