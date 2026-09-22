import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

// Every page used to repeat the same GET -> useState(null) -> useEffect ->
// setError(e.message) boilerplate. This is that pattern, written once.
// `path` is itself a dependency, so passing a template string like
// `/world/locations/${slug}` correctly refetches when `slug` changes.
export function useApi(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);

  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    if (!path) return undefined;
    let cancelled = false;
    setError("");
    api
      .get(path)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [path, version]);

  return { data, setData, error, setError, reload };
}
