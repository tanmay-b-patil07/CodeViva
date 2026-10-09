import Link from "next/link";

import {

  ArrowDownRight,

  ArrowRight,


  Braces,

  Check,

  ChevronRight,

  CircleDot,

  Code2,

  FileCode2,

  Fingerprint,


  Terminal,

  Zap,

} from "lucide-react";

const codeLines = [

  { n: "01", code: "def mystery(nums):", color: "text-lime" },

  { n: "02", code: "    result = 0", color: "text-zinc-300" },

  { n: "03", code: "    for n in nums:", color: "text-zinc-300" },

  { n: "04", code: "        if n % 2 == 0:", color: "text-zinc-300" },

  { n: "05", code: "            result += n", color: "text-zinc-300" },

  { n: "06", code: "    return result", color: "text-lime" },

];

export default function Home() {

  return (

    <main className="min-h-screen overflow-hidden bg-canvas text-zinc-100">

      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-10">

        <Link href="/" className="flex items-center gap-3">

          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-lime text-black">

            <Braces size={21} strokeWidth={2.5} />

          </div>

          <span className="text-lg font-bold tracking-tight">

            codeviva<span className="text-lime">.</span>

          </span>

        </Link>

        <nav className="hidden items-center gap-8 text-sm text-zinc-400 md:flex">

          <a href="#how-it-works" className="transition hover:text-white">

            How it works

          </a>

          <a href="#for-whom" className="transition hover:text-white">

            For students

          </a>

          <a href="#for-whom" className="transition hover:text-white">

            For educators

          </a>

        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/student/login"
            className="rounded-full border border-line px-4 py-2.5 text-sm font-medium transition hover:border-lime hover:text-lime"
          >
            Student sign in
          </Link>
          <Link
            href="/teacher/login"
            className="rounded-full bg-lime px-4 py-2.5 text-sm font-semibold text-black transition hover:bg-[#e2ff94]"
          >
            Teacher sign in
          </Link>
        </div>

      </header>

      <section className="mx-auto grid max-w-7xl items-center gap-16 px-6 pb-24 pt-16 lg:grid-cols-[1.02fr_0.98fr] lg:px-10 lg:pb-32 lg:pt-24">

        <div className="relative z-10">

          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-2 text-xs text-zinc-300">

            <span className="h-2 w-2 rounded-full bg-lime" />

            CODE COMPREHENSION, REIMAGINED

          </div>

          <h1 className="max-w-2xl text-5xl font-semibold leading-[1.08] tracking-[-0.055em] sm:text-6xl lg:text-7xl">

            Writing code is easy.

            <br />

            <span className="text-zinc-500">Understanding it</span>

            <br />

            <span className="text-lime">is the test.</span>

          </h1>

          <p className="mt-7 max-w-lg text-base leading-7 text-zinc-400 sm:text-lg sm:leading-8">

            CodeViva turns submitted code into meaningful comprehension

            questions, helping students prove what they know and educators

            see how they think.

          </p>

          <div className="mt-9 flex flex-wrap items-center gap-4">

            <Link

              href="/student/login"

              className="group inline-flex items-center gap-3 rounded-xl bg-lime px-5 py-3.5 font-semibold text-black transition hover:bg-[#e2ff94]"

            >

              Enter the workspace

              <ArrowRight size={18} className="transition group-hover:translate-x-1" />

            </Link>

            <a

              href="#how-it-works"

              className="inline-flex items-center gap-2 rounded-xl px-4 py-3 text-sm text-zinc-300 transition hover:text-lime"

            >

              See how it works <ArrowDownRight size={16} />

            </a>

          </div>

          <div className="mt-12 flex flex-wrap items-center gap-x-7 gap-y-3 border-t border-line pt-6 text-xs text-zinc-500">

            <span className="flex items-center gap-2">

              <Check size={14} className="text-lime" />

              Code-based questions

            </span>

            <span className="flex items-center gap-2">

              <Check size={14} className="text-lime" />

              Evidence-led evaluation

            </span>

          </div>

        </div>

        <div className="relative">

          <div className="absolute -inset-8 rounded-full bg-lime/[0.06] blur-3xl" />

          <div className="relative overflow-hidden rounded-2xl border border-[#34372e] bg-[#151713] shadow-2xl shadow-black/30">

            <div className="flex items-center justify-between border-b border-line px-5 py-4">

              <div className="flex items-center gap-3">

                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#262a20] text-lime">

                  <FileCode2 size={17} />

                </div>

                <div>

                  <p className="text-sm font-medium">untitled.py</p>

                  <p className="mt-0.5 text-[11px] text-zinc-500">Python · Sample snippet</p>

                </div>

              </div>

              <div className="flex items-center gap-2 rounded-full border border-line px-2.5 py-1 text-[10px] text-zinc-400">

                <CircleDot size={11} className="text-lime" />

                PREVIEW

              </div>

            </div>

            <div className="grid grid-cols-[1fr_0.88fr]">

              <div className="border-r border-line px-3 py-6 sm:px-5">

                <div className="mb-5 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-zinc-500">

                  <Terminal size={13} /> Source code

                </div>

                <div className="space-y-4 font-mono text-[11px] sm:text-xs">

                  {codeLines.map((line) => (

                    <div key={line.n} className="flex gap-4 whitespace-pre">

                      <span className="select-none text-zinc-600">{line.n}</span>

                      <span className={line.color}>{line.code}</span>

                    </div>

                  ))}

                </div>

                <div className="mt-8 rounded-lg border border-line bg-black/20 p-3">

                  <p className="text-[10px] uppercase tracking-widest text-zinc-500">

                    Function

                  </p>

                  <p className="mt-2 font-mono text-xs text-zinc-300">

                    mystery(nums)

                  </p>

                </div>

              </div>

              <div className="px-3 py-6 sm:px-5">

                <div className="mb-5 flex items-center gap-2 text-[10px] uppercase tracking-[0.14em] text-zinc-500">

                  <Fingerprint size={14} /> Understanding

                </div>

                <div className="rounded-xl border border-[#414832] bg-[#20241b] p-3 sm:p-4">

                  <div className="flex items-center justify-between gap-2">

                    <span className="text-xs font-medium">Question 01</span>

                    <span className="rounded-md bg-lime/10 px-2 py-1 text-[9px] text-lime">

                      LOGIC

                    </span>

                  </div>

                  <p className="mt-4 text-xs leading-5 text-zinc-200 sm:text-sm sm:leading-6">

                    What does this function return when given a list of

                    integers?

                  </p>

                  <div className="mt-4 space-y-2">

                    {[

                      "The sum of all numbers",

                      "The sum of even numbers",

                      "The count of even numbers",

                    ].map((answer, index) => (

                      <div

                        key={answer}

                        className={`rounded-lg border p-2.5 text-[10px] leading-4 sm:text-[11px] ${

                          index === 1

                            ? "border-lime/60 bg-lime/10 text-lime"

                            : "border-line text-zinc-400"

                        }`}

                      >

                        <span className="mr-2 text-zinc-500">

                          {String.fromCharCode(65 + index)}.

                        </span>

                        {answer}

                      </div>

                    ))}

                  </div>

                </div>

                <div className="mt-4 rounded-xl border border-line p-3">

                  <div className="flex items-center gap-2 text-xs text-zinc-300">

                    <Zap size={14} className="text-lime" />

                    Comprehension checkpoint

                  </div>

                  <p className="mt-2 text-[11px] leading-5 text-zinc-500">

                    Test the reasoning behind the code, not just the output.

                  </p>

                </div>

              </div>

            </div>

            <div className="flex items-center justify-between border-t border-line px-5 py-3 text-[10px] text-zinc-500">

              <span className="flex items-center gap-2">

                <span className="h-1.5 w-1.5 rounded-full bg-lime" />

                Interactive preview

              </span>

              <span>CODEVIVA / 001</span>

            </div>

          </div>

          <div className="absolute -bottom-5 -left-4 hidden rounded-xl border border-line bg-panel px-4 py-3 shadow-xl sm:block">

            <p className="text-[10px] text-zinc-500">THE GOAL</p>

            <p className="mt-1 text-xs font-medium text-zinc-200">

              Reasoning over memorization.

            </p>

          </div>

        </div>

      </section>

      <section

        id="how-it-works"

        className="border-y border-line bg-[#141512] px-6 py-20 lg:px-10"

      >

        <div className="mx-auto max-w-7xl">

          <div className="max-w-2xl">

            <p className="text-xs font-medium uppercase tracking-[0.2em] text-lime">

              THE WORKFLOW

            </p>

            <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">

              From code to comprehension.

            </h2>

            <p className="mt-4 leading-7 text-zinc-400">

              A simple process designed to make understanding visible.

            </p>

          </div>

          <div className="mt-12 grid gap-4 md:grid-cols-3">

            {[

              {

                number: "01",

                title: "Submit your code",

                text: "Start with a code snippet and examine its structure and logic.",

                icon: Code2,

              },

              {

                number: "02",

                title: "Explain your thinking",

                text: "Answer questions about behaviour, control flow and reasoning.",

                icon: Braces,

              },

              {

                number: "03",

                title: "See the evidence",

                text: "Review answers, feedback and comprehension results.",

                icon: Fingerprint,

              },

            ].map((step) => {

              const Icon = step.icon;

              return (

                <article

                  key={step.number}

                  className="group rounded-2xl border border-line bg-panel p-6 transition hover:-translate-y-1 hover:border-[#4a503b]"

                >

                  <div className="flex items-center justify-between">

                    <span className="font-mono text-xs text-zinc-500">

                      / {step.number}

                    </span>

                    <Icon

                      size={20}

                      className="text-zinc-500 transition group-hover:text-lime"

                    />

                  </div>

                  <h3 className="mt-9 text-lg font-medium">{step.title}</h3>

                  <p className="mt-3 text-sm leading-6 text-zinc-400">

                    {step.text}

                  </p>

                </article>

              );

            })}

          </div>

        </div>

      </section>

      <section

        id="for-whom"

        className="mx-auto flex max-w-7xl flex-col justify-between gap-8 px-6 py-16 sm:flex-row sm:items-center lg:px-10"

      >

        <div>

          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">

            BUILT FOR BOTH SIDES

          </p>

          <h2 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">

            Understanding should be visible.

          </h2>

          <p className="mt-3 max-w-xl text-sm leading-6 text-zinc-400">

            A shared platform for student practice and teacher-led assessment.

          </p>

        </div>

        <div className="flex flex-wrap gap-3">

          <Link
            href="/student/login"
            className="inline-flex items-center gap-2 rounded-xl bg-lime px-5 py-3 text-sm font-semibold text-black transition hover:bg-[#e2ff94]"
          >
            Student sign in <ArrowRight size={16} />
          </Link>
          <Link
            href="/student/register"
            className="inline-flex items-center gap-2 rounded-xl border border-line px-5 py-3 text-sm text-zinc-200 transition hover:border-zinc-500"
          >
            Student register <ChevronRight size={16} />
          </Link>
          <Link
            href="/teacher/login"
            className="inline-flex items-center gap-2 rounded-xl border border-line px-5 py-3 text-sm text-zinc-200 transition hover:border-zinc-500"
          >
            Teacher sign in <ArrowRight size={16} />
          </Link>
          <Link
            href="/teacher/register"
            className="inline-flex items-center gap-2 rounded-xl border border-line px-5 py-3 text-sm text-zinc-200 transition hover:border-zinc-500"
          >
            Teacher register <ChevronRight size={16} />
          </Link>

        </div>

      </section>

      <footer className="border-t border-line px-6 py-6 lg:px-10">

        <div className="mx-auto flex max-w-7xl flex-col gap-3 text-xs text-zinc-500 sm:flex-row sm:items-center sm:justify-between">

          <Link href="/" className="font-semibold tracking-tight text-zinc-300">

            codeviva<span className="text-lime">.</span>

          </Link>

          <p>Built to make understanding count.</p>

          <p>CodeViva · Hackathon project</p>

        </div>

      </footer>

    </main>

  );

}
