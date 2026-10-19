import { useEffect, useState, type ReactNode } from "react";

import { useI18n } from "../i18n";
import { type JobPilotApi } from "../lib/api";
import { errorText, formatDate } from "../lib/format";
import type { CandidateProfileData, ProfileOut } from "../lib/types";
import type { ProfileState } from "./App";

type Mode = "view" | "edit" | "upload";
type BusyKey = "parsing" | "saving" | "confirming";

export function ProfileView({
  api,
  profile,
  onChange,
  onBusyChange,
}: {
  api: JobPilotApi;
  profile: ProfileState;
  onChange: (profile: ProfileOut) => void;
  onBusyChange: (busy: boolean) => void;
}) {
  const { t, locale } = useI18n();
  const [mode, setMode] = useState<Mode>("view");
  const [busy, setBusy] = useState<BusyKey | null>(null);
  useEffect(() => onBusyChange(busy !== null), [busy, onBusyChange]);
  const [error, setError] = useState<unknown>(null);

  async function run(label: BusyKey, action: () => Promise<ProfileOut>, next: Mode = "view") {
    setBusy(label);
    setError(null);
    try {
      onChange(await action());
      setMode(next);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  if (profile === undefined) {
    return <div className="notice bad">{t.profile.unreachable}</div>;
  }

  const upload = (
    <UploadForm
      busy={busy !== null}
      onUpload={(file) => run("parsing", () => api.uploadResume(file))}
      onCancel={profile ? () => setMode("view") : undefined}
    />
  );

  return (
    <section className="stack">
      {error !== null && (
        <div className="notice bad">{errorText(t, error, api.settings.baseUrl)}</div>
      )}
      {busy && <div className="notice">{t.profile[busy]}</div>}

      {profile === null || mode === "upload" ? (
        upload
      ) : mode === "edit" ? (
        <JsonEditor
          data={profile.data}
          busy={busy !== null}
          onSave={(data) => run("saving", () => api.updateProfile({ data }))}
          onCancel={() => setMode("view")}
        />
      ) : (
        <>
          <header className="stack tight">
            <strong>{profile.resume_filename}</strong>
            <span className="muted small">
              {t.profile.updatedAt(formatDate(locale, profile.updated_at))}
            </span>
          </header>
          {profile.confirmed ? (
            <div className="notice good">{t.profile.confirmed}</div>
          ) : (
            <div className="notice warn">
              <p>{t.profile.review}</p>
              <button
                className="primary"
                disabled={busy !== null}
                onClick={() => run("confirming", () => api.updateProfile({ confirmed: true }))}
              >
                {t.profile.confirm}
              </button>
            </div>
          )}
          <div className="row">
            <button disabled={busy !== null} onClick={() => setMode("edit")}>
              {t.profile.edit}
            </button>
            <button disabled={busy !== null} onClick={() => setMode("upload")}>
              {t.profile.reupload}
            </button>
          </div>
          <ProfileDetails data={profile.data} />
        </>
      )}
    </section>
  );
}

function UploadForm({
  busy,
  onUpload,
  onCancel,
}: {
  busy: boolean;
  onUpload: (file: File) => void;
  onCancel?: () => void;
}) {
  const { t } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        if (file) onUpload(file);
      }}
    >
      <label className="field">
        <span>{t.profile.uploadLabel}</span>
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>
      <p className="hint">{t.profile.uploadHint}</p>
      <div className="row">
        <button className="primary" type="submit" disabled={!file || busy}>
          {t.profile.upload}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={busy}>
            {t.profile.cancel}
          </button>
        )}
      </div>
    </form>
  );
}

