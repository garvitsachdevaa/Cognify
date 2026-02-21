// ─── API client ────────────────────────────────────────────────────────────
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ─── Auth ──────────────────────────────────────────────────────────────────
export interface User {
  user_id: number;
  name: string;
  email: string;
}

export function register(name: string, email: string, password: string) {
  return request<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export function login(email: string, password: string) {
  return request<User>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// ─── Practice ─────────────────────────────────────────────────────────────
export interface Question {
  id: number;
  text: string;
  difficulty: number;
  subtopics: string[];
}

export interface PracticeStartResponse {
  questions: Question[];
  skill: number;
  concept: string;
}

export function startPractice(user_id: number, topic: string, n = 5) {
  return request<PracticeStartResponse>("/practice/start", {
    method: "POST",
    body: JSON.stringify({ user_id, topic, n }),
  });
}

export interface RemediationData {
  weak_prereq: string | null;
  target_concept: string;
  lesson: string;
  guided_questions: Array<{ text: string; difficulty: number }>;
}

export interface AnswerResponse {
  cms: number;
  old_skill: number;
  new_skill: number;
  skill_delta: number;
  remediation: RemediationData | null;
  message: string;
  is_correct: boolean;
  correct_answer: string;
  explanation: string;
}

export function submitAnswer(
  user_id: number,
  question_id: number,
  user_answer: string,
  time_taken: number,
  retries = 0,
  hint_used = false,
  confidence = 3
) {
  return request<AnswerResponse>("/practice/answer", {
    method: "POST",
    body: JSON.stringify({
      user_id,
      question_id,
      user_answer,
      time_taken,
      retries,
      hint_used,
      confidence,
    }),
  });
}

// ─── Doubt ────────────────────────────────────────────────────────────────
export interface DoubtResponse {
  steps: string[];
  final_answer: string;
  sympy_verified: boolean;
  sympy_error: string | null;
  model_used?: string;  // "aryabhata-1.0" or "gemini"
}

export function solveDoubt(
  user_id: number,
  question_text: string,
  image_base64?: string,
  image_mime_type?: string,
) {
  return request<DoubtResponse>("/doubt/solve", {
    method: "POST",
    body: JSON.stringify({
      user_id,
      question_text,
      ...(image_base64 ? { image_base64, image_mime_type: image_mime_type ?? "image/jpeg" } : {}),
    }),
  });
}

// ─── Hint ────────────────────────────────────────────────────────────────
export function getHint(question_id: number) {
  return request<{ hint: string }>(`/practice/hint/${question_id}`);
}

// ─── Dashboard ────────────────────────────────────────────────────────────
export interface SkillEntry {
  concept: string;
  display_name: string;
  skill: number;
  topic: string;   // backend field name
  category?: string; // alias – same as topic
}

export interface AttemptEntry {
  id: number;
  concept: string;       // derived from first subtopic
  text: string;          // question text
  is_correct: boolean;
  time_taken: number;
  cms: number;
  created_at: string;
}

export interface DashboardResponse {
  readiness_score: number;
  skill_vector: SkillEntry[];
  recent_attempts: AttemptEntry[];
}

export function getDashboard(user_id: number) {
  return request<DashboardResponse>(`/dashboard/${user_id}`);
}
