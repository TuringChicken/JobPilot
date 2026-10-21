import { useState } from "react";

import { useI18n } from "../i18n";
import { type JobPilotApi } from "../lib/api";
import { saveTextFile } from "../lib/download";
import {
  CHECK_TONES,
  FILTER_TONES,
  checkName,
  errorText,
  formatDate,
  salaryText,
  scoreTone,
} from "../lib/format";
import { markdownFileName, reportToMarkdown } from "../lib/markdown";
import type { DimensionScore, Evidence, MatchOut } from "../lib/types";

const DIMENSIONS = ["skills", "experience", "responsibilities", "preferences"] as const;

export function ReportView({
  api,
  match,
  onChange,
  onDeleted,
  onReanalyze,
}: {
  api: JobPilotApi;
  match: MatchOut;
  onChange: (match: MatchOut) => void;
  onDeleted: () => void;
  /** Shows an "Analyze again" button; resolves once the new report is shown. */
  onReanalyze?: () => Promise<void>;
}) {
  const { t, locale } = useI18n();
  const { report, job } = match;
  const status = report.hard_filter.status;
  const meta = [job.data.company, job.data.location, job.data.work_arrangement, salaryText(t, job.data)]
    .filter(Boolean)
    .join(" · ");
  const title = job.data.title ?? t.report.untitled;

  return (
    <article className="report stack">
      <header>
        <h2>
          {job.url ? (
            <a href={job.url} target="_blank" rel="noreferrer">
              {title}
            </a>
          ) : (
            title
          )}
        </h2>
        {meta && <p className="muted">{meta}</p>}
        <p className="muted small">{formatDate(locale, match.created_at)}</p>
      </header>

      <ReportActions
        api={api}
        match={match}
        onChange={onChange}
        onDeleted={onDeleted}
        onReanalyze={onReanalyze}
      />

      <div className="score-row">
        <div className={`score ${scoreTone(report.overall_score)}`}>{report.overall_score}</div>
        <div className="stack tight">
          <span className={`badge ${FILTER_TONES[status]}`}>{t.report.filter[status]}</span>
          <span className="muted small">{t.report.formula}</span>
        </div>
      </div>

      {!report.profile_confirmed && <div className="notice warn">{t.report.unconfirmed}</div>}
      {report.job_text_truncated && <div className="notice warn">{t.report.truncated}</div>}
      {report.unverified_evidence_count > 0 && (
        <div className="notice warn">{t.report.unverified(report.unverified_evidence_count)}</div>
      )}

      <section className="stack">
        {DIMENSIONS.map((key) => (
          <Dimension key={key} label={t.report.dimensions[key]} dim={report[key]} />
        ))}
      </section>

      {report.hard_filter.checks.length > 0 && (
        <section>
          <h3>{t.report.hardFilter}</h3>
          <ul className="checks">
            {report.hard_filter.checks.map((c) => (
              <li key={c.name}>
                <span className={`badge ${CHECK_TONES[c.status]}`}>{t.report.check[c.status]}</span>{" "}
                {checkName(t, c.name)}
                <div className="muted small">{c.detail}</div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {report.matched_skills.length > 0 && (
        <section>
          <h3>{t.report.matchedSkills}</h3>
          <div className="chips">
            {report.matched_skills.map((m) => (
              <span
                key={m.skill}
                className="chip good"
                title={m.evidence.map((e) => e.quote).join("\n")}
              >
                {m.skill}
              </span>
            ))}
          </div>
        </section>
      )}

      {report.missing_skills.length > 0 && (
        <section>
          <h3>{t.report.missingSkills}</h3>
          <ul>
            {report.missing_skills.map((g) => (
              <li key={g.skill}>
                <span className={`badge ${g.importance === "required" ? "bad" : "neutral"}`}>
                  {g.importance === "required" ? t.report.required : t.report.preferred}
                </span>{" "}
                {g.skill}
                {g.note && <div className="muted small">{g.note}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {report.uncertainties.length > 0 && (
        <section>
          <h3>{t.report.uncertainties}</h3>
          <ul>
            {report.uncertainties.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}

function Dimension({ label, dim }: { label: string; dim: DimensionScore }) {
  const tone = scoreTone(dim.score);
  return (
    <details className="dimension">
      <summary>
        <span className="dim-label">{label}</span>
        <span className="bar">
          <span className={`fill ${tone}`} style={{ width: `${dim.score}%` }} />
        </span>
        <span className="dim-score">{dim.score}</span>
      </summary>
      <p>{dim.rationale}</p>
      {dim.evidence.length > 0 && (
        <ul className="evidence">
          {dim.evidence.map((e, i) => (
            <EvidenceItem key={i} evidence={e} />
          ))}
        </ul>
      )}
    </details>
  );
}

function EvidenceItem({ evidence }: { evidence: Evidence }) {
  const { t } = useI18n();
  return (
    <li className={evidence.verified ? "" : "unverified"}>
      <span className="source">{evidence.source === "cv" ? t.report.sourceCv : t.report.sourceJd}</span>
      <q>{evidence.quote}</q>
      {!evidence.verified && <span title={t.report.unverifiedTitle}> ⚠</span>}
    </li>
  );
}

type ActionStatus =
  | { kind: "exported"; name: string }
  | { kind: "reanalyzing" }
  | { kind: "reanalyzed" }
  | { kind: "error"; error: unknown }
  | null;

function ReportActions({
  api,
  match,
  onChange,
  onDeleted,
  onReanalyze,
}: {
  api: JobPilotApi;
  match: MatchOut;
  onChange: (match: MatchOut) => void;
  onDeleted: () => void;
  onReanalyze?: () => Promise<void>;
}) {
  const { t, locale } = useI18n();
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<ActionStatus>(null);

  async function act(action: () => Promise<void>, pending: ActionStatus = null) {
    setBusy(true);
    setStatus(pending);
    try {
      await action();
    } catch (error) {
      setStatus({ kind: "error", error });
    } finally {
      setBusy(false);
    }
  }

  const reanalyze =
    onReanalyze &&
    (() =>
      act(async () => {
        await onReanalyze();
        setStatus({ kind: "reanalyzed" });
      }, { kind: "reanalyzing" }));

  const toggleSaved = () => act(async () => onChange(await api.setSaved(match.id, !match.saved)));

  const exportMarkdown = () =>
    act(async () => {
      const name = await saveTextFile(markdownFileName(match), reportToMarkdown(t, locale, match));
      if (name) setStatus({ kind: "exported", name });
    });

  const remove = () => {
    if (!confirm(t.report.deleteConfirm)) return;
    void act(async () => {
      await api.deleteMatch(match.id);
      onDeleted();
    });
  };

  return (
    <div className="stack tight">
      <div className="row">
        <button
          className={match.saved ? "saved" : ""}
          onClick={toggleSaved}
          disabled={busy}
          title={match.saved ? t.report.unsaveTitle : undefined}
        >
          {match.saved ? t.report.saved : t.report.save}
        </button>
        <button onClick={exportMarkdown} disabled={busy}>
          {t.report.exportMarkdown}
        </button>
        {reanalyze && (
          <button onClick={reanalyze} disabled={busy} title={t.report.reanalyzeTitle}>
            {status?.kind === "reanalyzing" ? t.report.reanalyzing : t.report.reanalyze}
          </button>
        )}
        <button className="danger" onClick={remove} disabled={busy}>
          {t.report.delete}
        </button>
      </div>
      {status?.kind === "exported" && (
        <p className="hint">{t.report.exported(status.name)}</p>
      )}
      {status?.kind === "reanalyzing" && <p className="hint">{t.report.reanalyzingHint}</p>}
      {status?.kind === "reanalyzed" && <p className="hint">{t.report.reanalyzed}</p>}
      {status?.kind === "error" && (
        <div className="notice bad">{errorText(t, status.error, api.settings.baseUrl)}</div>
      )}
    </div>
  );
}
