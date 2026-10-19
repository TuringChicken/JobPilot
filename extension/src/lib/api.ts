import type { Settings } from "./settings";
import type {
  CandidateProfileData,
  MatchOut,
  MatchSummary,
  PageContent,
  ProfileOut,
} from "./types";

// Backend limit is 100k characters; the server cleans and truncates further.
export const MAX_TEXT_CHARS = 100_000;

/** status 0 = backend unreachable. `detail` is the backend's own message, if any. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail || `HTTP ${status}`);
  }
}

/** Extracts FastAPI's error detail ({"detail": string | list}) as one line. */
export function errorDetail(body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d?.msg === "string" ? d.msg : JSON.stringify(d))).join("; ");
  }
  return "";
}

export class JobPilotApi {
  constructor(readonly settings: Settings) {}

  health(): Promise<{ status: string }> {
    return this.request("/api/health");
  }

  /** Returns null when no resume has been uploaded yet. */
  async profile(): Promise<ProfileOut | null> {
    try {
      return await this.request<ProfileOut>("/api/profile");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  }

  /** Parsing takes up to a minute; the new profile starts unconfirmed. */
  uploadResume(file: File): Promise<ProfileOut> {
    const form = new FormData();
    form.append("file", file);
    return this.request("/api/profile/resume", { method: "POST", body: form });
  }

  updateProfile(patch: { data?: CandidateProfileData; confirmed?: boolean }): Promise<ProfileOut> {
    return this.request("/api/profile", { method: "PATCH", body: JSON.stringify(patch) });
  }

  /** `language` (BCP 47) sets the language of the report's model-written text. */
  analyze(page: PageContent, language: string): Promise<MatchOut> {
    return this.request("/api/jobs/analyze", {
      method: "POST",
      body: JSON.stringify({
        url: page.url.slice(0, 2048) || null,
        page_title: page.title.slice(0, 500) || null,
        text: page.text.slice(0, MAX_TEXT_CHARS),
        language,
      }),
    });
  }

  /** `saved` filters to saved (true) or unsaved (false) reports; omit for all. */
  matches(options: { limit?: number; saved?: boolean } = {}): Promise<MatchSummary[]> {
    const params = new URLSearchParams({ limit: String(options.limit ?? 50) });
    if (options.saved !== undefined) params.set("saved", String(options.saved));
    return this.request(`/api/matches?${params}`);
  }

  setSaved(id: number, saved: boolean): Promise<MatchOut> {
    return this.request(`/api/matches/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ saved }),
    });
  }

  async deleteMatch(id: number): Promise<void> {
    await this.request(`/api/matches/${id}`, { method: "DELETE" });
  }

  match(id: number): Promise<MatchOut> {
    return this.request(`/api/matches/${id}`);
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let resp: Response;
    try {
      resp = await fetch(this.settings.baseUrl + path, {
        ...init,
        headers: {
          // FormData bodies set their own multipart Content-Type.
          ...(typeof init.body === "string" && { "Content-Type": "application/json" }),
          "X-API-Key": this.settings.apiKey,
          ...init.headers,
        },
      });
    } catch {
      throw new ApiError(0, "");
    }
    const body: unknown = await resp.json().catch(() => null);
    if (!resp.ok) throw new ApiError(resp.status, errorDetail(body));
    return body as T;
  }
}
