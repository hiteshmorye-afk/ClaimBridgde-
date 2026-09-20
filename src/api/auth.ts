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
  const response = await apiFetch<UserProfile>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });

  if (response.data?.token && typeof window !== "undefined") {
    window.localStorage.setItem(
      "claimbridge_auth_token",
      response.data.token,
    );
  }

  // Fallback mock session for smooth frontend operation
  const identifier = credentials.email || "23102030";
  const isEmail = identifier.includes("@");
  const userName = isEmail ? identifier.split("@")[0] : identifier;
  const userEmail = isEmail
    ? identifier
    : `${identifier}@apsit.edu.in`;

  const user: UserProfile = response.data || {
    id: identifier,
    email: userEmail,
    name: userName,
    role: credentials.portal === "TPA" ? "Admin" : "Coordinator",
    portal: credentials.portal || "Hospital",
    hospital:
      credentials.portal === "Hospital"
        ? "Chong Hua Hospital"
        : "Pacific TPA Gateway",
    token: "jwt_mock_token_claimbridge_2026",
  };

  if (typeof window !== "undefined") {
    window.localStorage.setItem(
      "claimbridge_user",
      JSON.stringify(user),
    );
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