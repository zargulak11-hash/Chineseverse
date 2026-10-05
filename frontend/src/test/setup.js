import { beforeEach, vi } from "vitest";

// A real, per-test localStorage (Node has none): api.js keeps the session in it.
class MemoryStorage {
  constructor() {
    this.items = new Map();
  }
  getItem(key) {
    return this.items.has(key) ? this.items.get(key) : null;
  }
  setItem(key, value) {
    this.items.set(key, String(value));
  }
  removeItem(key) {
    this.items.delete(key);
  }
  clear() {
    this.items.clear();
  }
}

beforeEach(() => {
  globalThis.localStorage = new MemoryStorage();
  globalThis.fetch = vi.fn();
});
