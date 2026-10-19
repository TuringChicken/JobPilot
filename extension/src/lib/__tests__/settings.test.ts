import { describe, expect, it } from "vitest";

import { InvalidUrlError, normalizeBaseUrl, originPattern } from "../settings";

describe("settings", () => {
  it("normalizes backend URLs", () => {
    expect(normalizeBaseUrl(" http://127.0.0.1:8000/ ")).toBe("http://127.0.0.1:8000");
    expect(normalizeBaseUrl("https://api.example.com/jobpilot//")).toBe(
      "https://api.example.com/jobpilot",
    );
  });

  it("rejects invalid URLs", () => {
    expect(() => normalizeBaseUrl("ftp://example.com")).toThrow(new InvalidUrlError("protocol"));
    expect(() => normalizeBaseUrl("not a url")).toThrow();
  });

  it("builds a host permission pattern", () => {
    expect(originPattern("https://api.example.com/jobpilot")).toBe("https://api.example.com/*");
  });
});
