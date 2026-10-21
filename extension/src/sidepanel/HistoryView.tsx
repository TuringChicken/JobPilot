import { useEffect, useState } from "react";

import { useI18n } from "../i18n";
import { type JobPilotApi } from "../lib/api";
import { FILTER_TONES, errorText, formatDate, scoreTone } from "../lib/format";
import type { MatchOut, MatchSummary } from "../lib/types";
import { ReportView } from "./ReportView";

type Filter = "all" | "saved";

export function HistoryView({
  api,
  active,
  onBusyChange,
}: {
  api: JobPilotApi;
  active: boolean;
  onBusyChange: (busy: boolean) => void;
}) {
  const { t, locale } = useI18n();
  const [filter, setFilter] = useState<Filter>("all");
  const [items, setItems] = useState<MatchSummary[] | null>(null);
  const [selected, setSelected] = useState<MatchOut | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [reanalyzing, setReanalyzing] = useState(0);
  useEffect(() => onBusyChange(reanalyzing > 0), [reanalyzing, onBusyChange]);

  // Reload whenever the tab is opened or the list is shown again, so changes show up.
  const showingList = active && selected === null;
  useEffect(() => {
    if (!showingList) return;
    setError(null);
    api
      .matches({ saved: filter === "saved" ? true : undefined })
      .then(setItems, setError);
  }, [api, showingList, filter]);

  async function open(id: number) {
    setError(null);
    try {
      setSelected(await api.match(id));
    } catch (err) {
      setError(err);
    }
  }

  /** Same job, current resume/preferences; the new report replaces the one on screen. */
  async function reanalyze(id: number) {
    setReanalyzing((n) => n + 1);
    try {
      const match = await api.reanalyze(id, locale);
      // Only if the user is still looking at the report it was started from.
      setSelected((current) => (current?.id === id ? match : current));
    } finally {
      setReanalyzing((n) => n - 1);
    }
  }

  if (selected) {
    return (
      <section className="stack">
        <button className="link" onClick={() => setSelected(null)}>
          {t.history.back}
        </button>
        <ReportView
          api={api}
          match={selected}
          onChange={setSelected}
          onDeleted={() => setSelected(null)}
          onReanalyze={() => reanalyze(selected.id)}
        />
      </section>
    );
  }

  return (
    <section className="stack">
      <div className="segmented">
        {(["all", "saved"] as const).map((f) => (
          <button
            key={f}
            className={f === filter ? "active" : ""}
            onClick={() => setFilter(f)}
          >
            {f === "all" ? t.history.all : t.history.savedOnly}
          </button>
        ))}
      </div>
      {error !== null && (
        <div className="notice bad">{errorText(t, error, api.settings.baseUrl)}</div>
      )}
      {items === null && error === null && <p className="muted">{t.history.loading}</p>}
      {items?.length === 0 && (
        <p className="muted">{filter === "saved" ? t.history.emptySaved : t.history.empty}</p>
      )}
      <ul className="history">
        {items?.map((m) => (
          <li key={m.id}>
            <button onClick={() => open(m.id)}>
              <span className={`score small ${scoreTone(m.overall_score)}`}>
                {m.overall_score}
              </span>
              <span className="stack tight">
                <strong>
                  {m.saved && <span className="star">★ </span>}
                  {m.title ?? t.report.untitled}
                </strong>
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
