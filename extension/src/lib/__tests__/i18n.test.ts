import { describe, expect, it } from "vitest";

import { detectLocale, LOCALES } from "../../i18n";

describe("i18n", () => {
  it("detects the closest supported locale", () => {
    expect(detectLocale(["zh-CN", "en"])).toBe("zh-CN");
    expect(detectLocale(["zh-TW"])).toBe("zh-CN");
    expect(detectLocale(["en-NZ"])).toBe("en");
    expect(detectLocale(["fr-FR"])).toBe("en");
  });

  it("gives every locale the same keys", () => {
    const keys = (o: object, prefix = ""): string[] =>
      Object.entries(o).flatMap(([k, v]) =>
        v && typeof v === "object" ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
      );
    const [first, ...rest] = LOCALES.map((l) => keys(l.messages).sort());
    for (const other of rest) expect(other).toEqual(first);
  });
});
