
"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Code2,
  Eye,
  Filter,
  Search,
  Users,
} from "lucide-react";

const submissions = [
  {
    id: "SUB-1042",
    student: "Aarav Sharma",
    initials: "AS",
    assessment: "Python Fundamentals",
    language: "Python",
    submitted: "Today, 10:42 AM",
    score: 88,
    status: "Reviewed",
  },
  {
    id: "SUB-1043",
    student: "Priya Nair",
    initials: "PN",
    assessment: "Python Fundamentals",
    language: "Python",
    submitted: "Today, 11:05 AM",
    score: null,
    status: "Pending",
  },
  {
    id: "SUB-1044",
    student: "Rohan Kumar",
    initials: "RK",
    assessment: "Control Flow & Logic",
    language: "C",
    submitted: "Today, 11:18 AM",
    score: 70,
    status: "Reviewed",
  },
  {
    id: "SUB-1045",
    student: "Ananya Rao",
    initials: "AR",
    assessment: "Functions and Recursion",
    language: "Python",
    submitted: "Today, 11:36 AM",
    score: null,
    status: "Pending",
  },
  {
    id: "SUB-1046",
    student: "Vikram Singh",
    initials: "VS",
    assessment: "Control Flow & Logic",
    language: "C",
    submitted: "Today, 12:02 PM",
    score: 82,
    status: "Reviewed",
  },
];

type Submission = (typeof submissions)[number];

