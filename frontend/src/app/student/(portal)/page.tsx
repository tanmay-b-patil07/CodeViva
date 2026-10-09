
import Link from "next/link";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Braces,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Code2,
  Flame,
  GraduationCap,
  Layers3,
  Plus,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";

const activities = [
  {
    title: "Loops & conditions",
    type: "Practice session",
    date: "Demo activity",
    score: "8/10",
    status: "Completed",
  },
  {
    title: "Function tracing",
    type: "Code comprehension",
    date: "Demo activity",
    score: "6/8",
    status: "Completed",
  },
  {
    title: "List operations",
    type: "Practice session",
    date: "Demo activity",
    score: "—",
    status: "In progress",
  },
];

export default function StudentDashboard() {
  return (
    <main className="min-h-screen bg-[#10110F] text-[#F3F4EF]">
      <header className="border-b border-[#2A2D27]">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#D5FF62] text-black">
              <Braces size={22} strokeWidth={2.4} />
            </div>
            <div>
              <p className="text-lg font-bold tracking-tight">
                codeviva<span className="text-[#D5FF62]">.</span>
              </p>
              <p className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">
                Student workspace
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <Link
              href="/student/exams"
              className="hidden rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:text-white sm:block"
            >
              My exams
            </Link>
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-[#414832] bg-[#20241B] text-xs font-semibold text-[#D5FF62]">
              S
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8 sm:py-10">
        <section className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <div className="mb-4 flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-[#D5FF62]">
              <span className="h-px w-6 bg-[#D5FF62]" />
              YOUR LEARNING SPACE
            </div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl lg:text-5xl">
              Make your thinking count.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-zinc-400 sm:text-base">
              Understand the logic. Explain the output. Build confidence one
              question at a time.
            </p>
          </div>

          <Link
            href="/student/upload"
            className="inline-flex items-center justify-center gap-2 self-start rounded-xl bg-[#D5FF62] px-5 py-3.5 text-sm font-semibold text-black transition hover:bg-[#E2FF94] lg:self-auto"
          >
            <Plus size={17} />
            Start a practice session
            <ArrowUpRight size={16} />
          </Link>
        </section>

        <section className="mt-9 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={<Layers3 size={18} />}
            label="Practice sessions"
            value="03"
            note="Illustrative demo data"
          />
          <StatCard
            icon={<Target size={18} />}
            label="Average score"
            value="78%"
            note="Sample performance"
          />
          <StatCard
            icon={<Flame size={18} />}
            label="Learning streak"
            value="04 days"
            note="Demo streak"
          />
          <StatCard
            icon={<Clock3 size={18} />}
            label="Time invested"
            value="1h 25m"
            note="Sample learning time"
          />
        </section>

        <section className="mt-7 grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
          <div className="overflow-hidden rounded-2xl border border-[#2A2D27] bg-[#151713]">
            <div className="flex items-center justify-between border-b border-[#2A2D27] px-5 py-5 sm:px-6">
              <div>
                <p className="text-base font-semibold">Pick up where you left off</p>
                <p className="mt-1 text-xs text-zinc-500">
                  Practice by understanding, not memorising.
                </p>
              </div>
              <div className="hidden h-10 w-10 items-center justify-center rounded-xl bg-[#24281F] text-[#D5FF62] sm:flex">
                <Code2 size={19} />
              </div>
            </div>

            <div className="p-5 sm:p-6">
              <div className="relative overflow-hidden rounded-xl border border-[#34372E] bg-[#121310] p-5 sm:p-7">
                <div className="pointer-events-none absolute -right-10 -top-10 h-48 w-48 rounded-full bg-[#D5FF62]/[0.06] blur-3xl" />

                <div className="relative">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md border border-[#414832] px-2 py-1 text-[10px] text-[#D5FF62]">
                      PYTHON
                    </span>
                    <span className="text-[11px] text-zinc-500">
                      STARTER EXERCISE
                    </span>
                  </div>

                  <h2 className="mt-5 text-xl font-semibold tracking-tight sm:text-2xl">
                    Can you explain this function?
                  </h2>
                  <p className="mt-3 max-w-lg text-sm leading-6 text-zinc-400">
                    Explore a short code snippet and answer questions about
                    its logic, output and edge cases.
                  </p>

                  <div className="mt-6 overflow-hidden rounded-lg border border-[#2A2D27] bg-[#0D0E0C]">
                    <div className="flex items-center gap-2 border-b border-[#2A2D27] px-4 py-3">
                      <span className="h-2 w-2 rounded-full bg-[#D5FF62]" />
                      <span className="font-mono text-[11px] text-zinc-400">
                        main.py
                      </span>
                    </div>
                    <div className="overflow-x-auto p-4 font-mono text-xs leading-7 sm:text-sm">
                      <p>
                        <span className="mr-4 text-zinc-600">01</span>
                        <span className="text-[#D5FF62]">def</span>
                        <span className="text-sky-300"> mystery</span>
                        <span className="text-zinc-300">(nums):</span>
                      </p>
                      <p>
                        <span className="mr-4 text-zinc-600">02</span>
                        <span className="text-zinc-500">{"    "}</span>
                        <span className="text-zinc-300">result = 0</span>
                      </p>
                      <p>
                        <span className="mr-4 text-zinc-600">03</span>
                        <span className="text-zinc-500">{"    "}</span>
                        <span className="text-[#D5FF62]">for</span>
                        <span className="text-zinc-300"> n </span>
                        <span className="text-[#D5FF62]">in</span>
                        <span className="text-zinc-300"> nums:</span>
                      </p>
                      <p>
                        <span className="mr-4 text-zinc-600">04</span>
                        <span className="text-zinc-500">{"        "}</span>
                        <span className="text-[#D5FF62]">if</span>
                        <span className="text-zinc-300"> n % 2 == 0:</span>
                      </p>
                      <p>
                        <span className="mr-4 text-zinc-600">05</span>
                        <span className="text-zinc-500">{"            "}</span>
                        <span className="text-zinc-300">result += n</span>
                      </p>
                    </div>
                  </div>

                  <Link
                    href="/student/upload"
                    className="mt-6 inline-flex items-center gap-2 rounded-lg bg-[#D5FF62] px-4 py-3 text-sm font-semibold text-black transition hover:bg-[#E2FF94]"
                  >
                    Open code workspace <ArrowRight size={16} />
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <aside className="flex flex-col gap-5">
            <div className="rounded-2xl border border-[#2A2D27] bg-[#151713] p-5 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold">Your progress</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Sample learning overview
                  </p>
                </div>
                <TrendingUp size={19} className="text-[#D5FF62]" />
              </div>

              <div className="mt-7 flex items-end justify-between">
                <div>
                  <p className="text-3xl font-semibold">78%</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Sample comprehension score
                  </p>
                </div>
                <span className="text-xs text-[#D5FF62]">Demo</span>
              </div>

              <div className="mt-5 h-2 overflow-hidden rounded-full bg-[#292C25]">
                <div className="h-full w-[78%] rounded-full bg-[#D5FF62]" />
              </div>

              <div className="mt-6 space-y-4">
                <ProgressRow label="Control flow" value={85} />
                <ProgressRow label="Functions" value={72} />
                <ProgressRow label="Edge cases" value={60} />
              </div>

              <p className="mt-5 text-[10px] leading-5 text-zinc-600">
                Illustrative values only. Real progress will appear after API
                integration.
              </p>
            </div>

            <div className="rounded-2xl border border-[#2A2D27] bg-[#151713] p-5 sm:p-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#24281F] text-[#D5FF62]">
                  <CalendarDays size={19} />
                </div>
                <div>
                  <p className="font-semibold">Assessment centre</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    Keep track of your exams
                  </p>
                </div>
              </div>

              <div className="mt-5 rounded-xl border border-[#2A2D27] bg-[#121310] p-4">
                <p className="text-sm font-medium">Ready for a challenge?</p>
                <p className="mt-2 text-xs leading-5 text-zinc-500">
                  View your scheduled assessments and prepare before exam
                  time.
                </p>
                <Link
                  href="/student/exams"
                  className="mt-4 inline-flex items-center gap-2 text-xs font-medium text-[#D5FF62] hover:text-white"
                >
                  View my exams <ChevronRight size={14} />
                </Link>
              </div>
            </div>
          </aside>
        </section>

        <section className="mt-7 overflow-hidden rounded-2xl border border-[#2A2D27] bg-[#151713]">
          <div className="flex flex-col justify-between gap-3 border-b border-[#2A2D27] px-5 py-5 sm:flex-row sm:items-center sm:px-6">
            <div>
              <h2 className="font-semibold">Recent activity</h2>
              <p className="mt-1 text-xs text-zinc-500">
                Example sessions to demonstrate the dashboard.
              </p>
            </div>
            <span className="inline-flex items-center gap-2 self-start rounded-full border border-[#2A2D27] px-3 py-1.5 text-[10px] text-zinc-400">
              <BookOpen size={12} />
              DEMO HISTORY
            </span>
          </div>

          <div className="divide-y divide-[#2A2D27]">
            {activities.map((activity) => (
              <div
                key={activity.title}
                className="flex flex-col gap-3 px-5 py-4 transition hover:bg-white/[0.015] sm:flex-row sm:items-center sm:px-6"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#2A2D27] bg-[#1C1E19] text-zinc-400">
                  {activity.status === "Completed" ? (
                    <CheckCircle2 size={17} className="text-[#D5FF62]" />
                  ) : (
                    <Sparkles size={17} className="text-[#D5FF62]" />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{activity.title}</p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {activity.type} · {activity.date}
                  </p>
                </div>

                <div className="flex items-center justify-between gap-4 sm:justify-end">
                  <span className="text-sm font-medium text-zinc-300">
                    {activity.score}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[10px] ${
                      activity.status === "Completed"
                        ? "bg-[#D5FF62]/10 text-[#D5FF62]"
                        : "bg-[#2A2D27] text-zinc-400"
                    }`}
                  >
                    {activity.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <footer className="mt-8 flex flex-col gap-2 border-t border-[#2A2D27] pt-5 text-[11px] text-zinc-600 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2">
            <GraduationCap size={14} />
            CodeViva · Student workspace
          </p>
          <p>All scores and activity shown are sample data.</p>
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
    <article className="rounded-2xl border border-[#2A2D27] bg-[#151713] p-5 transition hover:border-[#414832]">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-400">{label}</span>
        <span className="text-[#D5FF62]">{icon}</span>
      </div>
      <p className="mt-5 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-[10px] text-zinc-600">{note}</p>
    </article>
  );
}

function ProgressRow({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="font-mono text-zinc-300">{value}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#292C25]">
        <div
          className="h-full rounded-full bg-[#D5FF62]"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
