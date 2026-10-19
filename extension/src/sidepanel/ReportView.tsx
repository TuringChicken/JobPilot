import { useI18n } from "../i18n";
import {
  CHECK_TONES,
  FILTER_TONES,
  checkName,
  formatDate,
  salaryText,
  scoreTone,
} from "../lib/format";
import type { DimensionScore, Evidence, MatchOut } from "../lib/types";

const DIMENSIONS = ["skills", "experience", "responsibilities", "preferences"] as const;

export function ReportView({ match }: { match: MatchOut }) {
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
