"use client";
import { useEffect, useRef, useState } from "react";
import { Question, AnswerResponse, submitAnswer, getHint } from "@/lib/api";
import MathText from "@/components/MathText";

interface Props {
  question: Question;
  userId: number;
  index: number;
  total: number;
  onResult: (res: AnswerResponse) => void;
}

// ── MCQ + Numerical with retry logic ─────────────────────────────────────────

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
  const [selectedOption, setSelectedOption] = useState("");   // MCQ
  const [userAnswer, setUserAnswer] = useState("");           // Numerical
  const [retries, setRetries] = useState(0);
  const [localIncorrect, setLocalIncorrect] = useState(false);
  const [hintUsed, setHintUsed] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [hintLoading, setHintLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<AnswerResponse | null>(null);
  const startRef = useRef(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isMCQ = question.question_type === "mcq";

  useEffect(() => {
    setSelectedOption("");
    setUserAnswer("");
    setRetries(0);
    setLocalIncorrect(false);
    setHintUsed(false);
    setHint(null);
    setHintLoading(false);
    setElapsed(0);
    setSubmitting(false);
    setSubmitted(false);
    setResult(null);
    startRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
    }, 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [question.id]);

  function gradeLocally(answer: string): boolean {
    if (isMCQ) {
      return answer.toUpperCase() === (question.correct_option || "").toUpperCase();
    }
    try {
      const uv = parseFloat(answer);
      const cv = parseFloat(question.correct_answer || "");
      if (!isNaN(uv) && !isNaN(cv)) return Math.abs(uv - cv) < 0.01;
    } catch { /* fall through */ }
    return answer.trim().toLowerCase() === (question.correct_answer || "").trim().toLowerCase();
  }

  async function handleSubmit() {
    const answer = isMCQ ? selectedOption : userAnswer.trim();
    if (!answer || submitting) return;

    const isCorrect = gradeLocally(answer);

    // First wrong attempt — show retry prompt, no backend call yet
    if (!isCorrect && retries < 1) {
      setLocalIncorrect(true);
      setRetries(1);
      return;
    }

    // Final submission (correct OR retries exhausted)
    if (timerRef.current) clearInterval(timerRef.current);
    setSubmitting(true);
    const timeTaken = Math.floor((Date.now() - startRef.current) / 1000);
    try {
      const res = await submitAnswer(userId, question.id, answer, timeTaken, retries, hintUsed);
      setResult(res);
      setSubmitted(true);
    } catch {
      const fallback: AnswerResponse = {
        cms: isCorrect ? (retries === 0 ? 0.85 : 0.55) : 0,
        old_skill: 1000, new_skill: 1000, skill_delta: 0,
        remediation: null,
        message: isCorrect ? "Correct!" : "Incorrect.",
        is_correct: isCorrect,
        correct_answer: question.correct_answer || "",
        explanation: isCorrect
          ? "Correct!"
          : `The correct answer is ${isMCQ ? question.correct_option : question.correct_answer}.`,
      };
      setResult(fallback);
      setSubmitted(true);
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
          <span className="text-xs text-gray-500 font-medium uppercase tracking-wide border border-gray-700 px-2 py-0.5 rounded">
            {isMCQ ? "MCQ" : "Numerical"}
          </span>
          <span className={`badge ${DIFF_COLORS[question.difficulty] ?? "bg-gray-800 text-gray-300"}`}>
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
      <div className="bg-gray-800/50 rounded-xl p-4 text-gray-100 text-base leading-relaxed border border-gray-700/50">
        <MathText text={question.text} />
      </div>

      {!submitted ? (
        <>
          {/* Hint toggle */}
          <div className="space-y-2">
            <label className="flex items-center gap-2.5 cursor-pointer select-none w-fit">
              <div
                onClick={async () => {
                  if (!hintUsed) {
                    setHintUsed(true);
                    if (!hint) {
                      setHintLoading(true);
                      try {
                        const res = await getHint(question.id);
                        setHint(res.hint);
                      } catch {
                        setHint("Think about the key formula for this topic and apply it step by step.");
                      } finally {
                        setHintLoading(false);
                      }
                    }
                  } else {
                    setHintUsed(false);
                  }
                }}
                className={`w-10 h-5 rounded-full relative transition-colors ${hintUsed ? "bg-amber-500" : "bg-gray-700"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${hintUsed ? "translate-x-5" : "translate-x-0.5"}`} />
              </div>
              <span className="text-sm text-gray-400">
                {hintUsed ? "✦ Hint used (reduces score)" : "Use hint"}
              </span>
            </label>
            {hintUsed && (
              <div className="bg-amber-900/20 border border-amber-700/40 rounded-xl px-4 py-3 text-sm">
                {hintLoading ? (
                  <div className="flex items-center gap-2 text-amber-400">
                    <span className="w-3.5 h-3.5 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
                    Generating hint…
                  </div>
                ) : hint ? (
                  <div className="text-amber-200">
                    <span className="font-semibold text-amber-400 mr-1">Hint:</span>
                    <MathText text={hint} />
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {/* Answer input — MCQ or Numerical, hidden while retry prompt is shown */}
          {!localIncorrect ? (
            <>
              {isMCQ ? (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wide">
                    Select the correct option
                  </label>
                  <div className="space-y-2">
                    {(["A", "B", "C", "D"] as const).map((opt) => {
                      const optText = question.options?.[opt] ?? "";
                      if (!optText) return null;
                      const isSelected = selectedOption === opt;
                      return (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => setSelectedOption(opt)}
                          className={`w-full flex items-start gap-3 p-3 rounded-xl border text-left transition-all ${
                            isSelected
                              ? "border-brand-500 bg-brand-900/30 text-white"
                              : "border-gray-700 bg-gray-800/40 text-gray-300 hover:border-gray-500 hover:bg-gray-800/70"
                          }`}
                        >
                          <span className={`mt-0.5 w-6 h-6 shrink-0 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors ${
                            isSelected ? "border-brand-400 bg-brand-500 text-white" : "border-gray-600 text-gray-400"
                          }`}>
                            {opt}
                          </span>
                          <span className="text-sm leading-relaxed">
                            <MathText text={optText} />
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-gray-400 uppercase tracking-wide">
                    Your Answer (enter a number)
                  </label>
                  <input
                    type="number"
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                    placeholder="e.g. 42 or 3.5"
                    className="w-full bg-gray-800/70 border border-gray-700 rounded-xl px-4 py-3 text-gray-100 text-lg font-mono placeholder-gray-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/40 transition-colors [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                  />
                </div>
              )}

              <button
                onClick={handleSubmit}
                disabled={isMCQ ? !selectedOption || submitting : !userAnswer.trim() || submitting}
                className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Submitting…
                  </>
                ) : (
                  "Submit Answer →"
                )}
              </button>
            </>
          ) : (
            /* Retry prompt — shown after first wrong attempt */
            <div className="space-y-3">
              <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-900/30 border border-red-700/50 text-red-300 font-semibold text-sm">
                <span className="text-base">✗</span>
                <span>Incorrect — one more try!</span>
              </div>
              <button
                onClick={() => { setLocalIncorrect(false); setSelectedOption(""); setUserAnswer(""); }}
                className="w-full py-2.5 rounded-xl border border-gray-600 hover:border-gray-400 text-gray-300 text-sm font-medium transition-colors"
              >
                Try again →
              </button>
            </div>
          )}
        </>
      ) : result ? (
        /* ── Result panel ── */
        <div className="space-y-4">
          <div className={`flex items-center gap-2 px-4 py-3 rounded-xl font-semibold text-sm border ${
            result.is_correct
              ? "bg-emerald-900/40 border-emerald-700/60 text-emerald-300"
              : "bg-red-900/40 border-red-700/60 text-red-300"
          }`}>
            <span className="text-lg">{result.is_correct ? "✓" : "✗"}</span>
            {result.is_correct ? "Correct!" : "Incorrect"}
            {result.skill_delta !== 0 && (
              <span className={`ml-auto font-mono font-bold ${result.is_correct && result.skill_delta > 0 ? "text-emerald-400" : "text-red-400"}`}>
                {result.is_correct && result.skill_delta > 0 ? "+" : "−"}{Math.abs(result.skill_delta)} ELO
              </span>
            )}
          </div>

          <div className="bg-gray-800/40 rounded-xl p-3 border border-gray-700/50 space-y-1">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Your answer</p>
            <p className="text-gray-300 text-sm">{isMCQ ? selectedOption : userAnswer}</p>
          </div>

          {result.correct_answer && (
            <div className="bg-gray-800/40 rounded-xl p-3 border border-emerald-800/40 space-y-1">
              <p className="text-xs text-emerald-500 font-medium uppercase tracking-wide">Correct answer</p>
              <div className="text-gray-100 text-sm leading-relaxed">
                <MathText text={result.correct_answer} />
              </div>
            </div>
          )}

          {result.explanation && (
            <div className="bg-gray-800/40 rounded-xl p-3 border border-brand-800/40 space-y-1">
              <p className="text-xs text-brand-400 font-medium uppercase tracking-wide">Explanation</p>
              <div className="text-gray-200 text-sm leading-relaxed">
                <MathText text={result.explanation} />
              </div>
            </div>
          )}

          {result.remediation && (
            <div className="bg-amber-950/30 rounded-xl p-3 border border-amber-800/40 space-y-2">
              <p className="text-xs text-amber-400 font-medium uppercase tracking-wide">
                📚 Lesson to review
                {result.remediation.weak_prereq && (
                  <span className="ml-2 normal-case text-amber-500/70 font-normal">
                    — {result.remediation.weak_prereq.replace(/_/g, " ")}
                  </span>
                )}
              </p>
              <div className="text-gray-200 text-sm leading-relaxed">
                <MathText text={result.remediation.lesson} />
              </div>
              {result.remediation.guided_questions?.length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-amber-500/70 font-medium">Practice these:</p>
                  {result.remediation.guided_questions.map((q, i) => (
                    <div key={i} className="text-xs text-gray-400 bg-gray-800/60 rounded-lg px-3 py-2">
                      <MathText text={q.text} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-gray-500 px-1">
            <span>CMS: <span className="text-gray-300 font-mono">{(result.cms * 100).toFixed(0)}%</span></span>
            <span>{result.message}</span>
          </div>

          <button
            onClick={() => onResult(result)}
            className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-sm transition-colors"
          >
            Next Question →
          </button>
        </div>
      ) : null}
    </div>
  );
}
