"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, LockKeyhole, Send } from "lucide-react";

import {
  apiRequest,
  formatDate,
  TeacherAnswer,
  TeacherStudentDetail,
} from "@/lib/assignments";

export default function TeacherStudentAssignmentPage() {
  const params = useParams<{ assignmentId: string; studentId: string }>();
  const { assignmentId, studentId } = params;
  const [detail, setDetail] = useState<TeacherStudentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [prompt, setPrompt] = useState("");
  const [expectedAnswer, setExpectedAnswer] = useState("");
  const [rubric, setRubric] = useState("");
  const [maxScore, setMaxScore] = useState("1");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDetail(await apiRequest<TeacherStudentDetail>(
        `/teacher/assignments/${assignmentId}/students/${studentId}`,
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this student's work.");
    } finally {
      setLoading(false);
    }
  }, [assignmentId, studentId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function addQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail?.student.submission_id) return;
    setWorking(true);
    setError("");
    try {
      await apiRequest(`/teacher/assignments/${assignmentId}/questions`, {
        method: "POST",
        body: JSON.stringify({
          student_id: studentId,
          submission_id: detail.student.submission_id,
          prompt: prompt.trim(),
          answer_key: { expected_answer: expectedAnswer.trim() },
          rubric: { criteria: rubric.trim() },
          max_score: Number(maxScore),
        }),
      });
      setPrompt("");
      setExpectedAnswer("");
      setRubric("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add the question.");
    } finally {
      setWorking(false);
    }
  }

  async function setReleased(question: TeacherAnswer, released: boolean) {
    setWorking(true);
    setError("");
    try {
      await apiRequest(
        `/teacher/assignments/${assignmentId}/questions/${question.question_id}/release`,
        { method: "PATCH", body: JSON.stringify({ released }) },
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update question access.");
    } finally {
      setWorking(false);
    }
  }

  if (loading) {
    return <main className="min-h-screen bg-canvas p-8 text-center text-muted">Loading student work…</main>;
  }
  if (error && !detail) {
    return (
      <main className="min-h-screen bg-canvas px-5 py-10 text-white">
        <Link href={`/teacher/assignments/${assignmentId}`} className="text-sm text-lime">← Class overview</Link>
        <p className="mt-6 text-red-200">{error}</p>
      </main>
    );
  }
  if (!detail) return null;

  const { student, submission_code, answers, attempt_result } = detail;
  const understandingScore =
    attempt_result?.comprehension_index ??
    (student.score !== null && student.max_score !== null && student.max_score > 0
      ? (student.score / student.max_score) * 100
      : null);
  const rawScore = student.score;
  const rawMaxScore = student.max_score;
  return (
    <main className="min-h-screen bg-canvas text-white">
      <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <Link
          href={`/teacher/assignments/${assignmentId}`}
          className="inline-flex items-center gap-2 text-sm text-muted hover:text-lime"
        >
          <ArrowLeft size={16} /> Class overview
        </Link>
        <header className="mt-7">
          <p className="text-xs tracking-[0.2em] text-lime">STUDENT SUBMISSION</p>
          <h1 className="mt-2 text-3xl font-semibold">{student.full_name}</h1>
          <p className="mt-2 text-sm text-muted">{student.email} · {student.status}</p>
          {student.submitted_at && (
            <p className="mt-1 text-xs text-muted">Submitted {formatDate(student.submitted_at)}</p>
          )}
        </header>

        {error && <p role="alert" className="mt-5 rounded-lg border border-red-400/30 bg-red-400/5 px-4 py-3 text-sm text-red-200">{error}</p>}

        <section className="mt-7 rounded-2xl border border-line bg-panel p-5 sm:p-6">
          <h2 className="font-semibold">Student code</h2>
          {detail.ai_analysis_status === "failed" && (
            <p role="status" className="mt-3 text-sm text-amber-200">
              Code was saved. AI analysis failed: {detail.ai_analysis_error ?? "No further details are available."}
            </p>
          )}
          {submission_code ? (
            <pre className="mt-4 max-h-[520px] overflow-auto rounded-xl border border-line bg-canvas p-4 text-xs leading-6 text-zinc-200">
              <code>{submission_code}</code>
            </pre>
          ) : (
            <p className="mt-3 text-sm text-muted">This student has not submitted code.</p>
          )}
        </section>

        {detail.code_review && (
          <section className="mt-7 rounded-2xl border border-lime/20 bg-panel p-5 sm:p-6">
            <p className="text-xs tracking-[0.15em] text-lime">AI CODE REVIEW</p>
            <h2 className="mt-2 font-semibold">{detail.code_review.summary}</h2>
            <ReviewList title="Code improvements" items={detail.code_review.code_suggestions} />
            <ReviewList title="Understanding to practise" items={detail.code_review.understanding_suggestions} />
          </section>
        )}

        <section className="mt-7 rounded-2xl border border-lime/25 bg-panel p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs tracking-[0.15em] text-lime">INDIVIDUAL MARKS CARD</p>
              <h2 className="mt-2 font-semibold">Code understanding result</h2>
            </div>
            <p className="text-xs text-muted">{student.status}</p>
          </div>
          {understandingScore === null ? (
            <p className="mt-5 rounded-lg border border-line bg-canvas p-4 text-sm text-muted">
              Marks are pending. The card will show this student&apos;s evaluated result after their released-question answers have been graded.
            </p>
          ) : (
            <>
              <div className="mt-5 flex flex-wrap items-end gap-4">
                <p className="text-4xl font-semibold text-lime">
                  {Math.round(Number(understandingScore))}
                  <span className="ml-2 text-xl text-muted">/ 100</span>
                </p>
                {rawScore !== null && rawMaxScore !== null && (
                  <p className="pb-1 text-sm text-muted">
                    {rawScore} / {rawMaxScore} marks
                  </p>
                )}
              </div>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <ResultFact
                  label="Answers needing review"
                  value={String(attempt_result?.needs_review_count ?? answers.filter((answer) => answer.needs_review).length)}
                />
                <ResultFact
                  label="Oral follow-up"
                  value={attempt_result
                    ? attempt_result.flag_oral_followup ? "Flagged" : "Not flagged"
                    : "Not assessed"}
                />
              </div>
              {attempt_result && (
                <p className="mt-4 text-xs text-muted">
                  Saved {formatDate(attempt_result.computed_at)}. Score is based on the percentage of available marks awarded.
                </p>
              )}
            </>
          )}
        </section>

        <section className="mt-7 rounded-2xl border border-line bg-panel p-5 sm:p-6">
          <div className="flex items-start gap-3">
            <LockKeyhole className="mt-0.5 text-lime" size={18} />
            <div>
              <h2 className="font-semibold">Questions and saved results</h2>
              <p className="mt-1 text-xs leading-5 text-muted">
                AI-drafted and teacher-authored questions stay hidden as drafts until you release them to this student.
              </p>
            </div>
          </div>
          {answers.length ? (
            <div className="mt-5 space-y-4">
              {answers.map((answer) => (
                <article key={answer.question_id} className="rounded-xl border border-line bg-canvas p-4">
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                    <div>
                      <p className="text-xs text-lime">QUESTION {answer.order_idx}</p>
                      <p className="mt-2 text-sm leading-6">{answer.prompt}</p>
                    </div>
                    <button
                      disabled={working}
                      onClick={() => void setReleased(answer, !answer.released)}
                      className={`shrink-0 rounded-lg border px-3 py-2 text-xs disabled:opacity-50 ${
                        answer.released
                          ? "border-amber-300/30 text-amber-200 hover:bg-amber-300/5"
                          : "border-lime/30 text-lime hover:bg-lime/5"
                      }`}
                    >
                      {answer.released ? "Revoke access" : "Release question"}
                    </button>
                  </div>
                  <div className="mt-4 rounded-lg border border-line bg-panel p-3">
                    <p className="text-[10px] uppercase tracking-wider text-muted">Student answer</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-200">
                      {answer.answer_text || "No answer yet."}
                    </p>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted">
                    <span>
                      {answer.score === null
                        ? "Pending evaluation"
                        : `Saved score: ${answer.score} / ${answer.max_score}`}
                    </span>
                    {answer.needs_review && <span className="text-amber-200">Needs review</span>}
                  </div>
                  {answer.evidence && <p className="mt-2 text-xs leading-5 text-muted">Evidence: {answer.evidence}</p>}
                  {answer.feedback && <p className="mt-2 text-sm text-zinc-300">{answer.feedback}</p>}
                </article>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm text-muted">
              No prepared questions yet. Add one below; it will remain hidden until you release it.
            </p>
          )}

          {student.submission_id && (
            <form onSubmit={addQuestion} className="mt-6 grid gap-4 border-t border-line pt-6">
              <h3 className="text-sm font-semibold">Prepare a question</h3>
              <label className="text-sm">
                Question
                <textarea
                  required
                  maxLength={10_000}
                  rows={2}
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 outline-none focus:border-lime"
                />
              </label>
              <label className="text-sm">
                Expected answer (private until evaluation)
                <textarea
                  required
                  rows={2}
                  value={expectedAnswer}
                  onChange={(event) => setExpectedAnswer(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 outline-none focus:border-lime"
                />
              </label>
              <div className="grid gap-4 sm:grid-cols-[1fr_160px]">
                <label className="text-sm">
                  Grading rubric (private)
                  <textarea
                    required
                    rows={2}
                    value={rubric}
                    onChange={(event) => setRubric(event.target.value)}
                    className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 outline-none focus:border-lime"
                  />
                </label>
                <label className="text-sm">
                  Maximum score
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    required
                    value={maxScore}
                    onChange={(event) => setMaxScore(event.target.value)}
                    className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 outline-none focus:border-lime"
                  />
                </label>
              </div>
              <button
                disabled={working}
                className="inline-flex w-fit items-center gap-2 rounded-lg bg-lime px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50"
              >
                <Send size={15} /> {working ? "Saving…" : "Save as draft"}
              </button>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}

function ResultFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-canvas p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-2 text-lg font-semibold">{value}</p>
    </div>
  );
}

function ReviewList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="mt-5">
      <h3 className="text-sm font-medium">{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-zinc-300">
        {items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
      </ul>
    </div>
  );
}
