import { useState, type FormEvent } from "react";

import { LOCALES, isLocale, useI18n, type Locale } from "../i18n";
import { JobPilotApi } from "../lib/api";
import { errorText } from "../lib/format";
import {
  DEFAULT_BASE_URL,
  normalizeBaseUrl,
  originPattern,
  saveSettings,
  type Settings,
} from "../lib/settings";

// Kept as data so the message re-renders in the new language after a switch.
type Status =
  | { kind: "connected"; file: string; confirmed: boolean }
  | { kind: "noResume" }
  | { kind: "denied" }
  | { kind: "invalid"; error: unknown }
  | { kind: "failed"; error: unknown }
  | null;

export function SettingsView({
  settings,
  onSaved,
  onLocaleChange,
}: {
  settings: Settings;
  onSaved: (settings: Settings) => void;
  onLocaleChange: (locale: Locale) => void;
}) {
  const { t } = useI18n();
  const [baseUrl, setBaseUrl] = useState(settings.baseUrl);
  const [apiKey, setApiKey] = useState(settings.apiKey);
  const [status, setStatus] = useState<Status>(null);
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    setStatus(null);
    let next: Settings;
    try {
      next = { ...settings, baseUrl: normalizeBaseUrl(baseUrl), apiKey: apiKey.trim() };
    } catch (error) {
      setStatus({ kind: "invalid", error });
      return;
    }
    // Must run first, while the click still counts as a user gesture.
    // Already-granted origins (the default localhost ones) resolve without a prompt.
    const granted = await chrome.permissions.request({ origins: [originPattern(next.baseUrl)] });
    if (!granted) {
      setStatus({ kind: "denied" });
      return;
    }

    setBusy(true);
    await saveSettings(next);
    onSaved(next);
    try {
      const profile = await new JobPilotApi(next).profile();
      setStatus(
        profile
          ? { kind: "connected", file: profile.resume_filename, confirmed: profile.confirmed }
          : { kind: "noResume" },
      );
    } catch (error) {
      setStatus({ kind: "failed", error });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <label className="field">
        <span>{t.settings.language}</span>
        <select
          value={settings.locale}
          onChange={(e) => isLocale(e.target.value) && onLocaleChange(e.target.value)}
        >
          {LOCALES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
        <span className="hint">{t.settings.languageHint}</span>
      </label>

      <form className="stack" onSubmit={save}>
        <label className="field">
          <span>{t.settings.baseUrl}</span>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={DEFAULT_BASE_URL}
          />
        </label>
        <label className="field">
          <span>{t.settings.apiKey}</span>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={t.settings.apiKeyPlaceholder}
            autoComplete="off"
          />
        </label>
        <button className="primary" type="submit" disabled={busy}>
          {busy ? t.settings.testing : t.settings.save}
        </button>
        {status && <StatusNotice status={status} baseUrl={baseUrl} />}
        <p className="hint">{t.settings.storageHint}</p>
      </form>
    </div>
  );
}

function StatusNotice({ status, baseUrl }: { status: NonNullable<Status>; baseUrl: string }) {
  const { t } = useI18n();
  switch (status.kind) {
    case "connected":
      return <div className="notice good">{t.settings.connected(status.file, status.confirmed)}</div>;
    case "noResume":
      return <div className="notice good">{t.settings.connectedNoResume}</div>;
    case "denied":
      return <div className="notice bad">{t.settings.denied}</div>;
    case "invalid":
      return <div className="notice bad">{errorText(t, status.error)}</div>;
    case "failed":
      return (
        <div className="notice bad">
          {t.settings.savedButFailed(errorText(t, status.error, baseUrl))}
        </div>
      );
  }
}
