import { User } from "./api";

const KEY = "cognify_user";

export function saveUser(user: User) {
  if (typeof window !== "undefined") {
    localStorage.setItem(KEY, JSON.stringify(user));
  }
}

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function clearUser() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(KEY);
  }
}
