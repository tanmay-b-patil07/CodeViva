"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, CircleHelp, FileCode2, LockKeyhole, Play } from "lucide-react";

import {
  apiRequest,
  formatDate,
  StudentAssignmentDetail,
  StudentAttempt,
  StudentAttemptDetail,
  StudentQuestion,
} from "@/lib/assignments";

interface CodeSubmissionResponse {
  id: string;
  filename: string;
  created_at: string;
  code_facts: Record<string, unknown>;
  ai_analysis_status: "pending" | "complete" | "failed";
  ai_analysis_error: string | null;
}

export default function StudentAssignmentPage() {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const [assignment, setAssignment] = useState<StudentAssignmentDetail | null>(null);
  const [attemptDetail, setAttemptDetail] = useState<StudentAttemptDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submittingCode, setSubmittingCode] = useState(false);
  const [code, setCode] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const detail = await apiRequest<StudentAssignmentDetail>(
        `/student/assignments/${assignmentId}`,
      );
      setAssignment(detail);
      setCode(detail.submission_code ?? "");
      if (detail.questions_released) {
        const attempt = await apiRequest<StudentAttemptDetail | null>(
          `/student/assignments/${assignmentId}/attempt`,
        );
        setAttemptDetail(attempt);
        setAnswers(Object.fromEntries(
          (attempt?.answers ?? []).map((answer) => [answer.question_id, answer.answer_text]),
        ));
      } else {
        setAttemptDetail(null);
        setAnswers({});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this assignment.");
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submitCode() {
    if (!assignment || !code.trim()) {
      setError("Type your code before requesting AI analysis.");
      return;
    }
    if (new TextEncoder().encode(code).length > 50_000) {
      setError("Code must be no larger than 50,000 UTF-8 bytes for AI analysis.");
      return;
    }
    setSubmittingCode(true);
    setError("");
    setNotice("");
    try {
      const submitted = await apiRequest<CodeSubmissionResponse>(
        "/student/submissions/code",
        {
          method: "POST",
          body: JSON.stringify({
            code,
            language: assignment.language,
            assignment_id: assignment.id,
          }),
        },
      );
      setNotice(submitted.ai_analysis_status === "complete"
        ? `${submitted.filename} saved and analyzed. Your teacher can review and release the generated questions.`
        : `${submitted.filename} was saved, but AI analysis failed: ${submitted.ai_analysis_error ?? "Please try again later."}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Code analysis failed.");
    } finally {
      setSubmittingCode(false);
    }
  }

  async function beginQuestions() {
    setStarting(true);
    setError("");
    try {
      await apiRequest<StudentAttempt>(
        `/student/assignments/${assignmentId}/attempts`,
        { method: "POST" },
      );
      const current = await apiRequest<StudentAttemptDetail>(
        `/student/assignments/${assignmentId}/attempt`,
      );
      setAttemptDetail(current);
      setAnswers(Object.fromEntries(
        current.answers.map((answer) => [answer.question_id, answer.answer_text]),
      ));
      setNotice("Your question attempt is ready.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start questions.");
    } finally {
      setStarting(false);
    }
  }

  async function saveAnswer(question: StudentQuestion) {
    if (!attemptDetail) return;
    setError("");
    setNotice("");
    try {
      const saved = await apiRequest<{ question_id: string; answer_text: string }>(
        `/student/assignments/${assignmentId}/attempts/${attemptDetail.attempt.id}/answers`,
        {
          method: "PUT",
          body: JSON.stringify({
            question_id: question.id,
            answer_text: answers[question.id] ?? "",
          }),
        },
      );
      setAnswers((current) => ({ ...current, [saved.question_id]: saved.answer_text }));
      setNotice("Answer saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the answer.");
    }
  }

  async function submitAttempt() {
    if (!attemptDetail) return;
    setError("");
    setNotice("");
    try {
      const submitted = await apiRequest<StudentAttempt>(
        `/student/assignments/${assignmentId}/attempts/${attemptDetail.attempt.id}/submit`,
        { method: "POST" },
      );
      setAttemptDetail((current) => current ? { ...current, attempt: submitted } : current);
      setNotice("Your answers have been submitted.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit your answers.");
    }
  }

  if (loading) {
    return <main className="min-h-screen bg-[#10110F] p-8 text-center text-zinc-400">Loading assignment…</main>;
  }
  if (!assignment) {
    return (
      <main className="min-h-screen bg-[#10110F] px-5 py-10 text-white">
        <Link href="/student/assignments" className="text-sm text-[#D5FF62]">← Assigned work</Link>
        <p role="alert" className="mt-6 text-red-200">{error || "Assignment not found."}</p>
      </main>
    );
  }
  const isPastDue = assignment.status === "Past due";
  const isSubmitted = !!attemptDetail?.attempt.submitted_at;
  const gradedAnswers = (attemptDetail?.answers ?? []).filter(
    (answer) => answer.score !== null && answer.max_score !== null,
  );
  const totalScore = gradedAnswers.reduce((sum, answer) => sum + (answer.score ?? 0), 0);
  const totalMaxScore = gradedAnswers.reduce((sum, answer) => sum + (answer.max_score ?? 0), 0);
  const scorePercent = totalMaxScore > 0 ? Math.round((totalScore / totalMaxScore) * 100) : null;
  const understandingScore =
    attemptDetail?.attempt_result?.comprehension_index ?? scorePercent;

  return (
    <main className="min-h-screen bg-[#10110F] text-[#F3F4EF]">
      <div className="mx-auto max-w-5xl px-5 py-9 sm:px-8">
        <Link href="/student/assignments" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-[#D5FF62]">
          <ArrowLeft size={16} /> Assigned work
        </Link>
        <header className="mt-7">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-[#414832] px-2 py-1 text-[10px] text-[#D5FF62]">{assignment.language.toUpperCase()}</span>
            <span className="rounded-full border border-[#2A2D27] px-2.5 py-1 text-[10px] text-zinc-300">{assignment.status}</span>
          </div>
          <h1 className="mt-4 text-3xl font-semibold sm:text-4xl">{assignment.title}</h1>
          <p className="mt-3 text-sm text-zinc-400">
            {assignment.teacher_name} · {assignment.group_name} · Due {formatDate(assignment.due_at)}
          </p>
          {assignment.description && <p className="mt-5 max-w-3xl whitespace-pre-wrap text-sm leading-6 text-zinc-300">{assignment.description}</p>}
          {assignment.instructions && (
            <div className="mt-4 rounded-xl border border-[#2A2D27] bg-[#151713] p-4 text-sm leading-6 text-zinc-300">
              <strong className="text-white">Instructions</strong>
              <p className="mt-2 whitespace-pre-wrap">{assignment.instructions}</p>
            </div>
          )}
        </header>

        {error && <p role="alert" className="mt-6 rounded-lg border border-red-400/30 bg-red-400/5 px-4 py-3 text-sm text-red-200">{error}</p>}
        {notice && <p role="status" className="mt-6 rounded-lg border border-[#414832] bg-[#20241B] px-4 py-3 text-sm text-[#D5FF62]">{notice}</p>}

        <section className="mt-7 rounded-2xl border border-[#2A2D27] bg-[#151713] p-5 sm:p-6">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <FileCode2 className="mt-0.5 text-[#D5FF62]" size={19} />
              <div>
                <h2 className="font-semibold">Write and analyze your code</h2>
                <p className="mt-1 text-xs leading-5 text-zinc-500">
                  Type your {assignment.language} code below. AI feedback and draft questions are saved with your submission.
                </p>
                {assignment.submission_filename && (
                  <p className="mt-2 text-xs text-zinc-300">
                    Latest analysis: {assignment.submission_filename}
                    {assignment.submitted_at ? ` · ${formatDate(assignment.submitted_at)}` : ""}
                  </p>
                )}
                {assignment.ai_analysis_status === "failed" && (
                  <p role="status" className="mt-2 text-xs text-amber-200">
                    Your code is saved and visible to your teacher, but AI analysis did not complete: {assignment.ai_analysis_error ?? "Please contact your teacher."}
                  </p>
                )}
              </div>
            </div>
          </div>
          <textarea
            spellCheck={false}
            value={code}
            maxLength={50_000}
            disabled={assignment.questions_released || !!attemptDetail || isPastDue || submittingCode}
            onChange={(event) => setCode(event.target.value)}
            className="mt-5 min-h-[360px] w-full resize-y rounded-xl border border-[#2A2D27] bg-[#10110F] p-4 font-mono text-xs leading-6 text-[#D5FFB1] outline-none focus:border-[#D5FF62] disabled:opacity-60 sm:text-sm"
            placeholder={`Type your ${assignment.language} code here…`}
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <span className="text-[11px] text-zinc-500">
              {code.split("\n").length} lines · {new TextEncoder().encode(code).length} / 50,000 bytes
            </span>
            <button
              disabled={isPastDue || assignment.questions_released || !!attemptDetail || submittingCode || !code.trim()}
              onClick={() => void submitCode()}
              className="inline-flex items-center gap-2 rounded-lg bg-[#D5FF62] px-4 py-2.5 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Play size={15} />
              {submittingCode ? "Analyzing code and drafting questions…" : "Analyze and submit code"}
            </button>
          </div>
          {(assignment.questions_released || attemptDetail) && (
            <p className="mt-3 text-xs text-amber-200">
              Code is locked after questions are released so the marks and feedback remain tied to this submission.
            </p>
          )}
        </section>

        {assignment.code_review && (
          <section className="mt-7 rounded-2xl border border-[#414832] bg-[#20241B] p-5 sm:p-6">
            <p className="text-xs tracking-[0.15em] text-[#D5FF62]">AI CODE REVIEW</p>
            <h2 className="mt-2 font-semibold">{assignment.code_review.summary}</h2>
            <ReviewList title="Code improvements" items={assignment.code_review.code_suggestions} />
            <ReviewList title="Understanding to practise" items={assignment.code_review.understanding_suggestions} />
          </section>
        )}

        <section className="mt-7 overflow-hidden rounded-2xl border border-[#2A2D27] bg-[#151713]">
          <div className="border-b border-[#2A2D27] px-5 py-5 sm:px-6">
            <div className="flex items-start gap-3">
              {assignment.questions_released
                ? <CircleHelp className="mt-0.5 text-[#D5FF62]" size={19} />
                : <LockKeyhole className="mt-0.5 text-zinc-500" size={19} />}
              <div>
                <h2 className="font-semibold">Assignment questions</h2>
                <p className="mt-1 text-xs leading-5 text-zinc-500">
                  {assignment.questions_released
                    ? `${assignment.question_count} question(s) released by your teacher.`
                    : "Questions are not available until your teacher explicitly releases them."}
                </p>
              </div>
            </div>
          </div>
          {!assignment.questions_released ? (
            <div className="px-5 py-8 text-center text-sm text-zinc-500">
              Questions locked · This assignment information does not include unreleased question content.
            </div>
          ) : !attemptDetail ? (
            <div className="p-5 sm:p-6">
              <p className="text-sm text-zinc-400">
                Questions are available. Begin when you are ready; your answers will be saved to your account.
              </p>
              <button
                disabled={starting || isPastDue}
                onClick={() => void beginQuestions()}
                className="mt-4 rounded-lg bg-[#D5FF62] px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50"
              >
                {starting ? "Starting…" : "Begin questions"}
              </button>
            </div>
          ) : (
            <div className="space-y-4 p-5 sm:p-6">
              <p className="text-xs text-zinc-500">
                {isSubmitted
                  ? `Submitted ${formatDate(attemptDetail.attempt.submitted_at)}`
                  : `Attempt deadline ${formatDate(attemptDetail.attempt.deadline_at)}`}
              </p>
              {assignment.questions.map((question) => (
                <article key={question.id} className="rounded-xl border border-[#2A2D27] bg-[#121310] p-4">
                  <p className="text-[10px] tracking-wider text-[#D5FF62]">QUESTION {question.order_idx}</p>
                  <p className="mt-3 text-sm leading-6">{question.prompt}</p>
                  <p className="mt-3 rounded-lg border border-[#414832] bg-[#20241B] px-3 py-2.5 text-xs leading-5 text-[#D5FFB1]">
                    <span className="font-semibold text-[#D5FF62]">Hint: </span>
                    {question.hint}
                  </p>
                  {question.options?.length ? (
                    <div className="mt-4 space-y-2">
                      {question.options.map((option) => (
                        <label key={option} className="flex cursor-pointer items-center gap-3 rounded-lg border border-[#2A2D27] p-3 text-sm text-zinc-300">
                          <input
                            type="radio"
                            name={question.id}
                            value={option}
                            checked={answers[question.id] === option}
                            disabled={isSubmitted}
                            onChange={() => setAnswers((current) => ({ ...current, [question.id]: option }))}
                          />
                          {option}
                        </label>
                      ))}
                    </div>
                  ) : (
                    <textarea
                      rows={3}
                      value={answers[question.id] ?? ""}
                      disabled={isSubmitted}
                      onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))}
                      className="mt-4 w-full rounded-lg border border-[#2A2D27] bg-[#10110F] px-3 py-2.5 text-sm outline-none focus:border-[#D5FF62] disabled:opacity-60"
                      placeholder="Write your answer"
                    />
                  )}
                  {!isSubmitted && (
                    <button
                      onClick={() => void saveAnswer(question)}
                      className="mt-3 rounded-md border border-[#414832] px-3 py-2 text-xs text-[#D5FF62] hover:bg-[#20241B]"
                    >
                      Save answer
                    </button>
                  )}
                </article>
              ))}
              {!isSubmitted && (
                <button
                  onClick={() => void submitAttempt()}
                  className="rounded-lg bg-[#D5FF62] px-4 py-2.5 text-sm font-semibold text-black hover:bg-[#E2FF94]"
                >
                  Submit answers
                </button>
              )}
              {isSubmitted && <p className="flex items-center gap-2 text-sm text-[#D5FF62]"><CheckCircle2 size={16} /> Answers submitted</p>}
            </div>
          )}
        </section>

        {isSubmitted && (
          <section className="mt-7 rounded-2xl border border-[#414832] bg-[#20241B] p-5 sm:p-6">
            <p className="text-xs tracking-[0.15em] text-[#D5FF62]">RESULT SHEET</p>
            {scorePercent === null ? (
              <p className="mt-3 text-sm text-zinc-300">Evaluation is pending; your teacher will see the submitted answers.</p>
            ) : (
              <>
                <div className="mt-4 flex flex-wrap items-end gap-4">
                  <p className="text-4xl font-semibold text-[#D5FF62]">{totalScore} <span className="text-xl text-zinc-400">/ {totalMaxScore}</span></p>
                  <p className="pb-1 text-sm text-zinc-300">{scorePercent}% overall</p>
                </div>
                <div className="mt-5 rounded-xl border border-[#414832] bg-[#10110F] p-4">
                  <p className="text-xs uppercase tracking-[0.15em] text-zinc-400">
                    Code understanding
                  </p>
                  <p className="mt-2 text-3xl font-semibold text-[#D5FF62]">
                    {understandingScore === null
                      ? "Pending"
                      : `${Math.round(Number(understandingScore))} / 100`}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Based on your evaluated answers about the submitted code.
                    {attemptDetail?.attempt_result
                      ? ` Evaluated ${formatDate(attemptDetail.attempt_result.computed_at)}.`
                      : ""}
                  </p>
                  {!!attemptDetail?.attempt_result?.needs_review_count && (
                    <p className="mt-2 text-xs text-amber-200">
                      {attemptDetail.attempt_result.needs_review_count} answer(s) flagged for teacher review.
                    </p>
                  )}
                </div>
                <div className="mt-5 space-y-4">
                  {gradedAnswers.map((answer) => (
                    <article key={answer.id} className="rounded-xl border border-[#2A2D27] bg-[#10110F] p-4">
                      <div className="flex flex-wrap justify-between gap-2 text-sm">
                        <span>Question result</span>
                        <strong className="text-[#D5FF62]">{answer.score} / {answer.max_score}</strong>
                      </div>
                      {answer.feedback && <p className="mt-3 text-sm leading-6 text-zinc-300">{answer.feedback}</p>}
                      {answer.evidence && <p className="mt-2 text-xs leading-5 text-zinc-500">Evidence: {answer.evidence}</p>}
                      {answer.needs_review && <p className="mt-2 text-xs text-amber-200">Flagged for teacher review</p>}
                    </article>
                  ))}
                </div>
                <p className="mt-4 text-xs text-zinc-500">Your teacher can view the same marks, answers, and feedback.</p>
              </>
            )}
          </section>
        )}
      </div>
    </main>
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
