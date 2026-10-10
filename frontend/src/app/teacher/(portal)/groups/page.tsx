"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowLeft, Plus, UserPlus } from "lucide-react";

import { apiRequest, TeacherGroup } from "@/lib/assignments";

interface GroupStudent {
  student_id: string;
  full_name: string;
  email: string;
}

export default function TeacherGroupsPage() {
  const [groups, setGroups] = useState<TeacherGroup[]>([]);
  const [members, setMembers] = useState<Record<string, GroupStudent[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [groupName, setGroupName] = useState("");
  const [email, setEmail] = useState("");
  const [selectedGroup, setSelectedGroup] = useState("");
  const [working, setWorking] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const currentGroups = await apiRequest<TeacherGroup[]>("/teacher/groups");
      const memberLists = await Promise.all(
        currentGroups.map(async (group) => [
          group.id,
          await apiRequest<GroupStudent[]>(`/teacher/groups/${group.id}/members`),
        ] as const),
      );
      setGroups(currentGroups);
      setMembers(Object.fromEntries(memberLists));
      setSelectedGroup((current) =>
        currentGroups.some((group) => group.id === current)
          ? current
          : currentGroups[0]?.id ?? "",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load classes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function createGroup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError("");
    try {
      await apiRequest<TeacherGroup>("/teacher/groups", {
        method: "POST",
        body: JSON.stringify({ name: groupName.trim() }),
      });
      setGroupName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the class.");
    } finally {
      setWorking(false);
    }
  }

  async function addStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWorking(true);
    setError("");
    try {
      await apiRequest(`/teacher/groups/${selectedGroup}/members`, {
        method: "POST",
        body: JSON.stringify({ email: email.trim() }),
      });
      setEmail("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add this student.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="min-h-screen bg-canvas text-white">
      <div className="mx-auto max-w-5xl px-5 py-10 sm:px-8">
        <Link href="/teacher" className="inline-flex items-center gap-2 text-sm text-muted hover:text-lime">
          <ArrowLeft size={16} /> Teacher dashboard
        </Link>
        <header className="mt-7">
          <p className="text-xs tracking-[0.2em] text-lime">CLASS MANAGEMENT</p>
          <h1 className="mt-3 text-3xl font-semibold sm:text-4xl">Classes and students</h1>
          <p className="mt-3 text-sm text-muted">Students must have a registered student account before they can be added to a class.</p>
        </header>
        {error && <p role="alert" className="mt-5 rounded-lg border border-red-400/30 bg-red-400/5 px-4 py-3 text-sm text-red-200">{error}</p>}

        <section className="mt-7 grid gap-5 lg:grid-cols-2">
          <form onSubmit={createGroup} className="rounded-2xl border border-line bg-panel p-5">
            <h2 className="font-semibold">Create a class</h2>
            <label className="mt-4 block text-sm">
              Class or batch name
              <input
                required
                maxLength={100}
                value={groupName}
                onChange={(event) => setGroupName(event.target.value)}
                className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 outline-none focus:border-lime"
              />
            </label>
            <button disabled={working} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-lime px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50">
              <Plus size={16} /> Create class
            </button>
          </form>

          <form onSubmit={addStudent} className="rounded-2xl border border-line bg-panel p-5">
            <h2 className="font-semibold">Add a student</h2>
            <label className="mt-4 block text-sm">
              Class
              <select
                required
                value={selectedGroup}
                onChange={(event) => setSelectedGroup(event.target.value)}
                disabled={!groups.length}
                className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 outline-none focus:border-lime"
              >
                {groups.length === 0 && <option value="">Create a class first</option>}
                {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
              </select>
            </label>
            <label className="mt-4 block text-sm">
              Student account email
              <input
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-2 w-full rounded-lg border border-line bg-canvas px-3 py-2.5 outline-none focus:border-lime"
              />
            </label>
            <button disabled={working || !groups.length} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-lime/30 px-4 py-2.5 text-sm text-lime disabled:opacity-50">
              <UserPlus size={16} /> Add to class
            </button>
          </form>
        </section>

        <section className="mt-7 rounded-2xl border border-line bg-panel">
          <div className="border-b border-line px-5 py-5">
            <h2 className="font-semibold">Your classes</h2>
          </div>
          {loading ? (
            <p className="p-8 text-center text-sm text-muted">Loading classes…</p>
          ) : groups.length === 0 ? (
            <p className="p-8 text-center text-sm text-muted">No classes yet.</p>
          ) : (
            <div className="divide-y divide-line">
              {groups.map((group) => (
                <div key={group.id} className="px-5 py-5">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="font-medium">{group.name}</h3>
                    <span className="text-xs text-muted">{members[group.id]?.length ?? 0} students</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(members[group.id] ?? []).map((student) => (
                      <span key={student.student_id} className="rounded-full border border-line px-3 py-1.5 text-xs text-zinc-300">
                        {student.full_name} · {student.email}
                      </span>
                    ))}
                    {!members[group.id]?.length && <span className="text-xs text-muted">No members added.</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
