// Left panel: logo, folder loader, document list. A drawer on small screens.

import { X } from "lucide-react";
import DocumentList from "../documents/DocumentList";
import DropZone from "../documents/DropZone";
import FolderLoader from "../documents/FolderLoader";

export default function Sidebar({ documents, open, onClose }) {
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-20 bg-black/50 lg:hidden" onClick={onClose} aria-hidden="true" />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-[300px] flex-col gap-5 bg-brand-navy p-4 text-white transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-2.5 px-1">
          <img src="/logo-light.svg" alt="" className="h-8 w-8" />
          <span className="text-lg font-semibold tracking-tight">
            Project<span className="text-brand-teal">Lens</span>
          </span>
          <button
            onClick={onClose}
            className="ml-auto rounded-button p-1.5 hover:bg-brand-navy-light lg:hidden"
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        <div className="space-y-2">
          <FolderLoader
            folder={documents.folder}
            loading={documents.loading}
            error={documents.error}
            onLoad={documents.load}
          />
          <DropZone disabled={documents.loading} onFiles={documents.upload} />
        </div>

        <DocumentList
          documents={documents.documents}
          skipped={documents.skipped}
          loading={documents.loading}
          progress={documents.progress}
        />
      </aside>
    </>
  );
}
