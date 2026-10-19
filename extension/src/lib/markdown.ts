import type { Messages } from "../i18n";
import { checkName, salaryText } from "./format";
import type { Evidence, MatchOut } from "./types";

const DIMENSIONS = ["skills", "experience", "responsibilities", "preferences"] as const;

// Quotes and model text are single-line list items; keep them from breaking the layout.
const oneLine = (text: string) => text.replace(/\s+/g, " ").trim();

function evidenceLine(t: Messages, e: Evidence): string {
  const source = e.source === "cv" ? t.report.sourceCv : t.report.sourceJd;
  const flag = e.verified ? "" : ` ⚠ ${t.markdown.unverified}`;
  return `- **${source}**: "${oneLine(e.quote)}"${flag}`;
}

/** A self-contained Markdown copy of a report, in the user's language. */
export function reportToMarkdown(t: Messages, locale: string, match: MatchOut): string {
  const { report, job } = match;
  const lines: string[] = [];
  const push = (...l: string[]) => lines.push(...l);

  push(`# ${job.data.title ?? t.report.untitled}`, "");
  const meta = [job.data.company, job.data.location, job.data.work_arrangement, salaryText(t, job.data)]
    .filter(Boolean)
    .join(" · ");
  if (meta) push(meta, "");
  if (job.url) push(`- ${t.markdown.link}: <${job.url}>`);
  // Full date with year: exported files are kept long after the analysis.
  const analyzedAt = new Date(match.created_at).toLocaleString(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  push(`- ${t.markdown.analyzedAt}: ${analyzedAt}`, "");

  push(
    `## ${t.markdown.overall}: ${report.overall_score} / 100`,
    "",
    `**${t.report.filter[report.hard_filter.status]}** · ${t.report.formula}`,
    "",
  );
  const warnings = [
    !report.profile_confirmed && t.report.unconfirmed,
    report.job_text_truncated && t.report.truncated,
    report.unverified_evidence_count > 0 && t.report.unverified(report.unverified_evidence_count),
  ].filter((w): w is string => Boolean(w));
  if (warnings.length) push(warnings.map((w) => `> ${w}`).join("\n>\n"), "");

  push(
    `## ${t.markdown.scores}`,
    "",
    `| ${t.markdown.dimension} | ${t.markdown.score} | ${t.markdown.weight} |`,
    "|---|---|---|",
    ...DIMENSIONS.map(
      (d) => `| ${t.report.dimensions[d]} | ${report[d].score} | ${report[d].weight} |`,
    ),
    "",
  );
  for (const d of DIMENSIONS) {
    const dim = report[d];
    push(`### ${t.report.dimensions[d]} — ${dim.score}`, "", oneLine(dim.rationale), "");
    if (dim.evidence.length) {
      push(`${t.markdown.evidence}:`, "", ...dim.evidence.map((e) => evidenceLine(t, e)), "");
    }
  }

  if (report.hard_filter.checks.length) {
    push(`## ${t.report.hardFilter}`, "");
    for (const c of report.hard_filter.checks) {
      push(`- **${t.report.check[c.status]}** ${checkName(t, c.name)} — ${oneLine(c.detail)}`);
    }
    push("");
  }
  if (report.matched_skills.length) {
    push(`## ${t.report.matchedSkills}`, "", report.matched_skills.map((m) => m.skill).join(", "), "");
  }
  if (report.missing_skills.length) {
    push(`## ${t.report.missingSkills}`, "");
    for (const g of report.missing_skills) {
      const importance = g.importance === "required" ? t.report.required : t.report.preferred;
      push(`- **${importance}** ${g.skill}${g.note ? ` — ${oneLine(g.note)}` : ""}`);
    }
    push("");
  }
  if (report.uncertainties.length) {
    push(`## ${t.report.uncertainties}`, "", ...report.uncertainties.map((u) => `- ${oneLine(u)}`), "");
  }

  push("---", "", `*${t.markdown.generatedBy}*`, "");
  return lines.join("\n");
}

/** e.g. "jobpilot-2026-10-20-example-labs-junior-ai-engineer.md" */
export function markdownFileName(match: MatchOut): string {
  const slug = [match.job.data.company, match.job.data.title]
    .filter(Boolean)
    .join("-")
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/, "");
  const date = match.created_at.slice(0, 10);
  return `jobpilot-${date}${slug ? `-${slug}` : ""}.md`;
}
