// "Or drop files here": drag PDF/Excel files or whole folders in, or choose files or a folder. Sends them to the upload endpoint.

import { FolderUp, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { filesFromDrop, filesFromList } from "../../utils/droppedFiles";

const ACCEPT = ".pdf,.xlsx,.xls,.xlsm";

export default function DropZone({ disabled, onFiles }) {
  const { t } = useTranslation();
  const [dragging, setDragging] = useState(false);
  const [nothingFound, setNothingFound] = useState(false);
  const filePicker = useRef(null);
  const folderPicker = useRef(null);

  function take(files) {
    if (disabled) return;
    setNothingFound(!files.length);
    if (files.length) onFiles(files);
  }

  async function onDrop(event) {
    event.preventDefault();
    setDragging(false);
    take(await filesFromDrop(event.dataTransfer));
  }

  function onPicked(event) {
    take(filesFromList(event.target.files));
    event.target.value = "";
  }

  return (
    <div className="space-y-1.5">
      <button
        type="button"
        disabled={disabled}
        onClick={() => filePicker.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex w-full items-center justify-center gap-2 rounded-button border border-dashed px-3 py-3 text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
          dragging
            ? "border-brand-teal bg-brand-teal/15 text-white"
            : "border-white/25 text-white/60 hover:border-white/50 hover:text-white"
        }`}
      >
        <UploadCloud size={16} aria-hidden="true" />
        {dragging ? t("sidebar.dropNow") : t("sidebar.drop")}
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={() => folderPicker.current?.click()}
        className="flex w-full items-center justify-center gap-1.5 text-xs text-white/60 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        <FolderUp size={14} aria-hidden="true" />
        {t("sidebar.chooseFolder")}
      </button>
      {nothingFound && (
        <p className="text-center text-xs text-white/60" role="status">
          {t("sidebar.noSupportedFiles")}
        </p>
      )}
      <input ref={filePicker} type="file" multiple accept={ACCEPT} className="hidden" onChange={onPicked} />
      <input ref={folderPicker} type="file" webkitdirectory="" className="hidden" onChange={onPicked} />
    </div>
  );
}
