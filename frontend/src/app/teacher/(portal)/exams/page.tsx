
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
  Plus,
  Search,
  Users,
} from "lucide-react";

const assessments = [
  {
    id: "ASM-001",
    title: "Python Fundamentals",
    description: "Variables, data types, loops and basic programming logic.",
    language: "Python",
    level: "Beginner",
    students: 32,
    submissions: 24,
    status: "Active",
    due: "Oct 14, 2026",
  },
  {
    id: "ASM-002",
    title: "Control Flow & Logic",
    description: "Trace conditions, evaluate loops and predict program output.",
    language: "C",
    level: "Intermediate",
    students: 28,
    submissions: 28,
    status: "Completed",
    due: "Oct 06, 2026",
  },
  {
    id: "ASM-003",
    title: "Functions and Recursion",
    description: "Understand function calls, return values and recursion.",
    language: "Python",
    level: "Intermediate",
    students: 30,
    submissions: 12,
    status: "Active",
    due: "Oct 16, 2026",
  },
  {
    id: "ASM-004",
    title: "Array Logic Challenge",
    description: "Reason about array indexes, iterations and edge cases.",
    language: "C",
    level: "Advanced",
    students: 25,
    submissions: 0,
    status: "Draft",
    due: "Not scheduled",
  },
];

type Assessment = (typeof assessments)[number];

export default function TeacherExamsPage() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");

  const filtered = assessments.filter((assessment) => {
    const matchesSearch =
      assessment.title.toLowerCase().includes(search.toLowerCase()) ||
      assessment.language.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filter === "All" || assessment.status === filter;

    return matchesSearch && matchesFilter;
  });

  return (
    <main className="min-h-screen bg-canvas text-white">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
          <Link href="/teacher" className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-lime text-black">
              <Code2 size={22} />
            </div>
            <div>
              <p className="text-lg font-bold">CodeViva</p>
              <p className="text-xs text-muted">TEACHER WORKSPACE</p>
            </div>
          </Link>

          <Link
            href="/teacher"
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
            <p className="mb-4 text-xs tracking-[0.2em] text-lime">
              ASSESSMENT MANAGEMENT
            </p>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Your classroom.
              <br />
              <span className="text-lime">Your assessments.</span>
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-muted sm:text-base">
              Organise code comprehension assessments and track how students
              are progressing through each challenge.
            </p>
          </div>

          <button
            onClick={() =>
              alert(
                "Assessment creation is a demo placeholder. Backend integration is not connected yet."
              )
            }
            className="inline-flex w-fit items-center gap-2 rounded-xl bg-lime px-5 py-3 text-sm font-semibold text-black transition hover:bg-white"
          >
            <Plus size={18} />
            Create assessment
          </button>
        </div>

        <section className="mb-8 grid gap-4 sm:grid-cols-3">
          <SummaryCard
            icon={<BookOpen size={19} />}
            label="Total assessments"
            value="04"
            note="Illustrative demo records"
          />
          <SummaryCard
            icon={<Users size={19} />}
            label="Student assignments"
            value="115"
            note="Across demo assessments"
          />
          <SummaryCard
            icon={<CheckCircle2 size={19} />}
            label="Submissions received"
            value="64"
            note="Illustrative submission count"
          />
        </section>

        <section className="mb-6 rounded-2xl border border-line bg-panel p-4 sm:p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="relative w-full lg:max-w-md">
              <Search
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-muted"
              />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by assessment or language..."
                className="w-full rounded-xl border border-line bg-canvas py-3 pl-11 pr-4 text-sm outline-none placeholder:text-muted focus:border-lime"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Filter size={16} className="mr-1 text-muted" />
              {["All", "Active", "Completed", "Draft"].map((item) => (
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
          <h2 className="text-lg font-semibold">Assessment library</h2>
          <span className="text-xs text-muted">{filtered.length} results</span>
        </div>

        <section className="grid gap-4 lg:grid-cols-2">
          {filtered.map((assessment) => (
            <AssessmentCard key={assessment.id} assessment={assessment} />
          ))}
        </section>

        {filtered.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line py-16 text-center">
            <Search className="mx-auto mb-3 text-muted" size={28} />
            <p className="font-medium">No assessments found</p>
            <p className="mt-2 text-sm text-muted">
              Try a different search or status filter.
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

        <footer className="mt-10 flex flex-col justify-between gap-3 border-t border-line pt-6 text-xs text-muted sm:flex-row">
          <p>CodeViva · Assessment management</p>
          <p>Demo interface · Not connected to a backend</p>
        </footer>
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

function AssessmentCard({ assessment }: { assessment: Assessment }) {
  const percentage =
    assessment.students > 0
      ? Math.round((assessment.submissions / assessment.students) * 100)
      : 0;

  const statusStyle =
    assessment.status === "Active"
      ? "border-lime/30 text-lime"
      : assessment.status === "Completed"
        ? "border-emerald-500/30 text-emerald-400"
        : "border-line text-muted";

  return (
    <article className="group rounded-2xl border border-line bg-panel p-5 transition hover:-translate-y-1 hover:border-lime/40 sm:p-6">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div className="grid h-12 w-12 place-items-center rounded-xl border border-line bg-canvas text-lime">
          <Code2 size={23} />
        </div>
        <span
          className={`rounded-full border px-3 py-1.5 text-xs ${statusStyle}`}
        >
          {assessment.status}
        </span>
      </div>

      <p className="mb-2 text-xs tracking-wider text-muted">{assessment.id}</p>
      <h3 className="text-xl font-semibold">{assessment.title}</h3>
      <p className="mt-2 min-h-12 text-sm leading-6 text-muted">
        {assessment.description}
      </p>

      <div className="mt-5 flex flex-wrap gap-2">
        <span className="rounded-lg bg-canvas px-3 py-2 text-xs">
          {assessment.language}
        </span>
        <span className="rounded-lg bg-canvas px-3 py-2 text-xs text-muted">
          {assessment.level}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 border-t border-line pt-4">
        <div>
          <p className="text-xs text-muted">Submissions</p>
          <p className="mt-1 text-sm font-medium">
            {assessment.submissions}/{assessment.students}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted">Due date</p>
          <p className="mt-1 flex items-center gap-1.5 text-sm font-medium">
            <Clock3 size={14} className="text-muted" />
            {assessment.due}
          </p>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex justify-between text-xs">
          <span className="text-muted">Submission progress</span>
          <span>{percentage}%</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-canvas">
          <div
            className="h-full rounded-full bg-lime transition-all"
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      <Link
        href="/teacher"
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl border border-line px-4 py-3 text-sm font-medium transition hover:border-lime hover:text-lime"
      >
        View overview <ArrowRight size={16} />
      </Link>
    </article>
  );
}
