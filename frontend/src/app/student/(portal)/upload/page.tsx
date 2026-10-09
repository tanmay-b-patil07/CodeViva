
"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Braces,
  Check,
  ChevronDown,
  CircleHelp,
  Code2,
  FileCode2,
  Play,
  RotateCcw,
  Sparkles,
  Terminal,
  X,
} from "lucide-react";

const initialCode = `def mystery(nums):
    result = 0
    for n in nums:
        if n % 2 == 0:
            result += n
    return result

values = [3, 8, 5, 12, 7]
print(mystery(values))`;

const questions = [
  {
    category: "LOGIC",
    prompt: "What does the mystery() function return?",
    options: [
      "The sum of every number",
      "The sum of even numbers",
      "The count of even numbers",
      "The largest even number",
    ],
    correct: 1,
    explanation:
      "The condition n % 2 == 0 selects even numbers, and result += n adds each selected value.",
  },
  {
    category: "EXECUTION",
    prompt: "What does print(mystery(values)) display?",
    options: ["15", "20", "23", "35"],
    correct: 1,
    explanation:
      "The even values are 8 and 12. Their sum is 20.",
  },
  {
    category: "REASONING",
    prompt: "What happens if nums is an empty list?",
    options: [
      "The function returns 0",
      "The function returns None",
      "The function raises an error",
      "The function returns an empty list",
    ],
    correct: 0,
    explanation:
      "The loop runs zero times, so result remains 0 and is returned.",
  },
];

