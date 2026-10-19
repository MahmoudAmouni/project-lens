// The loaded files, skeleton rows while a folder is read, and a note about skipped files.

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

function skippedSummary(skipped) {
  const types = [...new Set(skipped.map((file) => file.name.split(".").pop().toLowerCase()))];
  return `${skipped.length} file${skipped.length === 1 ? "" : "s"} skipped (.${types.slice(0, 3).join(", .")})`;
}

export default function DocumentList({ documents, skipped, loading, progress }) {
  return (
    <section className="flex min-h-0 flex-1 flex-col" aria-label="Documents">
      <h2 className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-white/50">
        Documents {documents.length > 0 && `(${documents.length})`}
      </h2>

      {loading && (
        <p className="truncate px-2 pb-2 text-xs text-brand-teal" role="status" aria-live="polite">
          {progress || "Reading files…"}
        </p>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        {loading && documents.length === 0 ? (
          <SkeletonRows />
        ) : documents.length === 0 ? (
          <p className="px-2 py-3 text-xs leading-relaxed text-white/50">
            No documents yet. Enter a folder path above, or drop PDF and Excel files here.
          </p>
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
          {skippedSummary(skipped)}
        </p>
      )}
    </section>
  );
}
