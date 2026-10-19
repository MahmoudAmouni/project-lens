// Welcome screen. Suggested questions match the loaded files (BOQ tables -> the cost question, etc.).

import { FolderOpen } from "lucide-react";
import Logo from "../layout/Logo";

function suggestions(documents) {
  const readable = documents.filter((document) => document.status === "ok");
  const hasTables = readable.some((document) => document.tables.length > 0);
  const hasText = readable.some((document) => document.pages > 0);
  const list = [];
  if (hasTables) list.push("List all cost items above SAR 1 million");
  if (hasText) list.push("Summarize the scope of work", "Extract all dates and deliverables");
  if (hasTables) list.push("What is the total of each BOQ?");
  return list.slice(0, 4);
}

export default function EmptyState({ documents, readableCount, loading, onAsk, onOpenMenu }) {
  if (readableCount === 0) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
        <Logo />
        <h2 className="text-lg font-semibold text-heading">
          {loading ? "Reading your documents…" : "Load your project documents"}
        </h2>
        <p className="leading-relaxed text-ink-quiet">
          {loading
            ? "This can take a minute the first time, while the search index is built."
            : "Enter a folder path in the sidebar, or drop PDF and Excel files there. Every answer will show its source file and page."}
        </p>
        <button
          onClick={onOpenMenu}
          className="flex items-center gap-2 rounded-button bg-brand-navy px-4 py-2 text-white lg:hidden"
        >
          <FolderOpen size={16} /> Open documents
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-5 py-14 text-center">
      <Logo />
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-heading">
          Ask anything about your {readableCount} document{readableCount === 1 ? "" : "s"}
        </h2>
        <p className="text-ink-quiet">
          Answers come only from your files, with the file and page for every fact.
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        {suggestions(documents).map((question) => (
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
