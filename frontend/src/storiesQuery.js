// The library request for the Stories page (GET /stories, services/stories.py):
// the URL's filters become server-side filters, and the page asks for
// `pages` pages of cards. Until the learner's level is known (`ready`), a
// one-card request is enough to learn it.
export const PAGE = 12;

export function libraryPath({ ready, level, pages = 1, status = "all", topic = "all", time = "any", q = "" }) {
  const query = new URLSearchParams({ limit: ready ? String(PAGE * pages) : "1" });
  if (ready) query.set("level", String(level));
  if (status !== "all") query.set("status", status);
  if (topic !== "all") query.set("topic", topic);
  if (time !== "any") query.set("length", time);
  if (q) query.set("q", q);
  return `/stories?${query}`;
}
