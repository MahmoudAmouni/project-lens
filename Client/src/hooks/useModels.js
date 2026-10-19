// The AI models the user can pick, with how much of their free Groq limit is left.
// The pick is kept in the browser; the numbers are fetched again after every answer.

import { useCallback, useEffect, useState } from "react";
import { getModels } from "../api/serverApi";

const STORAGE_KEY = "projectlens-model";

function savedModel() {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return ""; // blocked storage: use the Server's default model
  }
}

/** Models look like: { name, tokens_left_today, daily_token_limit, requests_left_today, ..., limited_for_seconds } */
export function useModels() {
  const [models, setModels] = useState([]);
  const [picked, setPicked] = useState(savedModel);
  const [checking, setChecking] = useState(false);

  const reload = useCallback(async (refresh = false) => {
    setChecking(refresh);
    try {
      setModels((await getModels(refresh)).models);
    } catch {
      // no key or no Server yet: the picker stays hidden or shows the last numbers
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    reload(true);
  }, [reload]);

  const pick = useCallback((name) => {
    setPicked(name);
    try {
      localStorage.setItem(STORAGE_KEY, name);
    } catch {
      // the pick just won't survive a reload
    }
  }, []);

  // A saved pick that is no longer in .env falls back to the first (default) model.
  const current = models.some((model) => model.name === picked) ? picked : (models[0]?.name ?? "");
  return { models, current, pick, reload, checking };
}
