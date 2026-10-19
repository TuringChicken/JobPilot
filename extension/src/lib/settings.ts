import { detectLocale, isLocale, type Locale } from "../i18n";

export interface Settings {
  baseUrl: string;
  apiKey: string;
  locale: Locale;
}

export const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

// storage.local, not sync: the API key should stay on this machine.
export async function loadSettings(): Promise<Settings> {
  const stored = await chrome.storage.local.get(["baseUrl", "apiKey", "locale"]);
  return {
    baseUrl: typeof stored.baseUrl === "string" ? stored.baseUrl : DEFAULT_BASE_URL,
    apiKey: typeof stored.apiKey === "string" ? stored.apiKey : "",
    locale: isLocale(stored.locale) ? stored.locale : detectLocale(navigator.languages),
  };
}

export async function saveSettings(settings: Partial<Settings>): Promise<void> {
  await chrome.storage.local.set(settings);
}

export class InvalidUrlError extends Error {
  constructor(readonly reason: "format" | "protocol") {
    super(reason);
  }
}

/** Validates and normalizes a backend URL. */
export function normalizeBaseUrl(raw: string): string {
  let url: URL;
  try {
    url = new URL(raw.trim());
  } catch {
    throw new InvalidUrlError("format");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new InvalidUrlError("protocol");
  }
  return url.origin + url.pathname.replace(/\/+$/, "");
}

/** Host permission pattern Chrome needs before the panel can call this backend. */
export function originPattern(baseUrl: string): string {
  return `${new URL(baseUrl).origin}/*`;
}
