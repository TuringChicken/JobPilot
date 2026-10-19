import { useEffect, useState } from "react";

import { useI18n } from "../i18n";
import { type JobPilotApi } from "../lib/api";
import { errorText } from "../lib/format";
import { PageAccessError, readActiveTab, requestAllSitesAccess } from "../lib/page";
import type { MatchOut } from "../lib/types";
import type { ProfileState } from "./App";
import { ReportView } from "./ReportView";

type State =
  | { kind: "idle" }
  | { kind: "running"; startedAt: number; fromSelection: boolean }
  | { kind: "done"; match: MatchOut; fromSelection: boolean }
  | { kind: "error"; error: unknown };

export function AnalyzeView({
  api,
  profile,
  onOpenProfile,
  onBusyChange,
}: {
  api: JobPilotApi;
  profile: ProfileState;
  onOpenProfile: () => void;
  onBusyChange: (busy: boolean) => void;
}) {
  const { t, locale } = useI18n();
  const [state, setState] = useState<State>({ kind: "idle" });
  const running = state.kind === "running";
  useEffect(() => onBusyChange(running), [running, onBusyChange]);

  async function analyze() {
    try {
      const page = await readActiveTab();
      setState({ kind: "running", startedAt: Date.now(), fromSelection: page.fromSelection });
      const match = await api.analyze(page, locale);
      setState({ kind: "done", match, fromSelection: page.fromSelection });
    } catch (error) {
      setState({ kind: "error", error });
    }
  }

  async function grantAccess() {
    if (await requestAllSitesAccess()) await analyze();
  }

  return (
    <section className="stack">
      <ProfileNotice profile={profile} onOpenProfile={onOpenProfile} />
      <button className="primary" onClick={analyze} disabled={running}>
        {running ? t.analyze.running : t.analyze.button}
      </button>
      <p className="hint">{t.analyze.hint}</p>

      {state.kind === "running" && <Progress startedAt={state.startedAt} />}
      {state.kind === "error" && (
        <div className="notice bad">
          <p>{errorText(t, state.error, api.settings.baseUrl)}</p>
          {state.error instanceof PageAccessError && state.error.reason === "noAccess" && (
            <button onClick={grantAccess}>{t.analyze.grantAccess}</button>
          )}
        </div>
      )}
      {state.kind === "done" && (
        <>
          {state.fromSelection && <p className="hint">{t.analyze.fromSelection}</p>}
          <ReportView match={state.match} />
        </>
      )}
    </section>
  );
}

function ProfileNotice({
  profile,
  onOpenProfile,
}: {
  profile: ProfileState;
  onOpenProfile: () => void;
}) {
  const { t } = useI18n();
  if (profile === undefined || profile?.confirmed) return null;
  return (
    <div className="notice warn">
      <p>{profile === null ? t.analyze.noResume : t.analyze.unconfirmed}</p>
      <button onClick={onOpenProfile}>
        {profile === null ? t.analyze.uploadResume : t.analyze.reviewResume}
      </button>
    </div>
  );
}

function Progress({ startedAt }: { startedAt: number }) {
  const { t } = useI18n();
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <div className="notice">
      <p>{t.analyze.progress(Math.round((now - startedAt) / 1000))}</p>
      <p className="hint">{t.analyze.progressHint}</p>
    </div>
  );
}
