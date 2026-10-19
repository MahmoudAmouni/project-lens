// One file in the sidebar: icon, name, pages or sheets, and a status badge (icon + text, never color alone).

import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  FileSpreadsheet,
  FileText,
  Lock,
  ScanLine,
  XCircle,
} from "lucide-react";
import { useTranslation } from "react-i18next";

const STATUS = {
  ok: { icon: CheckCircle2, className: "text-status-ok" },
  scanned: { icon: ScanLine, className: "text-status-warn" },
  too_large: { icon: AlertTriangle, className: "text-status-warn" },
  empty: { icon: CircleDashed, className: "text-status-warn" },
  encrypted: { icon: Lock, className: "text-status-error" },
  corrupt: { icon: XCircle, className: "text-status-error" },
};

function details(t, document) {
  if (document.status !== "ok")
    return t(`statusReason.${document.status}`, { defaultValue: document.message });
  if (document.file_type === "excel") return t("document.sheets", { count: document.tables.length });
  const tables = document.tables.length
    ? ` · ${t("document.tables", { count: document.tables.length })}`
    : "";
  return t("document.pages", { count: document.pages }) + tables;
}

export default function DocumentItem({ document }) {
  const { t } = useTranslation();
  const statusName = STATUS[document.status] ? document.status : "corrupt";
  const status = STATUS[statusName];
  const FileIcon = document.file_type === "excel" ? FileSpreadsheet : FileText;
  const StatusIcon = status.icon;
  const readable = document.status === "ok";
  const label = t(`status.${statusName}`);
  const detail = details(t, document);

  return (
    <li
      className="group flex items-start gap-2.5 rounded-button px-2 py-2 hover:bg-brand-navy-light"
      title={readable ? document.name : detail}
    >
      <FileIcon
        size={18}
        strokeWidth={1.75}
        className={`mt-0.5 shrink-0 ${readable ? "text-white/80" : "text-white/40"}`}
      />
      <div className="min-w-0 flex-1">
        <p className={`truncate font-medium ${readable ? "text-white" : "text-white/60"}`}>
          <bdi>{document.name}</bdi>
        </p>
        <p className="truncate text-xs text-white/50">{detail}</p>
      </div>
      <span className={`mt-0.5 flex shrink-0 items-center gap-1 text-xs font-medium ${status.className}`}>
        <StatusIcon size={14} strokeWidth={2} aria-hidden="true" />
        {readable ? <span className="sr-only">{label}</span> : label}
      </span>
    </li>
  );
}
