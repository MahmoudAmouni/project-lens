// Side panel: logo, folder loader, document list. A drawer on small screens.
// Uses start/end, so in Arabic it sits on the right and slides in from the right.

import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import DocumentList from "../documents/DocumentList";
import DropZone from "../documents/DropZone";
import FolderLoader from "../documents/FolderLoader";

/** The app name, with its accent word in teal: "Project<Lens>" or "<عدسة> المشروع". */
function AppName() {
  const { t } = useTranslation();
  const [before, after] = t("app.name").split(t("app.nameAccent"));
  return (
    <span className="text-lg font-semibold tracking-tight">
      {before}
      <span className="text-brand-teal">{t("app.nameAccent")}</span>
      {after}
    </span>
  );
}

export default function Sidebar({ documents, open, onClose }) {
  const { t } = useTranslation();
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-20 bg-black/50 lg:hidden" onClick={onClose} aria-hidden="true" />
      )}
      <aside
        className={`fixed inset-y-0 start-0 z-30 flex w-[300px] flex-col gap-5 bg-brand-navy p-4 text-white transition-transform lg:static lg:translate-x-0 lg:rtl:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full rtl:translate-x-full"
        }`}
      >
        <div className="flex items-center gap-2.5 px-1">
          <img src="/logo-light.svg" alt="" className="h-8 w-8" />
          <AppName />
          <button
            onClick={onClose}
            className="ms-auto rounded-button p-1.5 hover:bg-brand-navy-light lg:hidden"
            aria-label={t("sidebar.closeMenu")}
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
