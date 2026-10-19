// "Or drop files here": drag PDF/Excel files in, or click to choose them. Sends them to the upload endpoint.

import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

const ACCEPT = ".pdf,.xlsx,.xls,.xlsm";

export default function DropZone({ disabled, onFiles }) {
  const { t } = useTranslation();
  const [dragging, setDragging] = useState(false);
  const picker = useRef(null);

  function take(fileList) {
    const files = [...(fileList ?? [])];
    if (files.length && !disabled) onFiles(files);
  }

  function onDrop(event) {
    event.preventDefault();
    setDragging(false);
    take(event.dataTransfer.files);
  }

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => picker.current?.click()}
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
      <input
        ref={picker}
        type="file"
        multiple
        accept={ACCEPT}
        className="hidden"
        onChange={(event) => {
          take(event.target.files);
          event.target.value = "";
        }}
      />
    </button>
  );
}
