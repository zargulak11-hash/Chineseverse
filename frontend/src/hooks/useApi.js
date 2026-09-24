import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api.js";

// Every page used to repeat the same GET -> useState(null) -> useEffect ->
// setError(e.message) boilerplate. This is that pattern, written once.
// `path` is itself a dependency, so passing a template string like
// `/world/locations/${slug}` correctly refetches when `slug` changes.
//
// i18n.language is also a dependency: api.js sends the current language as
// X-Locale on every request so the backend can localize DB-driven content
// (lessons, vocab meanings, missions, ...), but that only helps if the
// request is actually re-sent when the user switches language — otherwise
// the page keeps showing whatever locale it happened to load in. Doing it
// here once covers every page built on useApi instead of repeating a
// language-change effect in each one.
export function useApi(path) {
  const { i18n } = useTranslation();
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
  }, [path, version, i18n.language]);

  return { data, setData, error, setError, reload };
}
