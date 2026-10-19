import { describe, expect, it } from "vitest";

import { en } from "../../i18n/en";
import { zhCN } from "../../i18n/zh-CN";
import { checkName, salaryText, scoreTone } from "../format";
import type { JobPostingData } from "../types";

const job = (overrides: Partial<JobPostingData>): JobPostingData => ({
  title: null,
  company: null,
  location: null,
  work_arrangement: null,
  employment_type: null,
  salary_min: null,
  salary_max: null,
  salary_currency: null,
  salary_period: null,
  ...overrides,
});

describe("format", () => {
  it("bands scores", () => {
    expect([scoreTone(80), scoreTone(60), scoreTone(10)]).toEqual(["good", "warn", "bad"]);
  });

  it("names condition checks", () => {
    expect(checkName(zhCN, "salary")).toBe("薪资");
    expect(checkName(en, "salary")).toBe("Salary");
    expect(checkName(zhCN, "must_have: visa sponsorship")).toBe("必要条件：visa sponsorship");
    expect(checkName(en, "deal_breaker: on-call: weekends")).toBe("Deal-breaker: on-call: weekends");
  });

  it("formats salary ranges", () => {
    expect(salaryText(zhCN, job({}))).toBeNull();
    const nzd = job({ salary_min: 80000, salary_max: 95000, salary_currency: "NZD", salary_period: "year" });
    expect(salaryText(zhCN, nzd)).toBe("NZD 80,000–95,000/年");
    expect(salaryText(en, nzd)).toBe("NZD 80,000–95,000/yr");
    expect(salaryText(en, job({ salary_max: 40, salary_period: "hour" }))).toBe("40/hr");
  });
});
