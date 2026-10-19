import { createContext, useContext } from "react";

import { en } from "./en";
import { zhCN, type Messages } from "./zh-CN";

// To add a language: create a Messages file next to these and list it here.
// The code is a BCP 47 tag; it is also sent to the backend as the report language.
export const LOCALES = [
  { code: "zh-CN", label: "简体中文", messages: zhCN },
  { code: "en", label: "English", messages: en },
] as const satisfies readonly { code: string; label: string; messages: Messages }[];

export type Locale = (typeof LOCALES)[number]["code"];

export function isLocale(value: unknown): value is Locale {
  return LOCALES.some((l) => l.code === value);
}

/** Best match for the browser's preferred languages, falling back to English. */
export function detectLocale(preferred: readonly string[]): Locale {
  for (const tag of preferred) {
    const lower = tag.toLowerCase();
    const exact = LOCALES.find((l) => l.code.toLowerCase() === lower);
    if (exact) return exact.code;
    const base = LOCALES.find((l) => l.code.split("-")[0] === lower.split("-")[0]);
    if (base) return base.code;
  }
  return "en";
}

export function messagesFor(locale: Locale): Messages {
  return LOCALES.find((l) => l.code === locale)!.messages;
}

export const I18nContext = createContext<{ locale: Locale; t: Messages }>({
  locale: "en",
  t: en,
});

export function useI18n() {
  return useContext(I18nContext);
}

export type { Messages };