function JsonEditor({
  data,
  busy,
  onSave,
  onCancel,
}: {
  data: CandidateProfileData;
  busy: boolean;
  onSave: (data: CandidateProfileData) => void;
  onCancel: () => void;
}) {
  const { t } = useI18n();
  const [text, setText] = useState(() => JSON.stringify(data, null, 2));
  const [parseError, setParseError] = useState<string | null>(null);

  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault();
        try {
          setParseError(null);
          onSave(JSON.parse(text) as CandidateProfileData);
        } catch {
          setParseError(t.profile.invalidJson);
        }
      }}
    >
      <p className="hint">{t.profile.editHint}</p>
      <textarea
        className="json"
        value={text}
        onChange={(e) => setText(e.target.value)}
        spellCheck={false}
      />
      {parseError && <div className="notice bad">{parseError}</div>}
      <div className="row">
        <button className="primary" type="submit" disabled={busy}>
          {t.profile.save}
        </button>
        <button type="button" onClick={onCancel} disabled={busy}>
          {t.profile.cancel}
        </button>
      </div>
    </form>
  );
}

function dateRange(start: string | null, end: string | null): string {
  if (!start && !end) return "";
  return `${start ?? "?"} – ${end ?? "?"}`;
}

function join(...parts: (string | null | undefined)[]): string {
  return parts.filter(Boolean).join(" · ");
}

function Section({ title, count, children }: { title: string; count: number; children: ReactNode }) {
  const { t } = useI18n();
  return (
    <section>
      <h3>
        {title} <span className="muted small">{count}</span>
      </h3>
      {count === 0 ? <p className="muted small">{t.profile.none}</p> : children}
    </section>
  );
}

function ProfileDetails({ data }: { data: CandidateProfileData }) {
  const { t } = useI18n();
  return (
    <div className="stack profile">
      {data.summary && (
        <section>
          <h3>{t.profile.summary}</h3>
          <p>{data.summary}</p>
        </section>
      )}

      <Section title={t.profile.work} count={data.work_experience.length}>
        <ul className="entries">
          {data.work_experience.map((w, i) => (
            <li key={i}>
              <strong>{w.title}</strong> @ {w.company}
              <div className="muted small">{dateRange(w.start_date, w.end_date)}</div>
              {w.responsibilities.length > 0 && (
                <ul>
                  {w.responsibilities.map((r, j) => (
                    <li key={j}>{r}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </Section>

      <Section title={t.profile.projects} count={data.projects.length}>
        <ul className="entries">
          {data.projects.map((p, i) => (
            <li key={i}>
              <strong>{p.name}</strong>
              {p.description && <div>{p.description}</div>}
              {p.tech_stack.length > 0 && (
                <div className="muted small">{t.profile.techStack(p.tech_stack.join(", "))}</div>
              )}
              {p.outcomes.length > 0 && (
                <ul>
                  {p.outcomes.map((o, j) => (
                    <li key={j}>{o}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </Section>

      <Section title={t.profile.skills} count={data.skills.length}>
        <div className="chips">
          {data.skills.map((s, i) => (
            <span
              key={i}
              className="chip neutral"
              title={join(s.category, s.proficiency) || undefined}
            >
              {s.name}
            </span>
          ))}
        </div>
      </Section>

      <Section title={t.profile.education} count={data.education.length}>
        <ul className="entries">
          {data.education.map((e, i) => (
            <li key={i}>
              <strong>{join(e.degree, e.field_of_study) || t.profile.degree}</strong>
              <div>{e.institution}</div>
              <div className="muted small">{dateRange(e.start_date, e.end_date)}</div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title={t.profile.certifications} count={data.certifications.length}>
        <ul>
          {data.certifications.map((c, i) => (
            <li key={i}>{join(c.name, c.issuer, c.date)}</li>
          ))}
        </ul>
      </Section>

      <Section title={t.profile.languages} count={data.languages.length}>
        <ul>
          {data.languages.map((l, i) => (
            <li key={i}>{join(l.name, l.proficiency)}</li>
          ))}
        </ul>
      </Section>

      <Section title={t.profile.awards} count={data.awards.length}>
        <ul>
          {data.awards.map((a, i) => (
            <li key={i}>{join(a.title, a.issuer, a.date)}</li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
