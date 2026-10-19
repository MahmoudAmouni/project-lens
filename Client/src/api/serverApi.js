// All calls to the Server live here. Every failure becomes a ServerError with a code and a plain message.

export class ServerError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

function unreachable() {
  return new ServerError(
    "SERVER_UNREACHABLE",
    "The server is not running. Start it with scripts/start, then try again.",
  );
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, options);
  } catch (err) {
    if (err.name === "AbortError") throw new ServerError("STOPPED", "Stopped."); // the user pressed Stop
    throw unreachable();
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error;
    if (!error && response.status >= 500) throw unreachable(); // the dev proxy answers 500 when the Server is down
    throw new ServerError(
      error?.code ?? "INTERNAL_ERROR",
      error?.message ?? `The server answered ${response.status}.`,
    );
  }
  return body;
}

function postJson(path, data, signal) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    signal,
  });
}

export function getHealth() {
  return request("/health");
}

export function getDocuments() {
  return request("/documents");
}

export function loadFolder(folderPath) {
  return postJson("/documents/load", { folder_path: folderPath });
}

export function uploadFiles(files) {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return request("/documents/upload", { method: "POST", body: form });
}

/** `signal` (from an AbortController) cancels the question: the Server stops the agent when it sees that. */
export function askQuestion(question, history, uiLanguage, signal) {
  return postJson("/chat", { question, history, ui_language: uiLanguage }, signal);
}