export default function TeacherSubmissionsPage() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [selected, setSelected] = useState<Submission | null>(null);
  const [scores, setScores] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [reviewed, setReviewed] = useState<string[]>([]);

  const filtered = submissions.filter((item) => {
    const query = search.toLowerCase();
    const matchesSearch =
      item.student.toLowerCase().includes(query) ||
      item.assessment.toLowerCase().includes(query) ||
      item.id.toLowerCase().includes(query);

    const currentStatus = reviewed.includes(item.id)
      ? "Reviewed"
      : item.status;

    const matchesFilter =
      filter === "All" || currentStatus === filter;

    return matchesSearch && matchesFilter;
  });

  function saveReview(item: Submission) {
    const score = scores[item.id];
    if (score === undefined || score.trim() === "") {
      alert("Enter a score before saving the review.");
      return;
    }

    const numericScore = Number(score);
    if (
      !Number.isFinite(numericScore) ||
      numericScore < 0 ||
      numericScore > 100
    ) {
      alert("Enter a score between 0 and 100.");
      return;
    }

    setReviewed((previous) =>
      previous.includes(item.id) ? previous : [...previous, item.id]
    );
    alert("Demo review saved locally. It has not been sent to a backend.");
    setSelected(null);
  }

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
        <div className="mb-10">
          <p className="mb-4 text-xs tracking-[0.2em] text-lime">
            STUDENT WORK REVIEW
          </p>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Look beyond the <span className="text-lime">output.</span>
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-muted sm:text-base">
            Review submissions, evaluate students&apos; reasoning and leave
            feedback that helps them understand the logic behind their code.
          </p>
        </div>

        <section className="mb-8 grid gap-4 sm:grid-cols-3">
          <SummaryCard
            icon={<Users size={19} />}
            label="Total submissions"
            value="05"
            note="Illustrative sample records"
          />
          <SummaryCard
            icon={<Clock3 size={19} />}
            label="Awaiting review"
            value={String(
              submissions.filter(
                (item) =>
                  item.status === "Pending" && !reviewed.includes(item.id)
              ).length
            ).padStart(2, "0")}
            note="Sample review queue"
          />
          <SummaryCard
            icon={<CheckCircle2 size={19} />}
            label="Reviewed"
            value={String(
              submissions.filter(
                (item) =>
                  item.status === "Reviewed" || reviewed.includes(item.id)
              ).length
            ).padStart(2, "0")}
            note="Includes local demo reviews"
          />
        </section>

        <section className="overflow-hidden rounded-2xl border border-line bg-panel">
          <div className="border-b border-line p-5 sm:p-6">
            <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
              <div>
                <h2 className="text-xl font-semibold">Submission inbox</h2>
                <p className="mt-1 text-sm text-muted">
                  Select a submission to open the review panel.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <div className="relative">
                  <Search
                    size={17}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted"
                  />
                  <input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search submissions..."
                    className="w-full rounded-xl border border-line bg-canvas py-2.5 pl-10 pr-3 text-sm outline-none placeholder:text-muted focus:border-lime sm:w-64"
                  />
                </div>

                <div className="relative">
                  <Filter
                    size={15}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                  />
                  <select
                    value={filter}
                    onChange={(event) => setFilter(event.target.value)}
                    className="w-full appearance-none rounded-xl border border-line bg-canvas py-2.5 pl-9 pr-9 text-sm outline-none focus:border-lime sm:w-40"
                  >
                    <option>All</option>
                    <option>Pending</option>
                    <option>Reviewed</option>
                  </select>
                  <ChevronDown
                    size={14}
                    className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-muted"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="divide-y divide-line">
            {filtered.map((item) => {
              const isReviewed =
                item.status === "Reviewed" || reviewed.includes(item.id);

              return (
                <div
                  key={item.id}
                  className="flex flex-col justify-between gap-4 p-5 transition hover:bg-white/[0.02] sm:flex-row sm:items-center sm:px-6"
                >
                  <div className="flex items-start gap-4">
                    <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-line bg-canvas text-xs font-semibold text-lime">
                      {item.initials}
                    </div>

                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-medium">{item.student}</h3>
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] ${
                            isReviewed
                              ? "border-emerald-500/30 text-emerald-400"
                              : "border-amber-400/30 text-amber-300"
                          }`}
                        >
                          {isReviewed ? "Reviewed" : "Pending"}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-muted">
                        {item.assessment} · {item.language}
                      </p>
                      <p className="mt-2 text-xs text-muted">
                        {item.id} · {item.submitted}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-4 sm:justify-end">
                    <div className="text-right">
                      <p className="text-lg font-semibold">
                        {scores[item.id] !== undefined &&
                        scores[item.id] !== ""
                          ? `${scores[item.id]}%`
                          : item.score !== null
                            ? `${item.score}%`
                            : "—"}
                      </p>
                      <p className="text-xs text-muted">Score</p>
                    </div>

                    <button
                      onClick={() => setSelected(item)}
                      className="inline-flex items-center gap-2 rounded-xl border border-line px-4 py-2.5 text-sm transition hover:border-lime hover:text-lime"
                    >
                      <Eye size={16} />
                      Review
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {filtered.length === 0 && (
            <div className="py-14 text-center">
              <Search className="mx-auto mb-3 text-muted" size={26} />
              <p className="font-medium">No submissions found</p>
              <p className="mt-2 text-sm text-muted">
                Try another search or filter.
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
        </section>

        <footer className="mt-8 border-t border-line pt-5 text-xs text-muted">
          Demo submissions only. No real student records or backend review
          service is connected.
        </footer>
      </div>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/75 p-4 sm:items-center">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-title"
            className="my-6 w-full max-w-2xl rounded-2xl border border-line bg-panel shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4 border-b border-line p-5 sm:p-6">
              <div>
                <p className="text-xs tracking-wider text-lime">
                  {selected.id}
                </p>
                <h2 id="review-title" className="mt-2 text-2xl font-semibold">
                  Review submission
                </h2>
                <p className="mt-2 text-sm text-muted">
                  {selected.student} · {selected.assessment}
                </p>
              </div>
              <button
                onClick={() => setSelected(null)}
                aria-label="Close review panel"
                className="rounded-lg border border-line px-3 py-2 text-sm text-muted hover:text-white"
              >
                Close
              </button>
            </div>

            <div className="space-y-5 p-5 sm:p-6">
              <div>
                <p className="mb-3 text-sm font-medium">Sample submitted code</p>
                <pre className="overflow-x-auto rounded-xl border border-line bg-canvas p-4 text-sm leading-7 text-lime">
                  <code>{`def calculate_total(values):
    total = 0
    for value in values:
        total += value
    return total

numbers = [2, 4, 6]
print(calculate_total(numbers))`}</code>
                </pre>
                <p className="mt-2 text-xs text-muted">
                  Illustrative code sample, not the student&apos;s actual
                  submission.
                </p>
              </div>

              <div className="rounded-xl border border-line p-4">
                <p className="text-sm font-medium">Reasoning prompt</p>
                <p className="mt-2 text-sm leading-6 text-muted">
                  Explain how the loop updates total and predict the final
                  output. What would happen if the list were empty?
                </p>
              </div>

              <div>
                <label
                  htmlFor="review-score"
                  className="mb-2 block text-sm font-medium"
                >
                  Score (0–100)
                </label>
                <input
                  id="review-score"
                  type="number"
                  min="0"
                  max="100"
                  value={scores[selected.id] ?? (selected.score ?? "")}
                  onChange={(event) =>
                    setScores((previous) => ({
                      ...previous,
                      [selected.id]: event.target.value,
                    }))
                  }
                  placeholder="Enter score"
                  className="w-full rounded-xl border border-line bg-canvas px-4 py-3 text-sm outline-none focus:border-lime"
                />
              </div>

              <div>
                <label
                  htmlFor="review-feedback"
                  className="mb-2 block text-sm font-medium"
                >
                  Feedback for the student
                </label>
                <textarea
                  id="review-feedback"
                  rows={4}
                  value={feedback[selected.id] ?? ""}
                  onChange={(event) =>
                    setFeedback((previous) => ({
                      ...previous,
                      [selected.id]: event.target.value,
                    }))
                  }
                  placeholder="Share what they did well and what they can improve..."
                  className="w-full resize-y rounded-xl border border-line bg-canvas px-4 py-3 text-sm leading-6 outline-none placeholder:text-muted focus:border-lime"
                />
              </div>

              <div className="flex flex-col-reverse justify-end gap-3 sm:flex-row">
                <button
                  onClick={() => setSelected(null)}
                  className="rounded-xl border border-line px-5 py-3 text-sm text-muted transition hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={() => saveReview(selected)}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-lime px-5 py-3 text-sm font-semibold text-black transition hover:bg-white"
                >
                  Save demo review <ArrowRight size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
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
