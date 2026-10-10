import Link from "next/link";
import { ArrowRight, Braces, Code2 } from "lucide-react";

import { StudentAssignments } from "@/components/student-assignments";

export default function StudentDashboard() {
  return (
    <main className="min-h-screen bg-[#10110F] text-[#F3F4EF]">
      <header className="border-b border-[#2A2D27]">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/student" className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#D5FF62] text-black">
              <Braces size={22} />
            </span>
            <span>
              <span className="block text-lg font-bold">codeviva<span className="text-[#D5FF62]">.</span></span>
              <span className="block text-[10px] uppercase tracking-[0.16em] text-zinc-500">Student workspace</span>
            </span>
          </Link>
          <nav className="flex items-center gap-4 text-sm text-zinc-400">
            <Link href="/student/assignments" className="hover:text-[#D5FF62]">Assignments</Link>
            <Link href="/student/upload" className="hover:text-[#D5FF62]">Practice</Link>
          </nav>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14">
        <section className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <p className="mb-4 text-xs tracking-[0.2em] text-[#D5FF62]">YOUR LEARNING SPACE</p>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-5xl">Make your thinking count.</h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-zinc-400 sm:text-base">
              Find work assigned by your teachers, submit supported code, and answer questions when they are released.
            </p>
          </div>
          <Link
            href="/student/upload"
            className="inline-flex w-fit items-center gap-2 rounded-xl bg-[#D5FF62] px-5 py-3.5 text-sm font-semibold text-black hover:bg-[#E2FF94]"
          >
            <Code2 size={17} /> Open practice workspace <ArrowRight size={16} />
          </Link>
        </section>
        <StudentAssignments />
      </div>
    </main>
  );
}
