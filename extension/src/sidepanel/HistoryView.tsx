import { useEffect, useState } from "react";

import { useI18n } from "../i18n";
import { type JobPilotApi } from "../lib/api";
import { FILTER_TONES, errorText, formatDate, scoreTone } from "../lib/format";
import type { MatchOut, MatchSummary } from "../lib/types";
import { ReportView } from "./ReportView";

export function HistoryView({ api, active }: { api: JobPilotApi; active: boolean }) {
  const { t, locale } = useI18n();
  const [items, setItems] = useState<MatchSummary[] | null>(null);
  const [selected, setSelected] = useState<MatchOut | null>(null);
  const [error, setError] = useState<unknown>(null);

  // Reload whenever the tab is opened, so new analyses show up.
  useEffect(() => {
    if (!active) return;
    setError(null);
    api.matches().then(setItems, setError);
  }, [api, active]);

  async function open(id: number) {
    setError(null);
    try {
      setSelected(await api.match(id));
    } catch (err) {
      setError(err);
    }
  }

  if (selected) {
    return (
      <section className="stack">
        <button className="link" onClick={() => setSelected(null)}>
          {t.history.back}
        </button>
        <ReportView match={selected} />
      </section>
    );
  }

  return (
    <section className="stack">
      {error !== null && (
        <div className="notice bad">{errorText(t, error, api.settings.baseUrl)}</div>
      )}
      {items === null && error === null && <p className="muted">{t.history.loading}</p>}
      {items?.length === 0 && <p className="muted">{t.history.empty}</p>}
      <ul className="history">
        {items?.map((m) => (
          <li key={m.id}>
            <button onClick={() => open(m.id)}>
              <span className={`score small ${scoreTone(m.overall_score)}`}>
                {m.overall_score}
              </span>
              <span className="stack tight">
                <strong>{m.title ?? t.report.untitled}</strong>
                <span className="muted small">
                  {[m.company, formatDate(locale, m.created_at)].filter(Boolean).join(" · ")}
                </span>
                <span className={`badge ${FILTER_TONES[m.hard_filter_status]}`}>
                  {t.report.filter[m.hard_filter_status]}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
