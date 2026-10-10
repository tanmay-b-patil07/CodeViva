"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Braces, Play, Sparkles } from "lucide-react";

import {
  apiRequest,
  defaultCodeExtension,
  CodeReview,
  SUPPORTED_CODE_LANGUAGES,
} from "@/lib/assignments";

interface CodeAnalysisSubmission {
  id: string;
  filename: string;
  code_facts: Record<string, unknown> & { ai_review?: CodeReview };
  created_at: string;
  ai_analysis_status: "pending" | "complete" | "failed";
  ai_analysis_error: string | null;
  practice_session_id: string | null;
}

export default function StudentUploadPage() {
  const router = useRouter();
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState("");
  const [submission, setSubmission] = useState<CodeAnalysisSubmission | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");

  async function analyzeCode() {
    const extension = defaultCodeExtension(language);
    if (!extension) {
      setError("Choose one of the supported analysis languages.");
      return;
    }
    if (new TextEncoder().encode(code).length > 50_000) {
      setError("Code must be no larger than 50,000 UTF-8 bytes for AI analysis.");
      return;
    }
    if (!code.trim()) {
      setError("Add source code before requesting analysis.");
      return;
    }
    if (new TextEncoder().encode(code).length > 1_000_000) {
      setError("Code must be no larger than 1 MB.");
      return;
    }
    setAnalyzing(true);
    setError("");
    setSubmission(null);
    try {
      const result = await apiRequest<CodeAnalysisSubmission>(
        "/student/submissions/code",
        {
          method: "POST",
          body: JSON.stringify({ code, language }),
        },
      );
      setSubmission(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Code analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#10110F] text-[#F3F4EF]">
      <header className="border-b border-[#2A2D27]">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/student" className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#D5FF62] text-black"><Braces size={22} /></span>
            <span className="font-bold">codeviva<span className="text-[#D5FF62]">.</span></span>
          </Link>
          <Link href="/student" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-[#D5FF62]">
            <ArrowLeft size={15} /> Dashboard
          </Link>
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <div>
          <p className="mb-3 text-xs tracking-[0.2em] text-[#D5FF62]">PUBLIC PRACTICE WORKSPACE</p>
          <h1 className="text-3xl font-semibold sm:text-4xl">Open practice session</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-zinc-400">
            Enter code to generate AI comprehension questions, answer them, and get AI-scored feedback. Your code and practice results are saved to your account.
          </p>
        </div>

        {error && <p role="alert" className="mt-6 rounded-lg border border-red-400/30 bg-red-400/5 px-4 py-3 text-sm text-red-200">{error}</p>}

        <div className="mt-7 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="overflow-hidden rounded-2xl border border-[#2A2D27] bg-[#151713]">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#2A2D27] px-4 py-4 sm:px-5">
              <label className="text-xs text-zinc-400">
                Language
                <select
                  value={language}
                  onChange={(event) => {
                    const next = event.target.value;
                    setLanguage(next);
                    setSubmission(null);
                  }}
                  className="ml-2 rounded-md border border-[#2A2D27] bg-[#10110F] px-2.5 py-2 text-xs text-white outline-none focus:border-[#D5FF62]"
                >
                  {SUPPORTED_CODE_LANGUAGES.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="flex items-center gap-2 border-b border-[#2A2D27] px-4 py-3">
              <span className="h-2 w-2 rounded-full bg-[#D5FF62]" />
              <span className="font-mono text-[11px] text-zinc-400">{`practice${defaultCodeExtension(language)}`}</span>
            </div>
            <textarea
              spellCheck={false}
              value={code}
              onChange={(event) => {
                setCode(event.target.value);
                setSubmission(null);
              }}
              className="min-h-[380px] w-full resize-y bg-[#10110F] p-4 font-mono text-xs leading-6 text-[#D5FFB1] outline-none placeholder:text-zinc-600 sm:text-sm"
              placeholder="Type or paste source code here."
            />
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#2A2D27] px-4 py-3 sm:px-5">
              <span className="text-[11px] text-zinc-500">{code.split("\n").length} lines · {new TextEncoder().encode(code).length} bytes</span>
              <button
                disabled={analyzing || !code.trim()}
                onClick={() => void analyzeCode()}
                className="inline-flex items-center gap-2 rounded-lg bg-[#D5FF62] px-4 py-2.5 text-sm font-semibold text-black disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Play size={15} /> {analyzing ? "Saving code and generating questions…" : "Start AI practice"}
              </button>
            </div>
          </section>

          <section className="min-w-0 rounded-2xl border border-[#2A2D27] bg-[#151713]">
            <div className="flex items-center gap-3 border-b border-[#2A2D27] px-5 py-4">
              <Sparkles size={18} className="text-[#D5FF62]" />
              <div>
                <h2 className="text-sm font-medium">Analysis output</h2>
                <p className="mt-1 text-[11px] text-zinc-500">Language analysis and AI improvement suggestions</p>
              </div>
            </div>
            {analyzing ? (
              <p className="p-6 text-sm text-zinc-400">Analyzing your code…</p>
            ) : submission ? (
              <div className="p-5">
                <p role="status" className="text-xs text-[#D5FF62]">
                  Code saved · {submission.filename}
                  {submission.ai_analysis_status === "failed" && ` · ${submission.ai_analysis_error ?? "AI generation failed"}`}
                </p>
                {submission.practice_session_id && (
                  <button
                    type="button"
                    onClick={() => router.push(`/student/practice/${submission.practice_session_id}`)}
                    className="mt-4 rounded-lg bg-[#D5FF62] px-4 py-2.5 text-sm font-semibold text-black"
                  >
                    {submission.ai_analysis_status === "complete" ? "Open generated questions" : "View saved practice session"}
                  </button>
                )}
                {submission.code_facts.ai_review && (
                  <div className="mt-4 rounded-lg border border-[#414832] bg-[#20241B] p-4 text-sm">
                    <p className="font-medium">{submission.code_facts.ai_review.summary}</p>
                    <SuggestionList
                      title="Code improvements"
                      items={submission.code_facts.ai_review.code_suggestions}
                    />
                    <SuggestionList
                      title="Understanding to practise"
                      items={submission.code_facts.ai_review.understanding_suggestions}
                    />
                  </div>
                )}
                <details className="mt-4">
                  <summary className="cursor-pointer text-xs text-zinc-400">Show structural code facts</summary>
                  <pre className="mt-3 max-h-[620px] overflow-auto rounded-lg border border-[#2A2D27] bg-[#10110F] p-4 text-[11px] leading-5 text-zinc-300">
                  <code>{JSON.stringify(submission.code_facts, null, 2)}</code>
                  </pre>
                </details>
              </div>
            ) : (
              <div className="flex min-h-[320px] flex-col items-center justify-center px-7 py-10 text-center">
                <div className="grid h-12 w-12 place-items-center rounded-xl border border-[#414832] bg-[#20241B] text-[#D5FF62]"><Sparkles size={20} /></div>
                <p className="mt-4 text-sm font-medium">No analysis yet</p>
                <p className="mt-2 max-w-sm text-xs leading-5 text-zinc-500">
                  Your private practice session and answers are saved and are separate from teacher assignments.
                </p>
              </div>
            )}
          </section>
        </div>
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
