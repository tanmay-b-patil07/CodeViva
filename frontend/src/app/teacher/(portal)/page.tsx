"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  ChartNoAxesColumnIncreasing,
  RefreshCw,
  Users,
} from "lucide-react";

import {
  apiRequest,
  AssignmentStudent,
  TeacherAssignment,
  TeacherAssignmentDetail,
} from "@/lib/assignments";

export default function TeacherDashboard() {
  const [assignments, setAssignments] = useState<TeacherAssignment[]>([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState("");
  const [classResults, setClassResults] = useState<TeacherAssignmentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [error, setError] = useState("");
  const [resultsError, setResultsError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const nextAssignments = await apiRequest<TeacherAssignment[]>("/teacher/assignments");
      setAssignments(nextAssignments);
      setSelectedAssignmentId((current) =>
        nextAssignments.some((assignment) => assignment.id === current)
          ? current
          : nextAssignments[0]?.id ?? "",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load teacher data.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadClassResults = useCallback(async () => {
    if (!selectedAssignmentId) {
      setClassResults(null);
      return;
    }
    setResultsLoading(true);
    setResultsError("");
    try {
      setClassResults(
        await apiRequest<TeacherAssignmentDetail>(
          `/teacher/assignments/${selectedAssignmentId}`,
        ),
      );
    } catch (err) {
      setClassResults(null);
      setResultsError(
        err instanceof Error ? err.message : "Could not load class results.",
      );
    } finally {
      setResultsLoading(false);
    }
  }, [selectedAssignmentId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadClassResults();
  }, [loadClassResults]);

  const active = assignments.filter((item) => item.status !== "Past due").length;
  const assignedSeats = assignments.reduce((sum, item) => sum + item.student_count, 0);
  const released = assignments.reduce((sum, item) => sum + item.released_questions, 0);
  const studentsWithMarks = (classResults?.students ?? []).filter(
    (student) => student.score !== null && student.max_score !== null && student.max_score > 0,
  );
  const classAverage = studentsWithMarks.length
    ? studentsWithMarks.reduce(
        (sum, student) =>
          sum + ((student.score ?? 0) / (student.max_score ?? 1)) * 100,
        0,
      ) / studentsWithMarks.length
    : null;

  return (
    <main className="min-h-screen bg-canvas text-white">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
          <Link href="/teacher" className="text-lg font-bold">CodeViva<span className="text-lime">.</span></Link>
          <Link href="/student" className="text-sm text-muted hover:text-lime">
            Student view <ArrowUpRight className="ml-1 inline" size={15} />
          </Link>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <p className="mb-3 text-xs tracking-[0.2em] text-lime">EDUCATOR CONSOLE</p>
            <h1 className="text-4xl font-semibold sm:text-5xl">Teach with insight.</h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-muted">
              Manage assignments, release questions explicitly, and review each class&apos;s submissions and saved marks.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/teacher/groups" className="rounded-lg border border-line px-4 py-3 text-sm hover:border-lime hover:text-lime">
              Manage classes
            </Link>
            <Link href="/teacher/assignments" className="inline-flex items-center gap-2 rounded-lg bg-lime px-4 py-3 text-sm font-semibold text-black hover:bg-white">
              <BookOpen size={16} /> Manage assignments <ArrowRight size={15} />
            </Link>
          </div>
        </div>

        {error && (
          <p role="alert" className="mt-6 rounded-lg border border-red-400/30 bg-red-400/5 px-4 py-3 text-sm text-red-200">{error}</p>
        )}
        <section className="mt-9 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Metric icon={<BookOpen size={18} />} label="All assignments" value={loading ? "…" : String(assignments.length)} />
          <Metric icon={<BookOpen size={18} />} label="Active assignments" value={loading ? "…" : String(active)} />
          <Metric icon={<Users size={18} />} label="Assigned student seats" value={loading ? "…" : String(assignedSeats)} />
          <Metric icon={<BookOpen size={18} />} label="Released questions" value={loading ? "…" : String(released)} />
        </section>

        <section className="mt-7 rounded-2xl border border-line bg-panel p-5 sm:p-6">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="flex items-center gap-2 text-xs tracking-[0.16em] text-lime">
                <ChartNoAxesColumnIncreasing size={16} />
                CLASS PERFORMANCE
              </p>
              <h2 className="mt-2 text-xl font-semibold">Student results by batch</h2>
              <p className="mt-1 max-w-xl text-sm leading-6 text-muted">
                Compare saved marks for every student assigned to a class. Students without evaluated
                answers are shown as pending, not as zero.
              </p>
            </div>
            <label className="w-full text-xs text-muted sm:max-w-sm">
              Class and assignment
              <select
                value={selectedAssignmentId}
                onChange={(event) => setSelectedAssignmentId(event.target.value)}
                disabled={loading || assignments.length === 0}
                className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm text-white outline-none focus:border-lime disabled:opacity-60"
              >
                {assignments.length === 0 && <option value="">No assignments yet</option>}
                {assignments.map((assignment) => (
                  <option key={assignment.id} value={assignment.id}>
                    {assignment.group_name ?? "Class"} · {assignment.title}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {resultsError && (
            <p role="alert" className="mt-5 rounded-lg border border-red-400/30 bg-red-400/5 px-4 py-3 text-sm text-red-200">
              {resultsError}
            </p>
          )}
          {resultsLoading ? (
            <p className="mt-6 rounded-xl border border-line bg-canvas p-6 text-center text-sm text-muted">
              Loading saved class results…
            </p>
          ) : !selectedAssignmentId ? (
            <p className="mt-6 rounded-xl border border-line bg-canvas p-6 text-center text-sm text-muted">
              Create an assignment for a class to see its student results here.
            </p>
          ) : classResults && classResults.students.length === 0 ? (
            <p className="mt-6 rounded-xl border border-line bg-canvas p-6 text-center text-sm text-muted">
              This class has no students assigned to this work yet.
            </p>
          ) : classResults ? (
            <>
              <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted">
                <span>{classResults.assignment.group_name} · {classResults.assignment.title}</span>
                <span>{studentsWithMarks.length} of {classResults.students.length} students evaluated</span>
                <span>
                  {classAverage === null
                    ? "Class average: no saved marks"
                    : `Average of evaluated students: ${classAverage.toFixed(1)}%`}
                </span>
              </div>
              <div className="mt-6 overflow-x-auto rounded-xl border border-line bg-canvas p-4 sm:p-6">
                <div
                  className="flex min-h-56 min-w-max items-end gap-3 border-b border-line pb-3 sm:gap-5"
                  role="list"
                  aria-label={`Individual student marks for ${classResults.assignment.title}`}
                >
                  {classResults.students.map((student) => (
                    <DashboardStudentResult
                      key={student.student_id}
                      student={student}
                      assignmentId={selectedAssignmentId}
                    />
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between gap-3 text-[11px] text-muted">
                  <span>Each bar shows the student&apos;s saved marks as a percentage.</span>
                  <span className="shrink-0">Click a student to open their marks card</span>
                </div>
              </div>
              <Link
                href={`/teacher/assignments/${selectedAssignmentId}`}
                className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-lime hover:text-white"
              >
                Open full class report <ArrowRight size={15} />
              </Link>
            </>
          ) : null}
        </section>

        <section className="mt-7 overflow-hidden rounded-2xl border border-line bg-panel">
          <div className="flex items-center justify-between border-b border-line px-5 py-5 sm:px-6">
            <div>
              <h2 className="font-semibold">Recent assignments</h2>
              <p className="mt-1 text-xs text-muted">Loaded from your teacher account.</p>
            </div>
            <button onClick={() => void load()} aria-label="Refresh" className="rounded-lg border border-line p-2.5 text-muted hover:text-lime">
              <RefreshCw size={16} />
            </button>
          </div>
          {loading ? (
            <p className="p-8 text-center text-sm text-muted">Loading teacher assignments…</p>
          ) : assignments.length === 0 ? (
            <p className="p-8 text-center text-sm text-muted">Create a class and your first assignment to begin.</p>
          ) : (
            <div className="divide-y divide-line">
              {assignments.slice(0, 5).map((assignment) => (
                <Link
                  key={assignment.id}
                  href={`/teacher/assignments/${assignment.id}`}
                  className="flex items-center gap-4 px-5 py-4 hover:bg-white/[0.02] sm:px-6"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{assignment.title}</span>
                    <span className="mt-1 block text-xs text-muted">{assignment.group_name ?? "No class"} · {assignment.student_count} students</span>
                  </span>
                  <span className="text-xs text-muted">{assignment.status}</span>
                  <ArrowRight size={15} className="text-lime" />
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function DashboardStudentResult({
  student,
  assignmentId,
}: {
  student: AssignmentStudent;
  assignmentId: string;
}) {
  const hasScore =
    student.score !== null && student.max_score !== null && student.max_score > 0;
  const percentage = hasScore
    ? Math.min(100, Math.max(0, (student.score! / student.max_score!) * 100))
    : null;

  return (
    <Link
      href={`/teacher/assignments/${assignmentId}/students/${student.student_id}`}
      role="listitem"
      aria-label={`${student.full_name}: ${percentage === null ? "pending evaluation" : `${percentage.toFixed(1)} percent. Open marks card`}`}
      className="group flex w-16 shrink-0 flex-col items-center gap-2 rounded-lg px-1 py-2 transition hover:bg-white/[0.04] focus-visible:outline focus-visible:outline-2 focus-visible:outline-lime sm:w-20"
    >
      <span className="text-xs font-medium text-lime">
        {percentage === null ? "Pending" : `${percentage.toFixed(0)}%`}
      </span>
      <span className="flex h-36 w-full items-end overflow-hidden rounded-t-md bg-panel">
        <span
          className={`block w-full rounded-t-md transition-[height] group-hover:bg-white ${
            percentage === null ? "bg-line" : "bg-lime"
          }`}
          style={{ height: `${percentage === null ? 5 : Math.max(8, percentage)}%` }}
        />
      </span>
      <span className="w-full truncate text-center text-xs text-white group-hover:text-lime">
        {student.full_name}
      </span>
      <span className="w-full truncate text-center text-[10px] text-muted">
        {percentage === null
          ? "Pending evaluation"
          : `${student.score} / ${student.max_score}`}
      </span>
    </Link>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <article className="rounded-2xl border border-line bg-panel p-5">
      <div className="flex items-center gap-2 text-lime">{icon}<span className="text-xs text-muted">{label}</span></div>
      <p className="mt-3 text-2xl font-semibold">{value}</p>
    </article>
  );
}
