// The recent chat sent with each question, so follow-ups like "write those dates in Arabic" make sense.
// Each earlier answer goes with its table (first rows) and its sources, so the AI can reuse them exactly.

const HISTORY_MESSAGES = 6; // the Server also keeps only the last 6
const TABLE_ROWS = 15;

function tableText(table) {
  if (!table) return "";
  const lines = [table.columns, ...table.rows.slice(0, TABLE_ROWS)].map((row) =>
    row.map((cell) => cell ?? "").join(" | "),
  );
  const more = table.rows.length > TABLE_ROWS ? `\n(${table.rows.length - TABLE_ROWS} more rows)` : "";
  return `\n\n[Table:\n${lines.join("\n")}${more}]`;
}

function sourcesText(sources = []) {
  if (!sources.length) return "";
  return `\n\n[Sources: ${sources.map((source) => `${source.document} — ${source.location}`).join("; ")}]`;
}

/** Messages -> [{ role: "user" | "assistant", content }] for the Server. Errors and stops are left out. */
export function toHistory(messages) {
  return messages
    .filter((message) => message.role === "user" || message.role === "agent")
    .slice(-HISTORY_MESSAGES)
    .map((message) =>
      message.role === "user"
        ? { role: "user", content: message.text }
        : {
            role: "assistant",
            content: message.text + tableText(message.answer?.table) + sourcesText(message.answer?.sources),
          },
    );
}
