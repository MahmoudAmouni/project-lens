// Table of result rows (e.g. BOQ items): sticky header, sortable columns, money formatted and end-aligned,
// a total row for money columns (only when every row comes from one file), "Show all", Export CSV and Copy.
// Subtotal / grand total lines from the file (table.total_rows) are shown in bold but never added into that total.

import { ArrowDown, ArrowUp, Check, Copy, Download } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  downloadText,
  formatCell,
  isNumberColumn,
  isSummableColumn,
  rowsFromOneFile,
  sumColumn,
  tableToCsv,
  tableToTsv,
} from "../../utils/formatters";

const FIRST_ROWS = 50;

function compare(a, b) {
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;
  return typeof a === "number" && typeof b === "number"
    ? a - b
    : String(a).localeCompare(String(b), undefined, { numeric: true });
}

const LONG_TEXT_CHARS = 30;

/** Drop columns that are empty in every row (common when rows from several BOQs are merged). */
function withoutEmptyColumns({ columns, rows }) {
  const keep = columns
    .map((_, index) => index)
    .filter((index) => rows.some((row) => row[index] != null && row[index] !== ""));
  return {
    columns: keep.map((index) => columns[index]),
    rows: rows.map((row) => keep.map((index) => row[index])),
  };
}

export default function ResultTable({ table }) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage;
  const { columns, rows } = useMemo(() => withoutEmptyColumns(table), [table]);
  const totalLines = useMemo(
    () => new Set((table.total_rows ?? []).map((index) => rows[index])),
    [table, rows],
  );
  const itemRows = useMemo(() => rows.filter((row) => !totalLines.has(row)), [rows, totalLines]);
  const longText = useMemo(
    () => columns.map((_, index) => rows.some((row) => String(row[index] ?? "").length > LONG_TEXT_CHARS)),
    [columns, rows],
  );
  const [sort, setSort] = useState(null); // { index, descending }
  const [showAll, setShowAll] = useState(false);
  const [copied, setCopied] = useState(false);

  const numeric = useMemo(() => columns.map((_, index) => isNumberColumn(rows, index)), [columns, rows]);
  const summable = useMemo(
    () =>
      columns.map((column, index) => rowsFromOneFile(columns, rows) && isSummableColumn(column, rows, index)),
    [columns, rows],
  );
  const sorted = useMemo(() => {
    if (!sort) return rows;
    const ordered = [...rows].sort((a, b) => compare(a[sort.index], b[sort.index]));
    return sort.descending ? ordered.reverse() : ordered;
  }, [rows, sort]);
  const shown = showAll ? sorted : sorted.slice(0, FIRST_ROWS);

  function toggleSort(index) {
    setSort((current) =>
      current?.index === index
        ? { index, descending: !current.descending }
        : { index, descending: numeric[index] },
    );
  }

  async function copy() {
    await navigator.clipboard.writeText(tableToTsv(columns, sorted));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="overflow-hidden rounded-card border border-line">
      <div className="max-h-[420px] overflow-auto">
        <table className="numbers w-full border-collapse text-[13px]">
          <thead className="sticky top-0 z-10 bg-page">
            <tr>
              {columns.map((column, index) => (
                <th
                  key={column}
                  className={`whitespace-nowrap border-b border-line px-3 py-2 font-semibold ${numeric[index] ? "text-end" : "text-start"}`}
                >
                  <button
                    onClick={() => toggleSort(index)}
                    className="inline-flex items-center gap-1 hover:text-brand-teal-dark"
                  >
                    {column}
                    {sort?.index === index &&
                      (sort.descending ? <ArrowDown size={12} /> : <ArrowUp size={12} />)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={`border-b border-line last:border-0 even:bg-row-alt hover:bg-page ${totalLines.has(row) ? "font-semibold" : ""}`}
              >
                {row.map((value, index) => (
                  <td
                    key={index}
                    dir="auto"
                    className={`px-3 py-1.5 ${longText[index] ? "min-w-[14rem]" : "whitespace-nowrap"} ${
                      numeric[index] ? "text-end" : ""
                    } ${columns[index] === "Source" ? "text-xs text-brand-teal-dark" : ""}`}
                  >
                    {formatCell(value, columns[index], language)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          {summable.some(Boolean) && (
            <tfoot className="sticky bottom-0 bg-page font-semibold">
              <tr>
                {columns.map((column, index) => (
                  <td
                    key={column}
                    className={`whitespace-nowrap border-t border-line px-3 py-2 ${numeric[index] ? "text-end" : ""}`}
                  >
                    {index === 0
                      ? t("table.total", { count: itemRows.length })
                      : summable[index]
                        ? formatCell(sumColumn(itemRows, index), column, language)
                        : ""}
                  </td>
                ))}
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      <div className="flex items-center gap-2 border-t border-line bg-surface px-3 py-2 text-xs text-ink-quiet">
        <span>
          {shown.length < sorted.length
            ? t("table.showing", { shown: shown.length, total: sorted.length })
            : t("table.rows", { count: sorted.length })}
        </span>
        {shown.length < sorted.length && (
          <button
            onClick={() => setShowAll(true)}
            className="font-medium text-brand-teal-dark hover:underline"
          >
            {t("table.showAll")}
          </button>
        )}
        <button
          onClick={copy}
          className="ms-auto flex items-center gap-1 rounded-button px-2 py-1 hover:bg-page hover:text-ink"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? t("answer.copied") : t("answer.copy")}
        </button>
        <button
          onClick={() => downloadText("projectlens-results.csv", tableToCsv(columns, sorted))}
          className="flex items-center gap-1 rounded-button px-2 py-1 hover:bg-page hover:text-ink"
        >
          <Download size={14} /> {t("table.exportCsv")}
        </button>
      </div>
    </div>
  );
}
