import { describe, expect, it } from "vitest";

import { en } from "../../i18n/en";
import { zhCN } from "../../i18n/zh-CN";
import { ApiError, errorDetail } from "../api";
import { errorText } from "../format";

describe("errorDetail", () => {
  it("reads string and validation-list details", () => {
    expect(errorDetail({ detail: "Nope" })).toBe("Nope");
    expect(errorDetail({ detail: [{ msg: "Field required" }, { msg: "Too long" }] })).toBe(
      "Field required; Too long",
    );
    expect(errorDetail(null)).toBe("");
  });
});

describe("errorText", () => {
  it("prefixes a localized hint for known statuses", () => {
    const err = new ApiError(409, "Upload a resume before analyzing jobs.");
    expect(errorText(zhCN, err)).toBe("还没有上传简历 — Upload a resume before analyzing jobs.");
    expect(errorText(en, err)).toBe("No resume uploaded yet — Upload a resume before analyzing jobs.");
  });

  it("explains unreachable backends and unknown statuses", () => {
    expect(errorText(en, new ApiError(0, ""), "http://x")).toContain("http://x");
    expect(errorText(en, new ApiError(500, ""))).toBe("Request failed (HTTP 500)");
  });
});
