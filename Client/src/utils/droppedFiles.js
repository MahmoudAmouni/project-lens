// Turn dropped items or a chosen folder into a flat list of PDF/Excel/Word files, walking into subfolders.

const SUPPORTED = /\.(pdf|xlsx|xls|xlsm|docx)$/i;

// Hidden files (".DS_Store") and Office lock files ("~$Book.xlsx") are left out, like the Server does.
function isWanted(name) {
  return SUPPORTED.test(name) && !name.startsWith(".") && !name.startsWith("~$");
}

function fileFromEntry(entry) {
  return new Promise((resolve) => entry.file(resolve, () => resolve(null)));
}

// readEntries returns at most ~100 entries per call, so keep reading until it returns none.
async function readAllEntries(directory) {
  const reader = directory.createReader();
  const entries = [];
  for (;;) {
    const batch = await new Promise((resolve) => reader.readEntries(resolve, () => resolve([])));
    if (!batch.length) return entries;
    entries.push(...batch);
  }
}

async function filesFromEntry(entry) {
  if (entry.name.startsWith(".")) return [];
  if (entry.isFile) {
    const file = await fileFromEntry(entry);
    return file && isWanted(file.name) ? [file] : [];
  }
  const children = await readAllEntries(entry);
  const nested = await Promise.all(children.map(filesFromEntry));
  return nested.flat();
}

/** Files from a drop: plain files and whole folders. */
export async function filesFromDrop(dataTransfer) {
  const entries = [...(dataTransfer.items ?? [])].map((item) => item.webkitGetAsEntry?.()).filter(Boolean);
  if (!entries.length) return filesFromList(dataTransfer.files);
  const nested = await Promise.all(entries.map(filesFromEntry));
  return nested.flat();
}

/** Files from a file input (also a folder input, where hidden subfolders are skipped). */
export function filesFromList(fileList) {
  return [...(fileList ?? [])].filter(
    (file) =>
      isWanted(file.name) && !(file.webkitRelativePath ?? "").split("/").some((part) => part.startsWith(".")),
  );
}
