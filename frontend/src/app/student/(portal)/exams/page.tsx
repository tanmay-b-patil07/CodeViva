
"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock3,
  Code2,
  Filter,
  Search,
  Sparkles,
  Target,
} from "lucide-react";

const exams = [
  {
    id: "CV-001",
    title: "Python Fundamentals",
    description: "Variables, data types, loops and basic logic.",
    language: "Python",
    level: "Beginner",
    questions: 8,
    duration: "20 min",
    status: "Available",
    progress: 0,
  },
  {
    id: "CV-002",
    title: "Control Flow Challenge",
    description: "Trace conditions, loops and predict program output.",
    language: "Python",
    level: "Intermediate",
    questions: 10,
    duration: "30 min",
    status: "In progress",
    progress: 40,
  },
  {
    id: "CV-003",
    title: "Functions & Recursion",
    description: "Explain function calls, return values and recursion.",
    language: "C",
    level: "Intermediate",
    questions: 12,
    duration: "35 min",
    status: "Available",
    progress: 0,
  },
  {
    id: "CV-004",
    title: "Array Logic Assessment",
    description: "Reason about indexes, iterations and edge cases.",
    language: "C",
    level: "Advanced",
    questions: 10,
    duration: "30 min",
    status: "Completed",
    progress: 100,
  },
];

type Exam = (typeof exams)[number];

export default function StudentExamsPage() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");

  const filteredExams = exams.filter((exam) => {
    const matchesSearch =
      exam.title.toLowerCase().includes(search.toLowerCase()) ||
      exam.language.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filter === "All" ||
      (filter === "Available" && exam.status === "Available") ||
      (filter === "In progress" && exam.status === "In progress") ||
      (filter === "Completed" && exam.status === "Completed");

    return matchesSearch && matchesFilter;
  });

  return (
    <main className="min-h-screen bg-canvas text-white">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
          <Link href="/student" className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-lime text-black">
              <Code2 size={22} />
            </div>
            <div>
              <p className="text-lg font-bold tracking-tight">CodeViva</p>
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
        <div className="mb-10 flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-xs text-lime">
              <Sparkles size={14} />
              YOUR ASSESSMENT CENTRE
            </div>

            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Prove your <span className="text-lime">understanding.</span>
            </h1>

            <p className="mt-4 max-w-xl text-sm leading-6 text-muted sm:text-base">
              Go beyond writing code. Trace the logic, predict the output and
              show that you understand what your program actually does.
            </p>
          </div>

          <Link
            href="/student/upload"
            className="inline-flex w-fit items-center gap-2 rounded-xl bg-lime px-5 py-3 text-sm font-semibold text-black transition hover:bg-white"
          >
            <Code2 size={17} />
            Analyse my code
            <ArrowRight size={16} />
          </Link>
        </div>

        <section className="mb-9 grid gap-4 sm:grid-cols-3">
          <SummaryCard
            icon={<BookOpen size={19} />}
            label="Total assessments"
            value="04"
            note="Sample assessments"
          />
          <SummaryCard
            icon={<Clock3 size={19} />}
            label="Ready to attempt"
            value="02"
            note="Available in this demo"
          />
          <SummaryCard
            icon={<CheckCircle2 size={19} />}
            label="Completed"
            value="01"
            note="Demo completion status"
          />
        </section>

        <section className="mb-6 rounded-2xl border border-line bg-panel p-4 sm:p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="relative w-full md:max-w-sm">
              <Search
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-muted"
              />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search assessments or languages..."
                className="w-full rounded-xl border border-line bg-canvas py-3 pl-11 pr-4 text-sm outline-none transition placeholder:text-muted focus:border-lime"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Filter size={16} className="mr-1 text-muted" />
              {["All", "Available", "In progress", "Completed"].map((item) => (
                <button
                  key={item}
                  onClick={() => setFilter(item)}
                  className={`rounded-lg px-3 py-2 text-xs font-medium transition ${
                    filter === item
                      ? "bg-lime text-black"
                      : "border border-line text-muted hover:border-lime hover:text-white"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </section>

        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Your assessments</h2>
          <span className="text-xs text-muted">
            {filteredExams.length} results
          </span>
        </div>

        <section className="grid gap-4 lg:grid-cols-2">
          {filteredExams.map((exam) => (
            <ExamCard key={exam.id} exam={exam} />
          ))}
        </section>

        {filteredExams.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line py-16 text-center">
            <Search className="mx-auto mb-3 text-muted" size={28} />
            <p className="font-medium">No assessments found</p>
            <p className="mt-2 text-sm text-muted">
              Try another search or choose a different filter.
            </p>
            <button
              onClick={() => {
                setSearch("");
                setFilter("All");
              }}
              className="mt-4 text-sm text-lime hover:underline"
            >
              Clear filters
            </button>
          </div>
        )}

        <div className="mt-10 flex flex-col justify-between gap-3 border-t border-line pt-6 text-xs text-muted sm:flex-row">
          <p>CodeViva · Think beyond the syntax.</p>
          <p>Demo data — assessments are not connected to a backend yet.</p>
        </div>
      </div>
    </main>
  );
}

function SummaryCard({
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

function ExamCard({ exam }: { exam: Exam }) {
  const isCompleted = exam.status === "Completed";
  const isProgress = exam.status === "In progress";

  return (
    <article className="group rounded-2xl border border-line bg-panel p-5 transition duration-200 hover:-translate-y-1 hover:border-lime/50 sm:p-6">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-line bg-canvas text-lime transition group-hover:border-lime/40">
          <Code2 size={23} />
        </div>

        <span
          className={`rounded-full border px-3 py-1.5 text-xs ${
            isCompleted
              ? "border-emerald-500/30 text-emerald-400"
              : isProgress
                ? "border-amber-400/30 text-amber-300"
                : "border-lime/30 text-lime"
          }`}
        >
          {exam.status}
        </span>
      </div>

      <p className="mb-2 text-xs tracking-wider text-muted">{exam.id}</p>
      <h3 className="text-xl font-semibold tracking-tight">{exam.title}</h3>
      <p className="mt-2 min-h-12 text-sm leading-6 text-muted">
        {exam.description}
      </p>

      <div className="mt-5 flex flex-wrap gap-2">
        <span className="rounded-lg bg-canvas px-3 py-2 text-xs text-white">
          {exam.language}
        </span>
        <span className="rounded-lg bg-canvas px-3 py-2 text-xs text-muted">
          {exam.level}
        </span>
      </div>

      <div className="mt-5 flex items-center gap-5 border-t border-line pt-4 text-xs text-muted">
        <span className="flex items-center gap-2">
          <Target size={15} />
          {exam.questions} questions
        </span>
        <span className="flex items-center gap-2">
          <Clock3 size={15} />
          {exam.duration}
        </span>
      </div>

      {isProgress && (
        <div className="mt-5">
          <div className="mb-2 flex justify-between text-xs">
            <span className="text-muted">Demo progress</span>
            <span className="text-lime">{exam.progress}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-canvas">
            <div
              className="h-full rounded-full bg-lime"
              style={{ width: `${exam.progress}%` }}
            />
          </div>
        </div>
      )}

      <div className="mt-6">
        <Link
          href="/student/upload"
          className={`flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition ${
            isCompleted
              ? "border border-line text-muted hover:border-lime hover:text-lime"
              : "bg-lime text-black hover:bg-white"
          }`}
        >
          {isCompleted
            ? "Practise again"
            : isProgress
              ? "Continue practising"
              : "Start assessment"}
          <ArrowRight size={16} />
        </Link>
      </div>
    </article>
  );
}
