import { beforeEach, describe, expect, it } from "vitest";
import { api, clearSession, getSavedUser, getToken, login, saveToken, saveUser } from "./api.js";
import i18n from "./i18n.js";
import ru from "./locales/ru.json";

// A fetch Response stand-in with just what api.js reads.
function respond(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => {
      if (body === undefined) throw new SyntaxError("no body");
      return body;
    },
  };
}

function lastCall() {
  const [url, options] = fetch.mock.calls.at(-1);
  return { url, options };
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
});

describe("every request", () => {
  it("goes to the same-origin /api path and carries the session token and the UI language", async () => {
    saveToken("tok-123");
    await i18n.changeLanguage("ru");
    fetch.mockResolvedValue(respond(200, { ok: 1 }));
    expect(await api.get("/me")).toEqual({ ok: 1 });
    const { url, options } = lastCall();
    expect(url).toBe("/api/me");
    expect(options.method).toBe("GET");
    expect(options.headers.Authorization).toBe("Bearer tok-123");
    expect(options.headers["X-Locale"]).toBe("ru");
  });

  it("sends no Authorization header when signed out", async () => {
    fetch.mockResolvedValue(respond(200, []));
    await api.get("/animals");
    expect(lastCall().options.headers.Authorization).toBeUndefined();
  });

  it("JSON-encodes a body with the right content type", async () => {
    fetch.mockResolvedValue(respond(201, { id: 7 }));
    await api.post("/duels", { opponent_id: 3 });
    const { options } = lastCall();
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(options.body)).toEqual({ opponent_id: 3 });
  });

  it("treats 204 No Content as null", async () => {
    fetch.mockResolvedValue(respond(204));
    expect(await api.del("/me/avatar")).toBeNull();
  });
});

describe("errors", () => {
  it("shows the server's detail in the learner's language and keeps status, code and body", async () => {
    await i18n.changeLanguage("ru");
    fetch.mockResolvedValue(respond(409, { detail: "Quest already claimed", code: "x_code", extra: 1 }));
    const err = await api.post("/quests/1/claim").catch((e) => e);
    expect(err.message).toBe(ru.apiErrors.questClaimed);
    expect(err.status).toBe(409);
    expect(err.code).toBe("x_code");
    expect(err.data.extra).toBe(1);
  });

  it("an expired session (401) signs the learner out", async () => {
    saveToken("old");
    saveUser({ id: 1 });
    fetch.mockResolvedValue(respond(401, { detail: "Invalid or expired token" }));
    await expect(api.get("/me")).rejects.toThrow();
    expect(getToken()).toBeNull();
    expect(getSavedUser()).toBeNull();
  });

  it("a 403 does not sign the learner out", async () => {
    saveToken("still-valid");
    fetch.mockResolvedValue(respond(403, { detail: "Admin access required" }));
    await expect(api.get("/admin/users")).rejects.toThrow("Admin access required");
    expect(getToken()).toBe("still-valid");
  });

  it("the login lockout is shown translated", async () => {
    await i18n.changeLanguage("ru");
    fetch.mockResolvedValue(respond(429, { detail: "Too many sign-in attempts. Please wait a few minutes and try again." }));
    await expect(login({ username: "a", password: "b" })).rejects.toThrow(ru.apiErrors.loginLocked);
    expect(getToken()).toBeNull();
  });
});

describe("sign-in", () => {
  it("stores the token and user from a successful login", async () => {
    fetch.mockResolvedValue(respond(200, { access_token: "new-token", user: { id: 5, username: "zarina" } }));
    expect(await login({ username: "zarina", password: "secret1" })).toEqual({ id: 5, username: "zarina" });
    expect(getToken()).toBe("new-token");
    expect(getSavedUser()).toEqual({ id: 5, username: "zarina" });
    clearSession();
    expect(getToken()).toBeNull();
  });
});

describe("uploads", () => {
  it("send multipart form data with the session headers, and a 401 signs out", async () => {
    saveToken("tok");
    fetch.mockResolvedValue(respond(401, { detail: "Not authenticated" }));
    await expect(api.upload("/me/avatar", new Blob(["x"]))).rejects.toThrow();
    const { options } = lastCall();
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.headers.Authorization).toBe("Bearer tok");
    expect(options.headers["Content-Type"]).toBeUndefined(); // the browser sets the boundary
    expect(getToken()).toBeNull();
  });
});

describe("beacon (exam integrity reports)", () => {
  it("outlives the page and resolves to the JSON body", async () => {
    saveToken("tok");
    fetch.mockResolvedValue(respond(200, { status: "invalidated" }));
    expect(await api.beacon("/exams/attempts/3/violation", { reason: "hidden" })).toEqual({ status: "invalidated" });
    const { url, options } = lastCall();
    expect(url).toBe("/api/exams/attempts/3/violation");
    expect(options.keepalive).toBe(true);
    expect(options.headers.Authorization).toBe("Bearer tok");
    expect(JSON.parse(options.body)).toEqual({ reason: "hidden" });
  });

  it("never throws: a refused or failed report resolves to null", async () => {
    fetch.mockResolvedValueOnce(respond(409, { detail: "over" }));
    expect(await api.beacon("/x", {})).toBeNull();
    fetch.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    expect(await api.beacon("/x", {})).toBeNull();
  });
});
