"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { TOPICS, CATEGORIES, topicsByCategory } from "@/lib/topics";

const CATEGORY_ICONS: Record<string, string> = {
  "Sets & Functions": "𝒇",
  "Algebra": "𝑥²",
  "Matrices": "[ ]",
  "Trigonometry": "sin",
  "Coordinate Geometry": "📐",
  "Calculus": "∫",
  "Vectors & 3D": "→",
};

const CATEGORY_COLORS: Record<string, string> = {
  "Sets & Functions": "from-violet-900/50 to-violet-800/20 border-violet-700/50",
  "Algebra": "from-blue-900/50 to-blue-800/20 border-blue-700/50",
  "Matrices": "from-cyan-900/50 to-cyan-800/20 border-cyan-700/50",
  "Trigonometry": "from-emerald-900/50 to-emerald-800/20 border-emerald-700/50",
  "Coordinate Geometry": "from-yellow-900/50 to-yellow-800/20 border-yellow-700/50",
  "Calculus": "from-rose-900/50 to-rose-800/20 border-rose-700/50",
  "Vectors & 3D": "from-orange-900/50 to-orange-800/20 border-orange-700/50",
};

export default function TopicSelector() {
  const router = useRouter();
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  function selectTopic(id: string) {
    router.push(`/practice/${id}`);
  }

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4 text-gray-200">Choose a Topic</h2>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {CATEGORIES.map((cat) => {
          const topics = topicsByCategory(cat);
          const isActive = activeCategory === cat;
          return (
            <div key={cat} className="col-span-1">
              {/* Category header */}
              <button
                onClick={() => setActiveCategory(isActive ? null : cat)}
                className={`w-full text-left p-4 rounded-xl border bg-gradient-to-br transition-all hover:scale-[1.02] active:scale-[0.98] ${
                  CATEGORY_COLORS[cat] ?? "from-gray-800/50 to-gray-700/20 border-gray-700/50"
                } ${isActive ? "ring-2 ring-brand-500" : ""}`}
              >
                <div className="text-2xl mb-1">{CATEGORY_ICONS[cat] ?? "📚"}</div>
                <div className="font-semibold text-sm text-gray-100">{cat}</div>
                <div className="text-xs text-gray-400 mt-0.5">{topics.length} topics</div>
              </button>

              {/* Topic list (expands below the card) */}
              {isActive && (
                <div className="mt-2 space-y-1 col-span-full">
                  {topics.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => selectTopic(t.id)}
                      className="w-full text-left px-4 py-2.5 rounded-lg bg-gray-800 hover:bg-gray-700 hover:text-brand-300 text-gray-300 text-sm transition-colors flex items-center justify-between group"
                    >
                      <span>{t.label}</span>
                      <span className="text-gray-600 group-hover:text-brand-400 text-xs">→</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
