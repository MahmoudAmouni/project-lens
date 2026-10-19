// One file in the sidebar: icon, name, size or pages, and a status badge (icon + text, never color alone).

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

const STATUS = {
  ok: { label: "Ready", icon: CheckCircle2, className: "text-status-ok" },
  scanned: { label: "Scanned", icon: ScanLine, className: "text-status-warn" },
  too_large: { label: "Too large", icon: AlertTriangle, className: "text-status-warn" },
  empty: { label: "Empty", icon: CircleDashed, className: "text-status-warn" },
  encrypted: { label: "Locked", icon: Lock, className: "text-status-error" },
  corrupt: { label: "Corrupt", icon: XCircle, className: "text-status-error" },
};

function details(document) {
  if (document.status !== "ok") return document.message;
  if (document.file_type === "excel") {
    const sheets = document.tables.length;
    return `${sheets} sheet${sheets === 1 ? "" : "s"}`;
  }
  const tables = document.tables.length
    ? ` · ${document.tables.length} table${document.tables.length === 1 ? "" : "s"}`
    : "";
  return `${document.pages} p.${tables}`;
}

export default function DocumentItem({ document }) {
  const status = STATUS[document.status] ?? STATUS.corrupt;
  const FileIcon = document.file_type === "excel" ? FileSpreadsheet : FileText;
  const StatusIcon = status.icon;
  const readable = document.status === "ok";

  return (
    <li
      className="group flex items-start gap-2.5 rounded-button px-2 py-2 hover:bg-brand-navy-light"
      title={document.message || document.name}
    >
      <FileIcon
        size={18}
        strokeWidth={1.75}
        className={`mt-0.5 shrink-0 ${readable ? "text-white/80" : "text-white/40"}`}
      />
      <div className="min-w-0 flex-1">
        <p className={`truncate font-medium ${readable ? "text-white" : "text-white/60"}`}>{document.name}</p>
        <p className="truncate text-xs text-white/50">{details(document)}</p>
      </div>
      <span className={`mt-0.5 flex shrink-0 items-center gap-1 text-xs font-medium ${status.className}`}>
        <StatusIcon size={14} strokeWidth={2} aria-hidden="true" />
        {readable ? <span className="sr-only">{status.label}</span> : status.label}
      </span>
    </li>
  );
}
