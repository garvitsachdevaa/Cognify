"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getUser } from "@/lib/auth";
import DoubtChat from "@/components/DoubtChat";

export default function DoubtPage() {
  const router = useRouter();
  const [userId, setUserId] = useState<number | null>(null);

  useEffect(() => {
    const user = getUser();
    if (!user) { router.push("/login"); return; }
    setUserId(user.user_id);
  }, [router]);

  if (!userId) return null;

  return (
    <div className="min-h-screen p-4 max-w-2xl mx-auto">
      {/* Nav */}
      <div className="flex items-center justify-between mb-6">
        <Link href="/dashboard" className="text-gray-500 hover:text-gray-300 text-sm">
          ← Dashboard
        </Link>
        <h1 className="text-xl font-bold">Doubt Solver</h1>
        <div className="w-20" />
      </div>

      <div className="card">
        <p className="text-gray-500 text-sm mb-5">
          Describe any JEE Maths problem and get a step-by-step AI solution.
        </p>
        <DoubtChat userId={userId} />
      </div>
    </div>
  );
}
