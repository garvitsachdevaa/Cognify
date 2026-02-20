"use client";
import { useState } from "react";
import { solveDoubt, DoubtResponse } from "@/lib/api";
import MathText from "@/components/MathText";

interface Props {
  userId: number;
}

export default function DoubtChat({ userId }: Props) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<DoubtResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await solveDoubt(userId, question.trim());
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to solve doubt");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      {/* Input form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">
            Enter your question
          </label>
          <textarea
            className="input resize-none h-28"
            placeholder="e.g. Find ∫ x·eˣ dx using integration by parts"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
          />
        </div>
        <button
          type="submit"
          className="btn-primary w-full"
          disabled={loading || !question.trim()}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Solving…
            </span>
          ) : (
            "Solve with AI ✦"
          )}
        </button>
      </form>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-900/40 border border-red-700 text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">
          {/* Steps */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-200">Step-by-step solution</h3>
              <div className="flex items-center gap-1.5">
                {result.model_used === "aryabhata-1.0" ? (
                  <span className="badge bg-orange-900/60 text-orange-300 border border-orange-700/50 text-xs">
                    ⚡ Aryabhata 1.0
                  </span>
                ) : (
                  <span className="badge bg-blue-900/60 text-blue-300 border border-blue-700/50 text-xs">
                    ✦ Gemini
                  </span>
                )}
                {result.sympy_verified ? (
                  <span className="badge bg-emerald-900/60 text-emerald-300 border border-emerald-700/50">
                    ✓ Verified
                  </span>
                ) : (
                  <span className="badge bg-gray-800 text-gray-500">Unverified</span>
                )}
              </div>
            </div>

            <ol className="space-y-3">
              {result.steps.map((step, i) => (
                <li key={i} className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-brand-900/60 border border-brand-700/50 text-brand-400 text-xs font-bold flex items-center justify-center mt-0.5">
                    {i + 1}
                  </span>
                  <p className="text-gray-300 text-sm leading-relaxed">
                    <MathText text={step} />
                  </p>
                </li>
              ))}
            </ol>

            {/* Final answer */}
            <div className="border-t border-gray-800 pt-3 mt-2">
              <p className="text-xs text-gray-500 mb-1">Final Answer</p>
              <p className="text-brand-300 font-semibold text-lg">
                <MathText text={result.final_answer} />
              </p>
            </div>
          </div>

          {/* Ask another */}
          <button
            onClick={() => { setResult(null); setQuestion(""); }}
            className="btn-ghost w-full"
          >
            Ask another question
          </button>
        </div>
      )}
    </div>
  );
}
