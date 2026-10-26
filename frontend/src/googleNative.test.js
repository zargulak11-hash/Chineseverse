import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// googleNative.js loads the Capacitor plugin lazily; each case re-imports it
// with a fake plugin that records calls and answers as told.
let plugin;

async function load() {
  vi.resetModules();
  vi.doMock("@capgo/capacitor-social-login", () => ({ SocialLogin: plugin }));
  return import("./googleNative.js");
}

beforeEach(() => {
  plugin = {
    initialize: vi.fn(async () => {}),
    login: vi.fn(async () => ({ provider: "google", result: { idToken: "id-token-1", responseType: "online" } })),
  };
});

afterEach(() => {
  vi.doUnmock("@capgo/capacitor-social-login");
  vi.unstubAllGlobals();
});

function rejection(message, code) {
  const err = new Error(message);
  if (code) err.code = code;
  return err;
}

describe("nativeGoogleCredential", () => {
  it("asks Android for a token addressed to the server's web client id", async () => {
    const g = await load();
    expect(await g.nativeGoogleCredential("web-1.apps.googleusercontent.com")).toBe("id-token-1");
    expect(plugin.initialize).toHaveBeenCalledWith({
      google: { webClientId: "web-1.apps.googleusercontent.com", mode: "online" },
    });
    expect(plugin.login).toHaveBeenCalledWith({ provider: "google", options: {} });
  });

  it("initializes once per client id, not on every tap", async () => {
    const g = await load();
    await g.nativeGoogleCredential("web-1");
    await g.nativeGoogleCredential("web-1");
    expect(plugin.initialize).toHaveBeenCalledTimes(1);
    await g.nativeGoogleCredential("web-2");
    expect(plugin.initialize).toHaveBeenCalledTimes(2);
    expect(plugin.login).toHaveBeenCalledTimes(3);
  });

  it("without a client id says it isn't set up, without opening the picker", async () => {
    const g = await load();
    await expect(g.nativeGoogleCredential(null)).rejects.toMatchObject({ reason: "notConfigured" });
    expect(plugin.login).not.toHaveBeenCalled();
  });

  it("offline says so before opening the picker", async () => {
    vi.stubGlobal("navigator", { onLine: false });
    const g = await load();
    await expect(g.nativeGoogleCredential("web-1")).rejects.toMatchObject({ reason: "network" });
    expect(plugin.login).not.toHaveBeenCalled();
  });

  it("a sign-in that returns no ID token is a failure, never a success", async () => {
    plugin.login = vi.fn(async () => ({ provider: "google", result: { idToken: null } }));
    const g = await load();
    await expect(g.nativeGoogleCredential("web-1")).rejects.toMatchObject({ reason: "failed" });
  });

  it("a plugin rejection carries its reason and keeps the original error", async () => {
    const original = rejection("Google Sign-In cancelled by user", "USER_CANCELLED");
    plugin.login = vi.fn(async () => {
      throw original;
    });
    const g = await load();
    await expect(g.nativeGoogleCredential("web-1")).rejects.toMatchObject({ reason: "cancelled", cause: original });
  });

  it("a failed initialize is retried on the next tap", async () => {
    plugin.initialize = vi
      .fn()
      .mockRejectedValueOnce(rejection("network timeout"))
      .mockResolvedValue(undefined);
    const g = await load();
    await expect(g.nativeGoogleCredential("web-1")).rejects.toMatchObject({ reason: "network" });
    expect(await g.nativeGoogleCredential("web-1")).toBe("id-token-1");
    expect(plugin.initialize).toHaveBeenCalledTimes(2);
  });
});

describe("nativeGoogleReason", () => {
  // The plugin's own messages (GoogleProvider.java), wrapping Android's
  // Credential Manager exceptions.
  it.each([
    ["cancelled", rejection("Google Sign-In cancelled by user", "USER_CANCELLED")],
    [
      "notConfigured",
      rejection(
        "Google Sign-In failed: Google Cloud OAuth is not configured for this installed build ([28444] Developer console is not set up correctly.). Check Logcat tag GoogleProvider",
      ),
    ],
    ["notConfigured", rejection("Google Sign-In failed: 10: Developer console is not set up correctly.")],
    ["notConfigured", rejection("Google Sign-In failed: Client ID is not set")],
    ["noAccount", rejection("Google Sign-In failed: No credentials available")],
    ["network", rejection("Google Sign-In failed: 7: A network error occurred")],
    ["failed", rejection("Google Sign-In failed: [16] Account reauth failed. The plugin cleared state")],
    ["failed", rejection("Something unexpected")],
  ])("%s <- %s", async (reason, err) => {
    const g = await load();
    expect(g.nativeGoogleReason(err)).toBe(reason);
    expect(g.GOOGLE_NATIVE_REASONS).toContain(reason);
  });
});
