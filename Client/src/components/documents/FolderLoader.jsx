// Folder path input with a Load button, and the error when loading fails.

import { FolderOpen, Loader2 } from "lucide-react";
import { useState } from "react";

export default function FolderLoader({ folder, loading, error, onLoad }) {
  const [path, setPath] = useState("");

  function submit(event) {
    event.preventDefault();
    if (path.trim() && !loading) onLoad(path.trim());
  }

  return (
    <form onSubmit={submit} className="space-y-2">
      <label
        htmlFor="folder-path"
        className="block px-0.5 text-xs font-semibold uppercase tracking-wide text-white/50"
      >
        Folder
      </label>
      <div className="flex gap-2">
        <input
          id="folder-path"
          value={path}
          onChange={(event) => setPath(event.target.value)}
          placeholder={folder ?? "C:/docs/tender"}
          className="min-w-0 flex-1 rounded-button border border-white/15 bg-brand-navy-dark px-3 py-2 text-white placeholder:text-white/35 focus:border-brand-teal"
          spellCheck="false"
        />
        <button
          type="submit"
          disabled={loading || !path.trim()}
          className="flex items-center gap-1.5 rounded-button bg-brand-teal px-3 py-2 font-medium text-white hover:bg-brand-teal-dark disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          ) : (
            <FolderOpen size={16} aria-hidden="true" />
          )}
          Load
        </button>
      </div>
      {error && (
        <p
          className="rounded-button bg-status-error/25 px-3 py-2 text-xs leading-relaxed text-white"
          role="alert"
        >
          {error.message}
        </p>
      )}
    </form>
  );
}