export default function UploadPage() {
  const [code, setCode] = useState(initialCode);
  const [analysed, setAnalysed] = useState(false);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitted, setSubmitted] = useState(false);
  const [activeQuestion, setActiveQuestion] = useState(0);

  const score = questions.reduce(
    (total, question, index) =>
      total + (answers[index] === question.correct ? 1 : 0),
    0
  );

  function startAnalysis() {
    if (!code.trim()) return;
    setAnalysed(true);
    setSubmitted(false);
    setAnswers({});
    setActiveQuestion(0);
  }

  function resetWorkspace() {
    setCode(initialCode);
    setAnalysed(false);
    setSubmitted(false);
    setAnswers({});
    setActiveQuestion(0);
  }

  return (
    <main className="min-h-screen bg-[#10110F] text-[#F3F4EF]">
      <header className="sticky top-0 z-20 border-b border-[#2A2D27] bg-[#10110F]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-5 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              aria-label="Back to home"
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#2A2D27] text-zinc-400 transition hover:text-white"
            >
              <ArrowLeft size={17} />
            </Link>
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#D5FF62] text-black">
              <Braces size={21} />
            </div>
            <div>
              <p className="font-semibold tracking-tight">
                codeviva<span className="text-[#D5FF62]">.</span>
              </p>
              <p className="text-[11px] text-zinc-500">Practice workspace</p>
            </div>
          </div>

          <div className="hidden items-center gap-2 rounded-full border border-[#2A2D27] px-3 py-2 text-xs text-zinc-400 sm:flex">
            <span className="h-2 w-2 rounded-full bg-[#D5FF62]" />
            Python · Single file
            <ChevronDown size={13} />
          </div>

          <button
            onClick={resetWorkspace}
            className="flex items-center gap-2 rounded-lg border border-[#2A2D27] px-3 py-2 text-xs text-zinc-300 transition hover:border-zinc-500"
          >
            <RotateCcw size={14} />
            <span className="hidden sm:inline">Reset</span>
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-[1600px] px-5 py-7 lg:px-8">
        <div className="mb-7 flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <div className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-[#D5FF62]">
              <span className="h-px w-6 bg-[#D5FF62]" />
              THE PRACTICE ROOM
            </div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Think beyond the syntax.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-zinc-400">
              Submit a code snippet, reason through its behaviour, and prove
              you understand what it actually does.
            </p>
          </div>

          <button
            onClick={startAnalysis}
            disabled={!code.trim()}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#D5FF62] px-5 py-3.5 text-sm font-semibold text-black transition hover:bg-[#E2FF94] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {analysed ? <Check size={17} /> : <Sparkles size={17} />}
            {analysed ? "Analysis ready" : "Analyse my code"}
            {!analysed && <ArrowRight size={16} />}
          </button>
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.04fr_0.96fr]">
          <section className="min-w-0 overflow-hidden rounded-2xl border border-[#2A2D27] bg-[#151713]">
            <div className="flex items-center justify-between border-b border-[#2A2D27] px-4 py-4 sm:px-5">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#24281F] text-[#D5FF62]">
                  <FileCode2 size={18} />
                </div>
                <div>
                  <p className="text-sm font-medium">main.py</p>
                  <p className="mt-1 text-[11px] text-zinc-500">
                    Edit your code below
                  </p>
                </div>
              </div>
              <span className="rounded-md border border-[#2A2D27] px-2 py-1 text-[10px] text-zinc-400">
                PYTHON
              </span>
            </div>

            <div className="flex items-center gap-2 border-b border-[#2A2D27] px-5 py-2.5 text-[11px] text-zinc-500">
              <Code2 size={13} />
              SOURCE EDITOR
              <span className="ml-auto">UTF-8</span>
            </div>

            <div className="flex min-h-[360px] bg-[#121310] py-5">
              <div
                aria-hidden="true"
                className="select-none border-r border-[#242620] px-3 text-right font-mono text-xs leading-[25px] text-zinc-600 sm:px-4"
              >
                {code.split("\n").map((_, index) => (
                  <div key={index}>{index + 1}</div>
                ))}
              </div>
              <textarea
                aria-label="Python source code"
                spellCheck={false}
                value={code}
                onChange={(event) => {
                  setCode(event.target.value);
                  setAnalysed(false);
                  setSubmitted(false);
                }}
                className="min-w-0 flex-1 resize-y bg-transparent px-4 font-mono text-xs leading-[25px] text-[#D5FFB1] outline-none placeholder:text-zinc-600 sm:text-sm"
                style={{ minHeight: 330 }}
                placeholder="Paste your Python code here..."
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#2A2D27] px-4 py-3 sm:px-5">
              <div className="flex items-center gap-2 text-[11px] text-zinc-500">
                <Terminal size={14} />
                {code.split("\n").length} lines
                <span className="text-zinc-700">/</span>
                {code.length} characters
              </div>
              <span className="text-[10px] text-zinc-500">
                Local demo · No code uploaded
              </span>
            </div>
          </section>

          <section className="min-w-0 overflow-hidden rounded-2xl border border-[#2A2D27] bg-[#151713]">
            <div className="flex items-center justify-between border-b border-[#2A2D27] px-4 py-4 sm:px-5">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#24281F] text-[#D5FF62]">
                  <CircleHelp size={18} />
                </div>
                <div>
                  <p className="text-sm font-medium">Comprehension check</p>
                  <p className="mt-1 text-[11px] text-zinc-500">
                    {analysed
                      ? "Demo questions · Select your answers"
                      : "Questions appear after analysis"}
                  </p>
                </div>
              </div>
              {analysed && (
                <span className="rounded-full border border-[#414832] px-2.5 py-1 text-[10px] text-[#D5FF62]">
                  {questions.length} QUESTIONS
                </span>
              )}
            </div>

            {!analysed ? (
              <div className="flex min-h-[390px] flex-col items-center justify-center px-8 py-12 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-[#414832] bg-[#20241B] text-[#D5FF62]">
                  <Sparkles size={24} />
                </div>
                <h2 className="mt-6 text-lg font-medium">
                  Your code has a story.
                </h2>
                <p className="mt-3 max-w-xs text-sm leading-6 text-zinc-500">
                  Submit the snippet to explore example questions about its
                  logic, output and behaviour.
                </p>
                <button
                  onClick={startAnalysis}
                  className="mt-6 inline-flex items-center gap-2 rounded-lg border border-[#414832] px-4 py-2.5 text-sm text-[#D5FF62] transition hover:bg-[#20241B]"
                >
                  <Play size={15} />
                  Start demo analysis
                </button>
              </div>
            ) : (
              <div className="p-4 sm:p-5">
                <div className="mb-5 flex gap-2">
                  {questions.map((question, index) => (
                    <button
                      key={question.category}
                      onClick={() => setActiveQuestion(index)}
                      aria-label={`Go to question ${index + 1}`}
                      className={`flex h-9 w-9 items-center justify-center rounded-lg border text-xs transition ${
                        activeQuestion === index
                          ? "border-[#D5FF62] bg-[#D5FF62] font-semibold text-black"
                          : answers[index] !== undefined
                            ? "border-[#414832] bg-[#20241B] text-[#D5FF62]"
                            : "border-[#2A2D27] text-zinc-400 hover:border-zinc-500"
                      }`}
                    >
                      {answers[index] !== undefined &&
                      activeQuestion !== index ? (
                        <Check size={14} />
                      ) : (
                        index + 1
                      )}
                    </button>
                  ))}
                  <span className="ml-auto self-center text-[11px] text-zinc-500">
                    {Object.keys(answers).length}/{questions.length} answered
                  </span>
                </div>

                <div className="rounded-xl border border-[#2A2D27] bg-[#121310] p-4 sm:p-5">
                  <span className="text-[10px] font-medium tracking-[0.18em] text-[#D5FF62]">
                    QUESTION {String(activeQuestion + 1).padStart(2, "0")}{" "}
                    / {questionCount(questions.length)}
                  </span>
                  <p className="mt-4 text-base font-medium leading-7">
                    {questions[activeQuestion].prompt}
                  </p>
                  <div className="mt-5 space-y-2.5">
                    {questions[activeQuestion].options.map(
                      (option, index) => {
                        const selected =
                          answers[activeQuestion] === index;
                        const correct =
                          questions[activeQuestion].correct === index;
                        const reveal = submitted;

                        return (
                          <button
                            key={option}
                            disabled={submitted}
                            onClick={() =>
                              setAnswers((previous) => ({
                                ...previous,
                                [activeQuestion]: index,
                              }))
                            }
                            className={`flex w-full items-start gap-3 rounded-xl border p-3 text-left text-xs leading-5 transition sm:text-sm ${
                              reveal && correct
                                ? "border-[#D5FF62]/60 bg-[#D5FF62]/10 text-[#D5FF62]"
                                : reveal && selected
                                  ? "border-red-400/50 bg-red-400/5 text-red-200"
                                  : selected
                                    ? "border-[#D5FF62]/60 bg-[#D5FF62]/5 text-white"
                                    : "border-[#2A2D27] text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
                            }`}
                          >
                            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-current/20 text-[10px]">
                              {reveal && correct ? (
                                <Check size={13} />
                              ) : reveal && selected ? (
                                <X size={13} />
                              ) : (
                                String.fromCharCode(65 + index)
                              )}
                            </span>
                            <span className="pt-0.5">{option}</span>
                          </button>
                        );
                      }
                    )}
                  </div>

                  {submitted && (
                    <div className="mt-4 rounded-lg border border-[#414832] bg-[#20241B] p-3 text-xs leading-5 text-zinc-300">
                      <p className="mb-1 font-medium text-[#D5FF62]">
                        Why this is correct
                      </p>
                      {questions[activeQuestion].explanation}
                    </div>
                  )}
                </div>

                {!submitted ? (
                  <div className="mt-5 flex items-center justify-between gap-3">
                    <button
                      disabled={activeQuestion === 0}
                      onClick={() =>
                        setActiveQuestion((current) => current - 1)
                      }
                      className="rounded-lg border border-[#2A2D27] px-4 py-2.5 text-xs text-zinc-300 disabled:opacity-30"
                    >
                      Previous
                    </button>
                    {activeQuestion < questions.length - 1 ? (
                      <button
                        onClick={() =>
                          setActiveQuestion((current) => current + 1)
                        }
                        className="flex items-center gap-2 rounded-lg bg-[#D5FF62] px-4 py-2.5 text-xs font-semibold text-black"
                      >
                        Next question <ArrowRight size={14} />
                      </button>
                    ) : (
                      <button
                        disabled={
                          Object.keys(answers).length !== questions.length
                        }
                        onClick={() => setSubmitted(true)}
                        className="rounded-lg bg-[#D5FF62] px-4 py-2.5 text-xs font-semibold text-black disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Check answers
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="mt-5 rounded-xl border border-[#414832] bg-[#20241B] p-5">
                    <p className="text-xs text-zinc-400">DEMO RESULT</p>
                    <p className="mt-2 text-3xl font-semibold text-[#D5FF62]">
                      {score}/{questions.length}
                    </p>
                    <p className="mt-2 text-sm text-zinc-300">
                      {score === questions.length
                        ? "Excellent work. You understood every question."
                        : "Review the explanations to strengthen your understanding."}
                    </p>
                    <button
                      onClick={() => {
                        setAnswers({});
                        setSubmitted(false);
                        setActiveQuestion(0);
                      }}
                      className="mt-4 inline-flex items-center gap-2 text-xs text-[#D5FF62]"
                    >
                      Try again <RotateCcw size={13} />
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>

        <div className="mt-5 flex flex-col gap-2 text-[11px] leading-5 text-zinc-600 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2">
            <CircleHelp size={13} />
            Demo questions are fixed examples, not generated by the backend.
          </p>
          <Link
            href="/student"
            className="inline-flex items-center gap-1 text-zinc-400 transition hover:text-[#D5FF62]"
          >
            Student dashboard <ArrowRight size={13} />
          </Link>
        </div>
      </div>
    </main>
  );
}

function questionCount(count: number) {
  return String(count).padStart(2, "0");
}
