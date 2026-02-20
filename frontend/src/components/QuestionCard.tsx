"use client";
import { useEffect, useRef, useState } from "react";
import { Question, AnswerResponse, submitAnswer } from "@/lib/api";

interface Props {
  question: Question;
  userId: number;
  index: number;
  total: number;
  onResult: (res: AnswerResponse) => void;
}

const DIFF_LABELS: Record<number, string> = {
  1: "Easy",
  2: "Medium-Easy",
  3: "Medium",
  4: "Hard",
  5: "JEE Advanced",
};
const DIFF_COLORS: Record<number, string> = {
  1: "bg-emerald-900/60 text-emerald-300",
  2: "bg-green-900/60 text-green-300",
  3: "bg-yellow-900/60 text-yellow-300",
  4: "bg-orange-900/60 text-orange-300",
  5: "bg-red-900/60 text-red-300",
};

export default function QuestionCard({ question, userId, index, total, onResult }: Props) {
  const [confidence, setConfidence] = useState(3);
  const [hintUsed, setHintUsed] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const startRef = useRef(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start timer
  useEffect(() => {
    startRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [question.id]);

  async function handleAnswer(isCorrect: boolean) {
    if (timerRef.current) clearInterval(timerRef.current);
    setSubmitting(true);
    const timeTaken = Math.floor((Date.now() - startRef.current) / 1000);
    try {
      const res = await submitAnswer(
        userId,
        question.id,
        isCorrect,
        timeTaken,
        confidence,
        0,
        hintUsed
      );
      onResult(res);
    } catch {
      onResult({
        cms: 0,
        old_skill: 1000,
        new_skill: 1000,
        skill_delta: 0,
        remediation: null,
        message: "Could not record attempt.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <div className="card space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 font-medium">
          Question {index + 1} / {total}
        </span>
        <div className="flex items-center gap-3">
          <span
            className={`badge ${DIFF_COLORS[question.difficulty] ?? "bg-gray-800 text-gray-300"}`}
          >
            {DIFF_LABELS[question.difficulty] ?? `Level ${question.difficulty}`}
          </span>
          <span className="text-xs font-mono text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
            {mm}:{ss}
          </span>
        </div>
      </div>

      {/* Subtopics */}
      <div className="flex flex-wrap gap-1.5">
        {question.subtopics.map((s) => (
          <span key={s} className="badge bg-brand-900/50 text-brand-300 border border-brand-800/50">
            {s.replace(/_/g, " ")}
          </span>
        ))}
      </div>

      {/* Question text */}
      <div className="bg-gray-800/50 rounded-xl p-4 text-gray-100 text-base leading-relaxed whitespace-pre-wrap border border-gray-700/50">
        {question.text}
      </div>

      {/* Hint toggle */}
      <label className="flex items-center gap-2.5 cursor-pointer select-none w-fit">
        <div
          onClick={() => setHintUsed(!hintUsed)}
          className={`w-10 h-5 rounded-full relative transition-colors ${
            hintUsed ? "bg-amber-500" : "bg-gray-700"
          }`}
        >
          <div
            className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
              hintUsed ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </div>
        <span className="text-sm text-gray-400">
          {hintUsed ? "✦ Hint used (reduces score)" : "Use hint"}
        </span>
      </label>

      {/* Confidence slider */}
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1.5">
          <span>Confidence</span>
          <span className="font-semibold text-gray-300">
            {["", "Guessing", "Unsure", "Okay", "Confident", "Very sure"][confidence]}
          </span>
        </div>
        <input
          type="range"
          min={1}
          max={5}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          className="w-full accent-brand-500 h-1.5 cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-600 mt-0.5">
          <span>1</span>
          <span>2</span>
          <span>3</span>
          <span>4</span>
          <span>5</span>
        </div>
      </div>

      {/* Answer buttons */}
      <div className="grid grid-cols-2 gap-3 pt-2">
        <button
          onClick={() => handleAnswer(false)}
          disabled={submitting}
          className="py-3 rounded-xl bg-red-900/40 hover:bg-red-800/50 border border-red-800/60 text-red-300 font-semibold text-sm transition-colors disabled:opacity-40"
        >
          ✗ Got it wrong
        </button>
        <button
          onClick={() => handleAnswer(true)}
          disabled={submitting}
          className="py-3 rounded-xl bg-emerald-900/40 hover:bg-emerald-800/50 border border-emerald-800/60 text-emerald-300 font-semibold text-sm transition-colors disabled:opacity-40"
        >
          ✓ Got it right
        </button>
      </div>
    </div>
  );
}
