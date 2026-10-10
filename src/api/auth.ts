import { apiFetch } from "./client";

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: "Coordinator" | "Reviewer" | "Admin";
  portal: "TPA" | "Hospital";
  hospital?: string;
  token?: string;
}

export async function loginUser(credentials: {
  email: string;
  password?: string;
  portal?: "TPA" | "Hospital";
  role?: "Coordinator" | "Reviewer" | "Admin";
}) {
  const isEmail = credentials.email.includes("@");
  const emailToSubmit = isEmail
    ? credentials.email
    : `${credentials.email}@apsit.edu.in`;

  const response = await apiFetch<{
    message: string;
    user_id: string;
    full_name: string;
    email: string;
    role: string;
  }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email: emailToSubmit,
      password: credentials.password || "Password#123",
    }),
  });

  if (response.error || !response.data?.user_id) {
    throw new Error(response.error || "Invalid email or password");
  }

  const user: UserProfile = {
    id: response.data.user_id,
    email: response.data.email,
    name: response.data.full_name,
    role: (response.data.role as any) || "Coordinator",
    portal: credentials.portal || "Hospital",
    token: `token_${response.data.user_id}`,
  };

  if (typeof window !== "undefined") {
    window.localStorage.setItem("claimbridge_user", JSON.stringify(user));
    window.localStorage.setItem("claimbridge_auth_token", user.token);
  }

  return user;
}

export async function registerUser(data: {
  fullName: string;
  email: string;
  password: string;
  role?: string;
  portal?: "TPA" | "Hospital";
}) {
  const isEmail = data.email.includes("@");
  const emailToSubmit = isEmail
    ? data.email
    : `${data.email}@apsit.edu.in`;

  const response = await apiFetch<{
    message: string;
    user_id: string;
    email: string;
    role: string;
  }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      full_name: data.fullName,
      email: emailToSubmit,
      password: data.password,
      role: data.role || (data.portal === "TPA" ? "Admin" : "Coordinator"),
    }),
  });

  if (response.error || !response.data) {
    throw new Error(response.error || "Registration failed");
  }

  const user: UserProfile = {
    id: response.data.user_id,
    email: response.data.email,
    name: data.fullName,
    role: (response.data.role as any) || "Coordinator",
    portal: data.portal || "Hospital",
    token: `token_${response.data.user_id}`,
  };

  if (typeof window !== "undefined") {
    window.localStorage.setItem("claimbridge_user", JSON.stringify(user));
    window.localStorage.setItem("claimbridge_auth_token", user.token);
  }

  return user;
}

export function getCurrentUser(): UserProfile | null {
  if (typeof window === "undefined") {
    return null;
  }

  const stored = window.localStorage.getItem(
    "claimbridge_user",
  );

  if (!stored) {
    return null;
  }

  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}

export function logoutUser() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(
    "claimbridge_auth_token",
  );

  window.localStorage.removeItem(
    "claimbridge_user",
  );
}