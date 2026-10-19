import { describe, expect, it } from "vitest";

import { en } from "../../i18n/en";
import { zhCN } from "../../i18n/zh-CN";
import { markdownFileName, reportToMarkdown } from "../markdown";
import type { DimensionScore, MatchOut } from "../types";

const dim = (score: number): DimensionScore => ({
  score,
  weight: 0.25,
  rationale: "Solid\nmatch",
  evidence: [
    { source: "cv", quote: "Built REST APIs", verified: true },
    { source: "jd", quote: "Kubernetes", verified: false },
  ],
});

const match: MatchOut = {
  id: 1,
  job: {
    id: 1,
    url: "https://jobs.example.com/1",
    data: {
      title: "Junior AI Engineer",
      company: "Example Labs",
      location: "Auckland",
      work_arrangement: "hybrid",
      employment_type: "full_time",
      salary_min: 80000,
      salary_max: 95000,
      salary_currency: "NZD",
      salary_period: "year",
    },
  },
  report: {
    overall_score: 68,
    skills: dim(60),
    experience: dim(55),
    responsibilities: dim(65),
    preferences: dim(100),
    hard_filter: { status: "pass", checks: [{ name: "salary", status: "pass", detail: "OK" }] },
    matched_skills: [{ skill: "Python", evidence: [] }],
    missing_skills: [{ skill: "Kubernetes", importance: "required", note: null }],
    uncertainties: ["Work rights not stated"],
    unverified_evidence_count: 4,
    profile_confirmed: true,
    job_text_truncated: false,
  },
  saved: true,
  created_at: "2026-10-20T03:04:05Z",
};

describe("reportToMarkdown", () => {
  it("renders the report in the chosen language", () => {
    const md = reportToMarkdown(en, "en", match);
    expect(md).toContain("# Junior AI Engineer");
    expect(md).toContain("NZD 80,000–95,000/yr");
    expect(md).toContain("## Overall score: 68 / 100");
    expect(md).toContain("| Skills S | 60 | 0.25 |");
    expect(md).toContain('- **JD**: "Kubernetes" ⚠ unverified');
    expect(md).toContain("- **Required** Kubernetes");
    expect(md).toContain("Solid match"); // rationale flattened to one line

    const zh = reportToMarkdown(zhCN, "zh-CN", match);
    expect(zh).toContain("## 总分: 68 / 100");
    expect(zh).toContain("- **必需** Kubernetes");
  });

  it("builds a safe file name", () => {
    expect(markdownFileName(match)).toBe(
      "jobpilot-2026-10-20-example-labs-junior-ai-engineer.md",
    );
    const odd = { ...match, job: { ...match.job, data: { ...match.job.data, company: null, title: "AI/ML 工程师 (远程)" } } };
    expect(markdownFileName(odd)).toBe("jobpilot-2026-10-20-ai-ml-工程师-远程.md");
  });
});
