import type { Messages } from "../i18n";
import { ApiError } from "./api";
import { PageAccessError } from "./page";
import { InvalidUrlError } from "./settings";
import type { CheckStatus, HardFilterStatus, JobPostingData } from "./types";

export type Tone = "good" | "warn" | "bad" | "neutral";

export function scoreTone(score: number): Tone {
  if (score >= 75) return "good";
  if (score >= 50) return "warn";
  return "bad";
}

export const FILTER_TONES: Record<HardFilterStatus, Tone> = {
  pass: "good",
  needs_review: "warn",
  fail: "bad",
};

export const CHECK_TONES: Record<CheckStatus, Tone> = {
  pass: "good",
  unknown: "warn",
  fail: "bad",
};

export function checkName(t: Messages, name: string): string {
  if (name in t.report.checkNames) return t.report.checkNames[name];
  // Condition checks are named "must_have: <condition>" / "deal_breaker: <condition>".
  const [kind, ...rest] = name.split(": ");
  const condition = rest.join(": ");
  if (kind === "must_have" && condition) return t.report.mustHave(condition);
  if (kind === "deal_breaker" && condition) return t.report.dealBreaker(condition);
  return name;
}

export function salaryText(t: Messages, job: JobPostingData): string | null {
  const { salary_min: min, salary_max: max, salary_currency: cur, salary_period: period } = job;
  if (min === null && max === null) return null;
  const fmt = (n: number) => n.toLocaleString("en-NZ");
  const range =
    min !== null && max !== null && min !== max ? `${fmt(min)}–${fmt(max)}` : fmt((min ?? max)!);
  const unit = period === "hour" ? t.report.perHour : period === "year" ? t.report.perYear : "";
  return `${cur ?? ""} ${range}${unit}`.trim();
}

export function formatDate(locale: string, iso: string): string {
  return new Date(iso).toLocaleString(locale, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** User-facing message for any error thrown by the lib modules. */
export function errorText(t: Messages, err: unknown, baseUrl = ""): string {
  if (err instanceof ApiError) {
    if (err.status === 0) return t.errors.unreachable(baseUrl);
    const hint = t.errors.status[err.status];
    return [hint, err.detail].filter(Boolean).join(" — ") || t.errors.httpStatus(err.status);
  }
  if (err instanceof PageAccessError) return t.page[err.reason];
  if (err instanceof InvalidUrlError) {
    return err.reason === "format" ? t.settings.invalidUrl : t.settings.invalidProtocol;
  }
  return err instanceof Error ? err.message : String(err);
}
