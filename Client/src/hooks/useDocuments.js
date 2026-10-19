// Documents state: what is loaded, loading a folder or uploaded files, and progress while it reads.

import { useCallback, useEffect, useRef, useState } from "react";
import { getDocuments, getHealth, loadFolder, uploadFiles } from "../api/serverApi";
import i18n from "../i18n";

const EMPTY = { folder: null, documents: [], skipped: [], readable_count: 0, search_ready: false };
const PROGRESS_EVERY_MS = 700;
const START_RETRIES = 15;
const START_RETRY_MS = 2000;

export function useDocuments() {
  const [data, setData] = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null); // toast after a load: { text, tone }
  const poller = useRef(null);

  const watchProgress = useCallback(() => {
    clearInterval(poller.current);
    poller.current = setInterval(async () => {
      try {
        const health = await getHealth();
        if (health.loading_step) setProgress(health.loading_step);
      } catch {
        // progress is only a nicety; the load request itself reports errors
      }
    }, PROGRESS_EVERY_MS);
  }, []);

  const run = useCallback(
    async (action, startText) => {
      setLoading(true);
      setError(null);
      setProgress(startText);
      watchProgress();
      try {
        const result = await action();
        setData(result);
        setNotice(loadNotice(result));
        return true;
      } catch (err) {
        setError(err);
        return false;
      } finally {
        clearInterval(poller.current);
        setLoading(false);
        setProgress("");
      }
    },
    [watchProgress],
  );

  const load = useCallback((path) => run(() => loadFolder(path), i18n.t("progress.opening")), [run]);
  const upload = useCallback(
    (files) => run(() => uploadFiles(files), i18n.t("progress.uploading", { count: files.length })),
    [run],
  );

  // On start: show what the Server already has (it may still be reading DOCS_FOLDER from .env).
  useEffect(() => {
    let stopped = false;
    async function refresh(triesLeft) {
      try {
        const result = await getDocuments();
        if (stopped) return;
        setError(null);
        setData(result);
        if (result.loading) {
          setLoading(true);
          const health = await getHealth().catch(() => null);
          setProgress(health?.loading_step || i18n.t("progress.defaultFolder"));
          setTimeout(() => refresh(triesLeft), PROGRESS_EVERY_MS);
        } else {
          setLoading(false);
          setProgress("");
        }
      } catch (err) {
        if (stopped) return;
        // The Server may still be starting: try again for a while before showing the error.
        if (triesLeft > 0) setTimeout(() => refresh(triesLeft - 1), START_RETRY_MS);
        else setError(err);
      }
    }
    refresh(START_RETRIES);
    return () => {
      stopped = true;
      clearInterval(poller.current);
    };
  }, []);

  return { ...data, loading, progress, error, notice, clearNotice: () => setNotice(null), load, upload };
}

function loadNotice(result) {
  const ready = result.readable_count;
  const failed = result.documents.length - ready;
  const readyText = i18n.t("notice.ready", { count: ready });
  const text = failed ? i18n.t("notice.failed", { ready: readyText, count: failed }) : readyText;
  return { text, tone: failed ? "warn" : "ok" };
}
