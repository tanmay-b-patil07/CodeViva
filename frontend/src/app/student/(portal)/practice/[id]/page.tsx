"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, CircleHelp, Sparkles } from "lucide-react";

import { apiRequest, CodeReview } from "@/lib/assignments";

interface PracticeQuestion {
  id: string;
  order_idx: number;
  prompt: string;
  line_refs: { line: number }[];
  answer_text: string | null;
  score: number | null;
  max_score: number;
  feedback: string | null;
  grading_status: "pending" | "complete" | "failed";
}

interface PracticeSession {
  id: string;
  status: "generating" | "ready" | "failed";
  created_at: string;
  code: string;
  language: string;
  code_facts: Record<string, unknown> & { ai_review?: CodeReview };
  questions: PracticeQuestion[];
  error: string | null;
}

interface AnswerResult {
  question_id: string;
  answer_text: string;
  score: number | null;
  max_score: number;
  feedback: string | null;
  grading_status: "pending" | "complete" | "failed";
}

export default function PracticeSessionPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<PracticeSession | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [workingId, setWorkingId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError("");
    try {
      const result = await apiRequest<PracticeSession>(`/student/practice-sessions/${id}`);
      setSession(result);
      setAnswers(Object.fromEntries(
        result.questions.map((question) => [question.id, question.answer_text ?? ""]),
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the practice session.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submitAnswer(questionId: string) {
    setWorkingId(questionId);
    setError("");
    try {
      const result = await apiRequest<AnswerResult>(
        `/student/practice-sessions/${id}/questions/${questionId}/answer`,
        {
          method: "PUT",
          body: JSON.stringify({ answer_text: answers[questionId] ?? "" }),
        },
      );
      setSession((current) => current ? {
        ...current,
        questions: current.questions.map((question) =>
          question.id === questionId
            ? { ...question, ...result }
            : question,
        ),
      } : current);
      if (result.grading_status === "failed") {
        setError(result.feedback ?? "Your answer was saved, but AI grading failed.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save and grade your answer.");
    } finally {
      setWorkingId("");
    }
  }

  if (loading) {
    return <main className="min-h-screen bg-[#10110F] p-8 text-center text-zinc-400">Loading practice session…</main>;
  }
  if (!session) {
    return (
      <main className="min-h-screen bg-[#10110F] px-5 py-10 text-white">
        <Link href="/student/upload" className="text-sm text-[#D5FF62]">← Open practice</Link>
        <p role="alert" className="mt-6 text-red-200">{error || "Practice session not found."}</p>
      </main>
    );
  }

  const graded = session.questions.filter((question) => question.score !== null);
  const totalScore = graded.reduce((sum, question) => sum + (question.score ?? 0), 0);
  const totalMax = graded.reduce((sum, question) => sum + question.max_score, 0);

  return (
    <main className="min-h-screen bg-[#10110F] text-[#F3F4EF]">
      <div className="mx-auto max-w-5xl px-5 py-9 sm:px-8">
        <Link href="/student/upload" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-[#D5FF62]">
          <ArrowLeft size={16} /> Open practice
        </Link>
        <header className="mt-7">
          <p className="text-xs tracking-[0.2em] text-[#D5FF62]">SAVED PRACTICE SESSION · {session.language.toUpperCase()}</p>
          <h1 className="mt-3 text-3xl font-semibold">Code comprehension practice</h1>
          <p className="mt-2 text-sm text-zinc-400">
            {session.status === "ready"
              ? `${session.questions.length} AI-generated question(s). Your answers are saved and evaluated by AI.`
              : "Your code has been saved, but question generation did not complete."}
          </p>
        </header>

        {error && <p role="alert" className="mt-6 rounded-lg border border-amber-300/30 bg-amber-300/5 px-4 py-3 text-sm text-amber-100">{error}</p>}
        {session.status === "failed" && session.error && (
          <p role="status" className="mt-5 rounded-lg border border-amber-300/30 bg-amber-300/5 px-4 py-3 text-sm text-amber-100">
            Code is saved. AI could not generate questions: {session.error}
          </p>
        )}

        {session.code_facts.ai_review && (
          <section className="mt-7 rounded-2xl border border-[#414832] bg-[#20241B] p-5">
            <div className="flex items-center gap-2 text-[#D5FF62]"><Sparkles size={17} /><h2 className="text-sm font-semibold">AI code review</h2></div>
            <p className="mt-3 text-sm text-zinc-200">{session.code_facts.ai_review.summary}</p>
            <SuggestionList title="Code improvements" items={session.code_facts.ai_review.code_suggestions} />
            <SuggestionList title="Understanding to practise" items={session.code_facts.ai_review.understanding_suggestions} />
          </section>
        )}

        <section className="mt-7 rounded-2xl border border-[#2A2D27] bg-[#151713] p-5">
          <h2 className="font-semibold">Saved source code</h2>
          <pre className="mt-4 max-h-[420px] overflow-auto rounded-xl border border-[#2A2D27] bg-[#10110F] p-4 text-xs leading-6 text-[#D5FFB1]">
            <code>{session.code}</code>
          </pre>
        </section>

        {graded.length > 0 && (
          <section className="mt-7 flex items-center gap-3 rounded-2xl border border-[#414832] bg-[#20241B] p-5">
            <CheckCircle2 className="text-[#D5FF62]" />
            <div>
              <h2 className="font-semibold">Practice marks</h2>
              <p className="mt-1 text-sm text-zinc-300">
                {totalScore} / {totalMax} · {totalMax > 0 ? Math.round(totalScore / totalMax * 100) : 0}%
              </p>
            </div>
          </section>
        )}

        <section className="mt-7 space-y-5">
          <div className="flex items-center gap-2">
            <CircleHelp className="text-[#D5FF62]" size={19} />
            <h2 className="text-lg font-semibold">Questions and answers</h2>
          </div>
          {session.questions.map((question) => (
            <article key={question.id} className="rounded-2xl border border-[#2A2D27] bg-[#151713] p-5 sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="font-medium">Question {question.order_idx}</h3>
                <span className="text-xs text-zinc-400">Up to {question.max_score} marks</span>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-200">{question.prompt}</p>
              {question.line_refs.length > 0 && (
                <p className="mt-2 text-xs text-zinc-500">Code lines: {question.line_refs.map(({ line }) => line).join(", ")}</p>
              )}
              <textarea
                value={answers[question.id] ?? ""}
                onChange={(event) => {
                  const answerText = event.target.value;
                  setAnswers((current) => ({ ...current, [question.id]: answerText }));
                  setSession((current) => current ? {
                    ...current,
                    questions: current.questions.map((item) =>
                      item.id === question.id
                        ? { ...item, answer_text: answerText, score: null, feedback: null, grading_status: "pending" }
                        : item,
                    ),
                  } : current);
                }}
                maxLength={100_000}
                disabled={workingId === question.id}
                className="mt-4 min-h-28 w-full rounded-xl border border-[#2A2D27] bg-[#10110F] p-4 text-sm leading-6 text-white outline-none focus:border-[#D5FF62]"
                placeholder="Explain your reasoning…"
              />
              <button
                type="button"
                onClick={() => void submitAnswer(question.id)}
                disabled={workingId === question.id || !answers[question.id]?.trim()}
                className="mt-3 rounded-lg bg-[#D5FF62] px-4 py-2.5 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-50"
              >
                {workingId === question.id ? "Saving and evaluating…" : "Save and evaluate answer"}
              </button>
              {question.grading_status === "complete" && (
                <div className="mt-4 rounded-lg border border-[#414832] bg-[#20241B] p-4">
                  <p className="text-sm font-semibold text-[#D5FF62]">AI score: {question.score} / {question.max_score}</p>
                  {question.feedback && <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-zinc-300">{question.feedback}</p>}
                </div>
              )}
              {question.grading_status === "failed" && question.feedback && (
                <p role="status" className="mt-4 text-sm text-amber-200">{question.feedback}</p>
              )}
            </article>
          ))}
          {session.status === "ready" && session.questions.length === 0 && (
            <p className="rounded-xl border border-amber-300/30 p-4 text-sm text-amber-100">
              The AI returned no practice questions. Your code is saved; try starting another session.
            </p>
          )}
        </section>
      </div>
    </main>
  );
}

function SuggestionList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="mt-4">
      <h3 className="text-xs font-semibold text-[#D5FF62]">{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-5 text-zinc-300">
        {items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
      </ul>
    </div>
  );
}
