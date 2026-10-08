import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  api,
  changePassword,
  clearSession,
  completeGitHubSignIn,
  getSavedUser,
  getToken,
  githubStartUrl,
  login,
  onSessionExpired,
  saveToken,
  saveUser,
} from "./api.js";
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
  it("explains in the learner's language why onboarding can't be finished yet", async () => {
    await i18n.changeLanguage("ru");
    fetch.mockResolvedValue(respond(409, { detail: "Choose your companion before finishing onboarding" }));
    const err = await api.post("/onboarding/placement-test/skip").catch((e) => e);
    expect(err.message).toBe(ru.apiErrors.onboardingCompanionFirst);
    fetch.mockResolvedValue(respond(409, { detail: "Answer the onboarding questions before finishing onboarding" }));
    const again = await api.post("/onboarding/placement-test/skip").catch((e) => e);
    expect(again.message).toBe(ru.apiErrors.onboardingQuestionsFirst);
  });

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

  it("an expired session tells the app to sign out; a wrong password does not", async () => {
    const expired = vi.fn();
    const stop = onSessionExpired(expired);
    // No token sent: a failed login is not an ended session.
    fetch.mockResolvedValue(respond(401, { detail: "Invalid username or password" }));
    await expect(login({ username: "a", password: "b" })).rejects.toThrow();
    expect(expired).not.toHaveBeenCalled();
    saveToken("old");
    fetch.mockResolvedValue(respond(401, { detail: "Invalid or expired token" }));
    await expect(api.get("/dashboard")).rejects.toThrow();
    expect(expired).toHaveBeenCalledTimes(1);
    stop();
  });

  it.each([
    ["Chrome/Edge", "Failed to fetch"],
    ["Firefox", "NetworkError when attempting to fetch resource."],
    ["Safari", "Load failed"],
  ])("an unreachable server reads the same in every browser (%s)", async (_browser, raw) => {
    await i18n.changeLanguage("ru");
    fetch.mockRejectedValue(new TypeError(raw));
    const err = await api.get("/me").catch((e) => e);
    expect(err.message).toBe(ru.apiErrors.network);
    expect(err.status).toBe(0);
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

  it("GitHub starts as a plain navigation to the backend and returns to the right page", () => {
    expect(githubStartUrl("register")).toBe("/api/auth/github/start?page=register");
  });

  it("GitHub finishes by swapping the ticket cookie for a stored session", async () => {
    fetch.mockResolvedValue(respond(200, { access_token: "gh-token", user: { id: 9, onboarding_completed: false } }));
    expect(await completeGitHubSignIn()).toEqual({ id: 9, onboarding_completed: false });
    const { url, options } = lastCall();
    expect(url).toBe("/api/auth/github/session");
    expect(options.method).toBe("POST");
    expect(getToken()).toBe("gh-token");
  });

  it("a spent GitHub ticket is a translated message, not a sign-out", async () => {
    await i18n.changeLanguage("ru");
    const expired = vi.fn();
    const stop = onSessionExpired(expired);
    fetch.mockResolvedValue(respond(401, { detail: "This GitHub sign-in has expired. Please try again." }));
    await expect(completeGitHubSignIn()).rejects.toThrow(ru.apiErrors.githubExpired);
    expect(expired).not.toHaveBeenCalled();
    stop();
  });
});

describe("change password", () => {
  it("sends the three fields, swaps in the fresh token and stores no password", async () => {
    saveToken("old-token");
    fetch.mockResolvedValue(respond(200, { access_token: "fresh-token", user: { id: 1, username: "a" } }));
    const user = await changePassword({ current: "secret1", next: "brand-new", confirm: "brand-new" });
    const { url, options } = lastCall();
    expect(url).toBe("/api/me/password");
    expect(options.headers.Authorization).toBe("Bearer old-token");
    expect(JSON.parse(options.body)).toEqual({
      current_password: "secret1",
      new_password: "brand-new",
      confirm_password: "brand-new",
    });
    expect(user).toEqual({ id: 1, username: "a" });
    expect(getToken()).toBe("fresh-token");
    const stored = Object.keys(localStorage).map((k) => localStorage.getItem(k)).join("|");
    expect(stored).not.toContain("secret1");
    expect(stored).not.toContain("brand-new");
  });

  it("keeps the session on a wrong current password and says so in the learner's language", async () => {
    saveToken("still-valid");
    await i18n.changeLanguage("ru");
    fetch.mockResolvedValue(respond(400, { detail: "Current password is incorrect" }));
    const err = await changePassword({ current: "nope", next: "brand-new", confirm: "brand-new" }).catch((e) => e);
    expect(err.message).toBe(ru.apiErrors.currentPasswordWrong);
    expect(getToken()).toBe("still-valid");
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
