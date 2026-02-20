"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getDashboard, DashboardResponse, SkillEntry } from "@/lib/api";
import { getUser, clearUser } from "@/lib/auth";
import SkillRadar from "@/components/SkillRadar";
import TopicSelector from "@/components/TopicSelector";

function skillColor(skill: number) {
  if (skill >= 1100) return "bg-emerald-900/50 border-emerald-700/60 text-emerald-300";
  if (skill >= 1000) return "bg-yellow-900/40 border-yellow-700/50 text-yellow-300";
  return "bg-red-900/40 border-red-700/50 text-red-300";
}

function skillLabel(skill: number) {
  if (skill >= 1100) return "Strong";
  if (skill >= 1000) return "Average";
  return "Weak";
}

function ReadinessRing({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const r = 40;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const color = pct >= 70 ? "#10b981" : pct >= 40 ? "#f59e0b" : "#ef4444";
  return (
    <div className="relative w-28 h-28 flex items-center justify-center">
      <svg className="absolute" width="112" height="112" viewBox="0 0 112 112">
        <circle cx="56" cy="56" r={r} stroke="#1f2937" strokeWidth="10" fill="none" />
        <circle
          cx="56" cy="56" r={r}
          stroke={color}
          strokeWidth="10"
          fill="none"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 56 56)"
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
      </svg>
      <div className="text-center">
        <div className="text-2xl font-extrabold" style={{ color }}>{pct}%</div>
        <div className="text-xs text-gray-500">Readiness</div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showTopics, setShowTopics] = useState(false);
  const [userName, setUserName] = useState("");
  const [userId, setUserId] = useState<number | null>(null);

  useEffect(() => {
    const user = getUser();
    if (!user) { router.push("/login"); return; }
    setUserName(user.name);
    setUserId(user.user_id);

    getDashboard(user.user_id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [router]);

  function logout() {
    clearUser();
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // ── Skeleton on error (new user, no data) ──
  const readiness = data?.readiness_score ?? 0.5;
  const skills: SkillEntry[] = data?.skill_vector ?? [];
  const attempts = data?.recent_attempts ?? [];

  const weakTopics = skills.filter((s) => s.skill < 1000);
  const strongTopics = skills.filter((s) => s.skill >= 1100);

  return (
    <div className="min-h-screen">
      {/* Top nav */}
      <nav className="border-b border-gray-800 px-4 py-3 flex items-center justify-between bg-gray-900/80 backdrop-blur sticky top-0 z-10">
        <span className="text-xl font-extrabold text-brand-500">Cognify</span>
        <div className="flex items-center gap-3">
          <Link href="/doubt" className="btn-ghost text-xs px-3 py-1.5">
            Ask Doubt
          </Link>
          <span className="text-sm text-gray-400">{userName}</span>
          <button onClick={logout} className="text-xs text-gray-600 hover:text-red-400 transition-colors">
            Logout
          </button>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto p-4 space-y-6">
        {error && (
          <div className="px-4 py-3 rounded-lg bg-amber-900/40 border border-amber-700 text-amber-300 text-sm">
            {error} — showing default view.
          </div>
        )}

        {/* ── Hero row ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Readiness */}
          <div className="card flex flex-col items-center justify-center gap-2">
            <ReadinessRing score={readiness} />
            <p className="text-xs text-gray-500 text-center">Average CMS across all practice</p>
          </div>

          {/* Stats */}
          <div className="card sm:col-span-2 grid grid-cols-2 gap-4">
            <StatItem
              label="Topics practised"
              value={skills.length > 0 ? skills.length.toString() : "—"}
            />
            <StatItem
              label="Attempts"
              value={attempts.length > 0 ? attempts.length.toString() : "—"}
            />
            <StatItem
              label="Weak topics"
              value={weakTopics.length.toString()}
              color="text-red-400"
            />
            <StatItem
              label="Strong topics"
              value={strongTopics.length.toString()}
              color="text-emerald-400"
            />
          </div>
        </div>

        {/* ── Skill Radar ── */}
        {skills.length > 0 && (
          <div className="card">
            <h2 className="text-sm font-semibold text-gray-400 mb-4">Skill Radar</h2>
            <SkillRadar skills={skills} />
          </div>
        )}

        {/* ── Start Practice ── */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-200">Practice a Topic</h2>
            <button
              onClick={() => setShowTopics(!showTopics)}
              className="text-xs text-brand-400 hover:text-brand-300"
            >
              {showTopics ? "Hide" : "Browse all →"}
            </button>
          </div>

          {/* Quick-access: weak topics first, then first 6 topics */}
          {!showTopics && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {(weakTopics.length > 0
                ? weakTopics.slice(0, 6).map((s) => ({
                    id: s.concept,
                    label: s.concept.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
                    isWeak: true,
                  }))
                : [
                    { id: "integration_by_parts", label: "Integration by Parts", isWeak: false },
                    { id: "limits", label: "Limits", isWeak: false },
                    { id: "quadratic_equations", label: "Quadratic Equations", isWeak: false },
                    { id: "basic_probability", label: "Probability", isWeak: false },
                    { id: "complex_numbers_basics", label: "Complex Numbers", isWeak: false },
                    { id: "differentiation_basics", label: "Differentiation", isWeak: false },
                  ]
              ).map((t) => (
                <Link
                  key={t.id}
                  href={`/practice/${t.id}`}
                  className={`px-3 py-2.5 rounded-lg border text-sm font-medium text-center transition-colors ${
                    t.isWeak
                      ? "bg-red-900/30 border-red-700/50 text-red-300 hover:bg-red-800/40"
                      : "bg-gray-800 border-gray-700 text-gray-300 hover:border-brand-600 hover:text-brand-300"
                  }`}
                >
                  {t.isWeak && <span className="text-xs mr-1">⚠</span>}
                  {t.label}
                </Link>
              ))}
            </div>
          )}

          {showTopics && <TopicSelector />}
        </div>

        {/* ── Skill Vector ── */}
        {skills.length > 0 && (
          <div className="card">
            <h2 className="font-semibold text-gray-200 mb-4">All Practised Topics</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              {skills.map((s) => (
                <Link
                  key={s.concept}
                  href={`/practice/${s.concept}`}
                  className={`px-3 py-2.5 rounded-lg border text-sm transition-all hover:scale-[1.02] ${skillColor(s.skill)}`}
                >
                  <div className="font-medium truncate">
                    {s.concept.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs opacity-70">{skillLabel(s.skill)}</span>
                    <span className="text-xs font-mono">{Math.round(s.skill)}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* ── Recent Attempts ── */}
        {attempts.length > 0 && (
          <div className="card">
            <h2 className="font-semibold text-gray-200 mb-4">Recent Attempts</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-xs border-b border-gray-800">
                    <th className="text-left pb-2 pr-4">Topic</th>
                    <th className="text-center pb-2 pr-4">Result</th>
                    <th className="text-center pb-2 pr-4">CMS</th>
                    <th className="text-right pb-2">When</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60">
                  {attempts.map((a, i) => (
                    <tr key={i} className="hover:bg-gray-800/30 transition-colors">
                      <td className="py-2 pr-4 text-gray-300">
                        {a.concept.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </td>
                      <td className="py-2 pr-4 text-center">
                        {a.is_correct ? (
                          <span className="text-emerald-400 font-semibold">✓</span>
                        ) : (
                          <span className="text-red-400 font-semibold">✗</span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-center text-gray-400 font-mono text-xs">
                        {(a.cms * 100).toFixed(0)}%
                      </td>
                      <td className="py-2 text-right text-gray-600 text-xs">
                        {new Date(a.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StatItem({
  label,
  value,
  color = "text-brand-400",
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div>
      <div className={`text-2xl font-extrabold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}
