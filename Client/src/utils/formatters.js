// Small helpers for showing numbers, money, file sizes and tables.

const CURRENCY_IN_NAME = /\b(SAR|USD|EUR|AED|GBP|EGP)\b/i;
const AMOUNT_NAME = /amount|total|cost|price|value|sum/i;
const UTF8_BOM = String.fromCharCode(0xfeff); // lets Excel open the CSV as UTF-8 (Arabic text)
const NOT_AN_AMOUNT = /\b(rate|unit|qty|quantity|page|no\.?|number)\b|%/i;

export function formatNumber(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return value ?? "";
  return value.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

const ARABIC_CURRENCY = { SAR: "ر.س" };

/** "SAR 1,250,000" (Arabic screen: "ر.س 1,250,000") when the column name says the currency, else "1,250,000".
 * Digits stay Western in both languages, to match the numbers inside the documents. */
export function formatCell(value, column = "", language = "en") {
  if (typeof value !== "number") return value ?? "";
  const currency = column.match(CURRENCY_IN_NAME)?.[1]?.toUpperCase();
  if (!currency || !AMOUNT_NAME.test(column)) return formatNumber(value);
  const label = language === "ar" ? (ARABIC_CURRENCY[currency] ?? currency) : currency;
  return `${label} ${formatNumber(value)}`;
}

export function formatFileSize(megabytes) {
  if (!megabytes) return "";
  return megabytes < 1 ? `${Math.max(1, Math.round(megabytes * 1024))} KB` : `${megabytes.toFixed(1)} MB`;
}

export function isNumberColumn(rows, index) {
  const filled = rows.map((row) => row[index]).filter((value) => value !== null && value !== "");
  return filled.length > 0 && filled.every((value) => typeof value === "number");
}

/** Only money columns get a total; adding up rates or quantities means nothing. */
export function isSummableColumn(column, rows, index) {
  return isNumberColumn(rows, index) && AMOUNT_NAME.test(column) && !NOT_AN_AMOUNT.test(column);
}

export function sumColumn(rows, index) {
  return rows.reduce((total, row) => total + (typeof row[index] === "number" ? row[index] : 0), 0);
}

/** "page 3" -> "p. 3", so source chips stay short. */
export function shortLocation(location = "") {
  return location.replace(/\bpages?\s+/gi, "p. ").replace(/^Sheet\s+/i, "");
}

function csvCell(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function tableToCsv(columns, rows) {
  return [columns, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
}

/** Tab-separated, so pasting into Excel keeps the columns. */
export function tableToTsv(columns, rows) {
  return [columns, ...rows].map((row) => row.map((value) => value ?? "").join("\t")).join("\n");
}

export function downloadText(fileName, text, type = "text/csv") {
  const url = URL.createObjectURL(new Blob([UTF8_BOM + text], { type: `${type};charset=utf-8` }));
  const link = Object.assign(document.createElement("a"), { href: url, download: fileName });
  link.click();
  URL.revokeObjectURL(url);
}
