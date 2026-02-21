"use client";
import { useState, useRef, useCallback, useEffect } from "react";
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

  // Image state
  const [imagePreview, setImagePreview] = useState<string | null>(null);   // data URL for <img>
  const [imageBase64, setImageBase64] = useState<string | null>(null);     // pure base64
  const [imageMime, setImageMime] = useState<string>("image/jpeg");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadImageFile = useCallback((file: File) => {
    const mime = file.type || "image/jpeg";
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      setImagePreview(dataUrl);
      // Strip data:<mime>;base64, prefix to get raw base64
      const b64 = dataUrl.split(",")[1];
      setImageBase64(b64);
      setImageMime(mime);
    };
    reader.readAsDataURL(file);
  }, []);

  // Global paste listener — catches Ctrl+V / Cmd+V anywhere on the page
  useEffect(() => {
    function onPaste(e: ClipboardEvent) {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) { loadImageFile(file); e.preventDefault(); }
          break;
        }
      }
    }
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, [loadImageFile]);

  const clearImage = () => {
    setImagePreview(null);
    setImageBase64(null);
    setImageMime("image/jpeg");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const canSubmit = !loading && (!!question.trim() || !!imageBase64);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await solveDoubt(
        userId,
        question.trim(),
        imageBase64 ?? undefined,
        imageMime,
      );
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

        {/* Image upload area */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-medium text-gray-400">
              Question image <span className="text-gray-600">(optional — paste or upload)</span>
            </label>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
            >
              + Upload image
            </button>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) loadImageFile(file);
            }}
          />
          {imagePreview ? (
            <div className="relative rounded-xl overflow-hidden border border-gray-700/60 bg-gray-900">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imagePreview}
                alt="Question screenshot"
                className="w-full max-h-64 object-contain p-2"
              />
              <button
                type="button"
                onClick={clearImage}
                className="absolute top-2 right-2 w-6 h-6 rounded-full bg-gray-900/80 border border-gray-700 text-gray-400 hover:text-white flex items-center justify-center text-xs leading-none"
                title="Remove image"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full h-24 rounded-xl border border-dashed border-gray-700 hover:border-brand-600 bg-gray-900/40 text-gray-500 hover:text-gray-400 text-sm transition-colors flex flex-col items-center justify-center gap-1"
            >
              <span className="text-2xl">📷</span>
              <span>Click to upload or paste a screenshot (Ctrl+V / ⌘V)</span>
            </button>
          )}
        </div>

        {/* Text question */}
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1.5">
            {imageBase64 ? "Add context (optional)" : "Or type your question"}
          </label>
          <textarea
            className="input resize-none h-24"
            placeholder={
              imageBase64
                ? "e.g. I'm stuck on part (b) specifically…"
                : "e.g. Find ∫ x·eˣ dx using integration by parts"
            }
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </div>

        <button
          type="submit"
          className="btn-primary w-full"
          disabled={!canSubmit}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              {imageBase64 ? "Reading image & solving…" : "Solving…"}
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
