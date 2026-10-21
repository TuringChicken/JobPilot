import { useCallback, useEffect, useMemo, useState } from "react";

import { I18nContext, messagesFor, type Locale } from "../i18n";
import { JobPilotApi } from "../lib/api";
import { loadSettings, saveSettings, type Settings } from "../lib/settings";
import type { ProfileOut } from "../lib/types";
import { AnalyzeView } from "./AnalyzeView";
import { HistoryView } from "./HistoryView";
import { ProfileView } from "./ProfileView";
import { SettingsView } from "./SettingsView";

type Tab = "analyze" | "profile" | "history" | "settings";

const TABS: Tab[] = ["analyze", "profile", "history", "settings"];

// undefined = not checked yet / unreachable; null = no resume uploaded.
export type ProfileState = ProfileOut | null | undefined;

export function App() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [tab, setTab] = useState<Tab>("analyze");
  const [profile, setProfile] = useState<ProfileState>(undefined);
  // Tabs with work in flight, marked in the tab bar while the user looks elsewhere.
  const [busy, setBusy] = useState<Partial<Record<Tab, boolean>>>({});
  const busySetter = useCallback(
    (id: Tab) => (value: boolean) => setBusy((b) => ({ ...b, [id]: value })),
    [],
  );
  const setAnalyzeBusy = useMemo(() => busySetter("analyze"), [busySetter]);
  const setProfileBusy = useMemo(() => busySetter("profile"), [busySetter]);
  const setHistoryBusy = useMemo(() => busySetter("history"), [busySetter]);

  const refreshProfile = useCallback(async (s: Settings) => {
    try {
      setProfile(await new JobPilotApi(s).profile());
    } catch {
      setProfile(undefined);
    }
  }, []);

  useEffect(() => {
    loadSettings().then((s) => {
      setSettings(s);
      if (!s.apiKey) setTab("settings");
      else void refreshProfile(s);
    });
  }, [refreshProfile]);

  const api = useMemo(() => settings && new JobPilotApi(settings), [settings]);
  const i18n = useMemo(
    () => settings && { locale: settings.locale, t: messagesFor(settings.locale) },
    [settings],
  );

  useEffect(() => {
    if (i18n) document.documentElement.lang = i18n.locale;
  }, [i18n]);

  if (!settings || !api || !i18n) return null;
  const { t } = i18n;

  function changeLocale(locale: Locale) {
    void saveSettings({ locale });
    setSettings((s) => s && { ...s, locale });
  }

  return (
    <I18nContext.Provider value={i18n}>
      <div className="app">
        <nav className="tabs">
          {TABS.map((id) => (
            <button
              key={id}
              className={id === tab ? "tab active" : "tab"}
              onClick={() => setTab(id)}
            >
              {t.tabs[id]}
              {busy[id] && id !== tab && <span className="spinner" title={t.busy} />}
            </button>
          ))}
        </nav>
        {/* Every view stays mounted so in-flight requests and results survive tab switches. */}
        <main>
          <div hidden={tab !== "analyze"}>
            <AnalyzeView
              api={api}
              profile={profile}
              onOpenProfile={() => setTab("profile")}
              onBusyChange={setAnalyzeBusy}
            />
          </div>
          <div hidden={tab !== "profile"}>
            <ProfileView
              api={api}
              profile={profile}
              onChange={setProfile}
              onBusyChange={setProfileBusy}
            />
          </div>
          <div hidden={tab !== "history"}>
            <HistoryView api={api} active={tab === "history"} onBusyChange={setHistoryBusy} />
          </div>
          <div hidden={tab !== "settings"}>
            <SettingsView
              settings={settings}
              onLocaleChange={changeLocale}
              onSaved={(s) => {
                setSettings(s);
                void refreshProfile(s);
              }}
            />
          </div>
        </main>
      </div>
    </I18nContext.Provider>
  );
}
