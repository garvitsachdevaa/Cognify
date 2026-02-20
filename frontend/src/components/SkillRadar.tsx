"use client";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { SkillEntry } from "@/lib/api";

interface Props {
  skills: SkillEntry[];
}

export default function SkillRadar({ skills }: Props) {
  // Aggregate by topic — average skill per topic
  const byCategory: Record<string, number[]> = {};
  for (const s of skills) {
    const key = s.topic || s.category || "General";
    if (!byCategory[key]) byCategory[key] = [];
    byCategory[key].push(s.skill);
  }

  const data = Object.entries(byCategory).map(([name, vals]) => ({
    subject: name,
    skill: Math.round(vals.reduce((a, b) => a + b, 0) / vals.length),
    fullMark: 1200,
  }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-600 text-sm">
        No skill data yet — start practising!
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data}>
        <PolarGrid stroke="#374151" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
          labelStyle={{ color: "#e5e7eb" }}
          formatter={(val: number) => [`${val}`, "Skill"]}
        />
        <Radar
          name="Skill"
          dataKey="skill"
          stroke="#6366f1"
          fill="#6366f1"
          fillOpacity={0.25}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
