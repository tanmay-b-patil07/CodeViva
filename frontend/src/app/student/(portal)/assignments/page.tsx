import Link from "next/link";
import { StudentAssignments } from "@/components/student-assignments";

export default function StudentAssignmentsPage() {
  return (
    <main className="min-h-screen bg-[#10110F] text-[#F3F4EF]">
      <header className="border-b border-[#2A2D27] px-5 py-5 sm:px-8">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link href="/student" className="font-bold">codeviva<span className="text-[#D5FF62]">.</span></Link>
          <Link href="/student" className="text-sm text-zinc-400 hover:text-[#D5FF62]">Dashboard</Link>
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
        <p className="text-xs tracking-[0.2em] text-[#D5FF62]">STUDENT WORKSPACE</p>
        <h1 className="mt-3 text-3xl font-semibold">Assigned work</h1>
        <StudentAssignments />
      </div>
    </main>
  );
}
