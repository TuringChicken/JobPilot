// Mirrors backend/app/schemas (jobs.py, profile.py). Keep in sync when the API changes.

export type CheckStatus = "pass" | "fail" | "unknown";
export type HardFilterStatus = "pass" | "fail" | "needs_review";

export interface Evidence {
  source: "cv" | "jd";
  quote: string;
  verified: boolean;
}

export interface DimensionScore {
  score: number;
  weight: number;
  rationale: string;
  evidence: Evidence[];
}

export interface FilterCheck {
  name: string;
  status: CheckStatus;
  detail: string;
}

export interface SkillGap {
  skill: string;
  importance: "required" | "preferred";
  note: string | null;
}

export interface MatchReport {
  overall_score: number;
  skills: DimensionScore;
  experience: DimensionScore;
  responsibilities: DimensionScore;
  preferences: DimensionScore;
  hard_filter: { status: HardFilterStatus; checks: FilterCheck[] };
  matched_skills: { skill: string; evidence: Evidence[] }[];
  missing_skills: SkillGap[];
  uncertainties: string[];
  unverified_evidence_count: number;
  profile_confirmed: boolean;
  job_text_truncated: boolean;
}

export interface JobPostingData {
  title: string | null;
  company: string | null;
  location: string | null;
  work_arrangement: string | null;
  employment_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  salary_period: "year" | "hour" | null;
}

export interface MatchOut {
  id: number;
  job: { id: number; url: string | null; data: JobPostingData };
  report: MatchReport;
  created_at: string;
}

export interface MatchSummary {
  id: number;
  job_id: number;
  title: string | null;
  company: string | null;
  url: string | null;
  overall_score: number;
  hard_filter_status: HardFilterStatus;
  created_at: string;
}

export interface CandidateProfileData {
  summary: string | null;
  education: {
    institution: string;
    degree: string | null;
    field_of_study: string | null;
    start_date: string | null;
    end_date: string | null;
  }[];
  skills: { name: string; category: string | null; proficiency: string | null }[];
  certifications: { name: string; issuer: string | null; date: string | null }[];
  languages: { name: string; proficiency: string | null }[];
  awards: { title: string; issuer: string | null; date: string | null }[];
  work_experience: {
    title: string;
    company: string;
    start_date: string | null;
    end_date: string | null;
    responsibilities: string[];
  }[];
  projects: { name: string; description: string | null; tech_stack: string[]; outcomes: string[] }[];
}

export interface ProfileOut {
  id: number;
  resume_filename: string;
  confirmed: boolean;
  data: CandidateProfileData;
  updated_at: string;
}

export interface PageContent {
  url: string;
  title: string;
  text: string;
  fromSelection: boolean;
}
