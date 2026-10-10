
"use client";

import Link from "next/link";
import {
  ArrowDownRight,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Award,
  BookOpen,
  CheckCircle2,
  Clock3,
  Code2,
  Flame,
  Target,
  TrendingUp,
} from "lucide-react";

const history = [
  {
    title: "Python Fundamentals",
    language: "Python",
    date: "Oct 08, 2026",
    score: 88,
    correct: "7/8",
    status: "Passed",
  },
  {
    title: "Control Flow & Logic",
    language: "C",
    date: "Oct 05, 2026",
    score: 70,
    correct: "7/10",
    status: "Passed",
  },
  {
    title: "Functions & Recursion",
    language: "Python",
    date: "Oct 02, 2026",
    score: 50,
    correct: "5/10",
    status: "Needs practice",
  },
];

const topics = [
  { name: "Variables & data types", score: 92, note: "Strong" },
  { name: "Control flow", score: 78, note: "Good progress" },
  { name: "Functions", score: 64, note: "Keep practising" },
  { name: "Edge cases", score: 48, note: "Focus area" },
];

export default function StudentResultsPage() {
  return (
    <main className="min-h-screen bg-canvas text-white">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
          <Link href="/student" className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-lime text-black">
              <Code2 size={22} />
            </div>
            <div>
              <p className="text-lg font-bold">CodeViva</p>
              <p className="text-xs text-muted">STUDENT WORKSPACE</p>
            </div>
          </Link>

          <Link
            href="/student"
            className="flex items-center gap-2 text-sm text-muted transition hover:text-lime"
          >
            <ArrowLeft size={16} />
            Dashboard
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="mb-10">
          <p className="mb-4 text-xs tracking-[0.2em] text-lime">
            YOUR LEARNING JOURNEY
          </p>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Progress you can <span className="text-lime">prove.</span>
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-muted sm:text-base">
            Understand what you have mastered, find the gaps in your reasoning,
            and turn every assessment into your next improvement.
          </p>
        </div>

        <section className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={<Award size={20} />}
            label="Average score"
            value="69%"
            note="Across sample assessments"
          />
          <StatCard
            icon={<CheckCircle2 size={20} />}
            label="Completed"
            value="03"
            note="Demo assessment history"
          />
          <StatCard
            icon={<Flame size={20} />}
            label="Best score"
            value="88%"
            note="Python Fundamentals"
          />
          <StatCard
            icon={<Clock3 size={20} />}
            label="Practice time"
            value="1h 25m"
            note="Illustrative demo value"
          />
        </section>

        <section className="mb-8 grid items-start gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-line bg-panel p-6 sm:p-8">
            <div className="mb-7 flex items-start justify-between gap-4">
              <div>
                <p className="text-sm text-muted">Overall performance</p>
                <h2 className="mt-2 text-3xl font-semibold">69%</h2>
                <p className="mt-2 text-sm text-muted">
                  A starting point for your next learning milestone.
                </p>
              </div>
              <div className="grid h-12 w-12 place-items-center rounded-xl bg-lime/10 text-lime">
                <TrendingUp size={23} />
              </div>
            </div>

            <div className="mb-3 flex items-center justify-between text-xs text-muted">
              <span>Current average</span>
              <span>Target: 85%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-canvas">
              <div
                className="h-full rounded-full bg-lime"
                style={{ width: "69%" }}
              />
            </div>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-line bg-canvas p-4">
                <p className="text-xs text-muted">Target gap</p>
                <p className="mt-2 text-2xl font-semibold">16 pts</p>
                <p className="mt-1 text-xs text-muted">
                  To reach your target
                </p>
              </div>
              <div className="rounded-xl border border-line bg-canvas p-4">
                <p className="text-xs text-muted">Strongest area</p>
                <p className="mt-2 text-lg font-semibold">Variables</p>
                <p className="mt-1 text-xs text-lime">92% demo score</p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-line bg-panel p-6 sm:p-8">
            <div className="mb-7 flex items-center justify-between">
              <div>
                <p className="text-sm text-muted">Topic breakdown</p>
                <h2 className="mt-1 text-xl font-semibold">
                  Know your strengths.
                </h2>
              </div>
              <Target className="text-lime" size={22} />
            </div>

            <div className="space-y-6">
              {topics.map((topic) => (
                <div key={topic.name}>
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <span className="text-sm">{topic.name}</span>
                    <span className="text-sm font-medium">{topic.score}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-canvas">
                    <div
                      className="h-full rounded-full bg-lime"
                      style={{ width: `${topic.score}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-muted">{topic.note}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mb-8 rounded-2xl border border-line bg-panel p-6 sm:p-8">
          <div className="mb-6 flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-lime/10 text-lime">
              <BookOpen size={21} />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Your next focus</h2>
              <p className="mt-1 text-sm text-muted">
                Suggested from the illustrative topic breakdown above.
              </p>
            </div>
          </div>

          <div className="flex flex-col justify-between gap-5 rounded-xl border border-line bg-canvas p-5 sm:flex-row sm:items-center">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 text-xs text-lime">
                <ArrowDownRight size={15} />
                PRIORITY PRACTICE
              </div>
              <h3 className="text-lg font-semibold">Edge cases & conditions</h3>
              <p className="mt-2 max-w-xl text-sm leading-6 text-muted">
                Practise tracing boundary conditions, empty inputs and loop
                termination. Explain why each output occurs, not just what it is.
              </p>
            </div>
            <Link
              href="/student/upload"
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-lime px-5 py-3 text-sm font-semibold text-black transition hover:bg-white"
            >
              Practise now <ArrowRight size={16} />
            </Link>
          </div>
        </section>

        <section className="overflow-hidden rounded-2xl border border-line bg-panel">
          <div className="flex flex-col justify-between gap-3 border-b border-line p-5 sm:flex-row sm:items-center sm:p-6">
            <div>
              <h2 className="text-xl font-semibold">Assessment history</h2>
              <p className="mt-1 text-sm text-muted">
                Review your recent practice sessions.
              </p>
            </div>
            <Link
              href="/student/assignments"
              className="inline-flex items-center gap-2 text-sm text-lime hover:text-white"
            >
              Browse assignments <ArrowUpRight size={16} />
            </Link>
          </div>

          <div className="divide-y divide-line">
            {history.map((item) => (
              <div
                key={item.title}
                className="flex flex-col justify-between gap-4 p-5 transition hover:bg-white/[0.02] sm:flex-row sm:items-center sm:px-6"
              >
                <div className="flex items-start gap-4">
                  <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-line bg-canvas text-lime">
                    <Code2 size={20} />
                  </div>
                  <div>
                    <h3 className="font-medium">{item.title}</h3>
                    <p className="mt-1 text-xs text-muted">
                      {item.language} · {item.date} · {item.correct} correct
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-5 sm:justify-end">
                  <div className="text-right">
                    <p className="text-xl font-semibold">{item.score}%</p>
                    <p
                      className={`mt-1 text-xs ${
                        item.status === "Passed"
                          ? "text-lime"
                          : "text-amber-300"
                      }`}
                    >
                      {item.status}
                    </p>
                  </div>
                  <Link
                    href="/student/upload"
                    aria-label={`Practise ${item.title} again`}
                    className="grid h-9 w-9 place-items-center rounded-lg border border-line text-muted transition hover:border-lime hover:text-lime"
                  >
                    <ArrowRight size={17} />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>

        <footer className="mt-8 flex flex-col justify-between gap-3 border-t border-line pt-5 text-xs text-muted sm:flex-row">
          <p>CodeViva · Every mistake is a chance to understand more.</p>
          <p>Illustrative demo results · Not real student records</p>
        </footer>
      </div>
    </main>
  );
}

function StatCard({
  icon,
  label,
  value,
  note,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="rounded-2xl border border-line bg-panel p-5">
      <div className="mb-5 flex items-center justify-between">
        <span className="text-sm text-muted">{label}</span>
        <span className="text-lime">{icon}</span>
      </div>
      <p className="text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-xs text-muted">{note}</p>
    </div>
  );
}
