
"use client";

import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  Clock3,
  Code2,
  FileText,
  Plus,
  Sparkles,
  Users,
} from "lucide-react";

const assessments = [
  {
    title: "Python Fundamentals",
    language: "PYTHON",
    students: 32,
    submitted: 24,
    status: "Active",
  },
  {
    title: "Control Flow & Logic",
    language: "C",
    students: 28,
    submitted: 28,
    status: "Completed",
  },
  {
    title: "Functions and Recursion",
    language: "PYTHON",
    students: 30,
    submitted: 12,
    status: "Active",
  },
];

export default function TeacherDashboard() {
  return (
    <main className="min-h-screen bg-canvas text-white">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-lime text-black">
              <Code2 size={22} />
            </div>
            <div>
              <p className="text-lg font-bold">CodeViva</p>
              <p className="text-xs text-muted">TEACHER WORKSPACE</p>
            </div>
          </Link>

          <Link
            href="/student"
            className="text-sm text-muted transition hover:text-lime"
          >
            Student view <ArrowUpRight className="ml-1 inline" size={15} />
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="mb-10 flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-xs text-lime">
              <Sparkles size={14} />
              EDUCATOR CONSOLE
            </div>

            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Teach with <span className="text-lime">insight.</span>
            </h1>

            <p className="mt-4 max-w-xl text-sm leading-6 text-muted sm:text-base">
              Manage assessments, review student understanding and identify
              where learners need support.
            </p>
          </div>

          <Link
            href="/teacher/exams"
            className="inline-flex w-fit items-center gap-2 rounded-xl bg-lime px-5 py-3 text-sm font-semibold text-black transition hover:bg-white"
          >
            <Plus size={17} />
            Manage assessments
            <ArrowRight size={16} />
          </Link>
        </div>

        <section className="mb-9 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={<BookOpen size={19} />}
            label="Assessments"
            value="03"
            note="Sample assessment data"
          />
          <StatCard
            icon={<Users size={19} />}
            label="Enrolled students"
            value="90"
            note="Across sample assessments"
          />
          <StatCard
            icon={<CheckCircle2 size={19} />}
            label="Submissions"
            value="64"
            note="Sample submission count"
          />
          <StatCard
            icon={<Clock3 size={19} />}
            label="Awaiting review"
            value="26"
            note="Illustrative pending count"
          />
        </section>

        <section className="grid items-start gap-6 lg:grid-cols-[1.5fr_0.8fr]">
          <div className="overflow-hidden rounded-2xl border border-line bg-panel">
            <div className="flex items-center justify-between border-b border-line p-5 sm:p-6">
              <div>
                <h2 className="text-lg font-semibold">Recent assessments</h2>
                <p className="mt-1 text-xs text-muted">
                  A quick view of your assessment activity
                </p>
              </div>
              <FileText size={21} className="text-lime" />
            </div>

            <div className="divide-y divide-line">
              {assessments.map((assessment) => (
                <div
                  key={assessment.title}
                  className="p-5 transition hover:bg-white/[0.02] sm:p-6"
                >
                  <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                    <div>
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="text-[10px] tracking-wider text-muted">
                          {assessment.language}
                        </span>
                        <span
                          className={`rounded-full px-2.5 py-1 text-[10px] ${
                            assessment.status === "Active"
                              ? "bg-lime/10 text-lime"
                              : "bg-white/5 text-muted"
                          }`}
                        >
                          {assessment.status}
                        </span>
                      </div>
                      <h3 className="font-medium">{assessment.title}</h3>
                      <p className="mt-2 text-xs text-muted">
                        {assessment.submitted} of {assessment.students}{" "}
                        submissions
                      </p>
                    </div>

                    <div className="w-full sm:w-32">
                      <div className="mb-2 flex justify-between text-xs">
                        <span className="text-muted">Submitted</span>
                        <span className="text-white">
                          {Math.round(
                            (assessment.submitted / assessment.students) * 100
                          )}
                          %
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-canvas">
                        <div
                          className="h-full rounded-full bg-lime"
                          style={{
                            width: `${
                              (assessment.submitted / assessment.students) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <Link
              href="/teacher/exams"
              className="flex items-center justify-between border-t border-line p-5 text-sm text-muted transition hover:text-lime sm:px-6"
            >
              View all assessments <ArrowRight size={16} />
            </Link>
          </div>

          <aside className="rounded-2xl border border-line bg-panel p-6">
            <div className="mb-5 grid h-11 w-11 place-items-center rounded-xl bg-lime/10 text-lime">
              <Sparkles size={21} />
            </div>

            <h2 className="text-xl font-semibold">Your next move.</h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              Create an assessment, prepare code-based questions and give
              students an opportunity to demonstrate their reasoning.
            </p>

            <div className="my-6 space-y-4">
              <ActionItem
                number="01"
                title="Prepare an assessment"
                description="Set up a code comprehension activity."
              />
              <ActionItem
                number="02"
                title="Review submissions"
                description="Inspect student responses and results."
              />
              <ActionItem
                number="03"
                title="Find learning gaps"
                description="Identify topics that need more practice."
              />
            </div>

            <Link
              href="/teacher/exams"
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-line px-4 py-3 text-sm font-medium transition hover:border-lime hover:text-lime"
            >
              Open assessment centre <ArrowRight size={16} />
            </Link>
          </aside>
        </section>

        <p className="mt-8 border-t border-line pt-5 text-xs text-muted">
          CodeViva · Teacher dashboard · All counts and assessment records on
          this screen are illustrative demo data.
        </p>
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

function ActionItem({
  number,
  title,
  description,
}: {
  number: string;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-3">
      <span className="pt-0.5 font-mono text-xs text-lime">{number}</span>
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 text-xs leading-5 text-muted">{description}</p>
      </div>
    </div>
  );
}
