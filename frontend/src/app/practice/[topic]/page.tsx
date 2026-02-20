"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { startPractice, AnswerResponse, Question } from "@/lib/api";
import { getUser } from "@/lib/auth";
import QuestionCard from "@/components/QuestionCard";
import Link from "next/link";

interface Result extends AnswerResponse {
  questionIndex: number;
}

export default function PracticePage() {
  const params = useParams();
  const router = useRouter();
  const topic = params.topic as string;

  const [questions, setQuestions] = useState<Question[]>([]);
  const [current, setCurrent] = useState(0);
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [userId, setUserId] = useState<number | null>(null);

  useEffect(() => {
    const user = getUser();
    if (!user) { router.push("/login"); return; }
    setUserId(user.user_id);

    startPractice(user.user_id, topic, 5)
      .then((res) => setQuestions(res.questions))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [topic, router]);

  function handleResult(res: AnswerResponse) {
    const newResults = [...results, { ...res, questionIndex: current }];
    setResults(newResults);
    if (current + 1 >= questions.length) {
      setDone(true);
    } else {
      setCurrent(current + 1);
    }
  }

  const topicLabel = topic.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  // ── Loading ──
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-gray-400 text-sm">Loading questions for {topicLabel}…</p>
        </div>
      </div>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="card max-w-md text-center space-y-4">
          <p className="text-red-400">{error}</p>
          <Link href="/dashboard" className="btn-ghost">← Back to dashboard</Link>
        </div>
      </div>
    );
  }

  // ── No questions ──
  if (questions.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="card max-w-md text-center space-y-4">
          <p className="text-gray-400">No questions found for this topic yet.</p>
          <Link href="/dashboard" className="btn-ghost">← Back to dashboard</Link>
        </div>
      </div>
    );
  }

  // ── Session summary ──
  if (done) {
    const correct = results.filter((r) => r.skill_delta > 0).length;
    const avgCms = results.reduce((s, r) => s + r.cms, 0) / results.length;
    const lastSkill = results[results.length - 1]?.new_skill ?? 1000;
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-md space-y-4">
          <div className="card text-center space-y-4">
            <div className="text-4xl">{correct === results.length ? "🎉" : correct === 0 ? "📚" : "💪"}</div>
            <h2 className="text-2xl font-bold">Session Complete</h2>
            <p className="text-gray-400 text-sm">{topicLabel}</p>

            <div className="grid grid-cols-3 gap-3 mt-4">
              <StatBox label="Score" value={`${correct}/${results.length}`} />
              <StatBox label="Avg CMS" value={`${(avgCms * 100).toFixed(0)}%`} />
              <StatBox label="Skill" value={Math.round(lastSkill).toString()} />
            </div>

            {results.some((r) => r.remediation) && (
              <div className="bg-amber-900/30 border border-amber-700/50 rounded-xl p-4 text-left mt-2">
                <p className="text-amber-300 text-xs font-semibold mb-2">📖 Remediation tip</p>
                <p className="text-amber-100 text-sm leading-relaxed">
                  {results.find((r) => r.remediation)!.remediation}
                </p>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => { setCurrent(0); setResults([]); setDone(false); setLoading(true);
                getUser() && startPractice(getUser()!.user_id, topic, 5)
                  .then((r) => setQuestions(r.questions))
                  .catch((e) => setError(e.message))
                  .finally(() => setLoading(false));
              }}
              className="btn-primary flex-1"
            >
              Practice again
            </button>
            <Link href="/dashboard" className="btn-ghost flex-1 text-center">
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Active question ──
  return (
    <div className="min-h-screen p-4 flex flex-col">
      {/* Nav */}
      <div className="flex items-center justify-between mb-4 max-w-2xl mx-auto w-full">
        <Link href="/dashboard" className="text-gray-500 hover:text-gray-300 text-sm">
          ← Dashboard
        </Link>
        <span className="text-gray-400 text-sm font-medium">{topicLabel}</span>
        {userId && (
          <Link href="/doubt" className="text-brand-400 hover:text-brand-300 text-sm">
            Ask doubt
          </Link>
        )}
      </div>

      {/* Progress bar */}
      <div className="max-w-2xl mx-auto w-full mb-5">
        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-500 rounded-full transition-all duration-500"
            style={{ width: `${((current) / questions.length) * 100}%` }}
          />
        </div>
      </div>

      <div className="max-w-2xl mx-auto w-full flex-1">
        {userId && (
          <QuestionCard
            key={questions[current].id}
            question={questions[current]}
            userId={userId}
            index={current}
            total={questions.length}
            onResult={handleResult}
          />
        )}
      </div>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800 rounded-xl p-3 text-center">
      <div className="text-xl font-bold text-brand-400">{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
