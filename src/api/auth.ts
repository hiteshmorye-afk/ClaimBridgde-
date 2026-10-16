import { apiFetch } from "./client";

export type AppRole = "claimant" | "claims_officer";
export type AppPortal = "Claimant" | "TPA";

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  phone: string;
  role: AppRole;
  portal: AppPortal;
  organization: string;
  token: string;
}

interface AuthResponse {
  message: string;
  user_id: string;
  full_name: string;
  email: string;
  phone?: string;
  role: AppRole;
  portal: AppPortal;
  organization: string;
  token: string;
}

export interface OtpRegistrationResult {
  message: string;
  user_id: string;
  email: string;
  challenge_id: string;
  verification_required: true;
  organization_authorization_required?: boolean;
}

function storeUser(response: AuthResponse): UserProfile {
  if (
    !response.user_id ||
    !response.token ||
    !["claimant", "claims_officer"].includes(response.role) ||
    !["Claimant", "TPA"].includes(response.portal)
  ) {
    throw new Error("The backend returned an invalid active user profile.");
  }

  const user: UserProfile = {
    id: response.user_id,
    email: response.email,
    name: response.full_name,
    phone: response.phone || "",
    role: response.role,
    portal: response.portal,
    organization: response.organization || "",
    token: response.token,
  };

  if (typeof window !== "undefined") {
    window.localStorage.setItem("claimbridge_user", JSON.stringify(user));
    window.localStorage.setItem("claimbridge_auth_token", user.token);
  }
  return user;
}

export async function loginUser(credentials: {
  email: string;
  password: string;
}): Promise<UserProfile> {
  const response = await apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email: credentials.email.trim(),
      password: credentials.password,
    }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Invalid email or password.");
  }
  return storeUser(response.data);
}

export async function registerUser(data: {
  fullName: string;
  phone: string;
  email: string;
  password: string;
}): Promise<OtpRegistrationResult> {
  const response = await apiFetch<OtpRegistrationResult>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      full_name: data.fullName.trim(),
      phone: data.phone.trim(),
      email: data.email.trim(),
      password: data.password,
    }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Registration failed.");
  }
  return response.data;
}

export async function registerTpaApplicant(data: {
  fullName: string;
  phone: string;
  email: string;
  password: string;
  organization: string;
}): Promise<OtpRegistrationResult> {
  const response = await apiFetch<OtpRegistrationResult>("/auth/register/tpa", {
    method: "POST",
    body: JSON.stringify({
      full_name: data.fullName.trim(),
      phone: data.phone.trim(),
      email: data.email.trim(),
      password: data.password,
      organization: data.organization.trim(),
    }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "TPA application failed.");
  }
  return response.data;
}

export async function verifyEmailOtp(
  challengeId: string,
  code: string,
): Promise<UserProfile | null> {
  const response = await apiFetch<AuthResponse & {
    verified: boolean;
    activated: boolean;
  }>("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ challenge_id: challengeId, code }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Email verification failed.");
  }
  if (!response.data.activated) {
    return null;
  }
  return storeUser(response.data);
}

export async function resendEmailOtp(email: string): Promise<void> {
  const response = await apiFetch<{ message: string }>("/auth/otp/resend", {
    method: "POST",
    body: JSON.stringify({ email: email.trim() }),
  });
  if (response.error) {
    throw new Error(response.error);
  }
}

export function getCurrentUser(): UserProfile | null {
  if (typeof window === "undefined") {
    return null;
  }

  const stored = window.localStorage.getItem("claimbridge_user");
  const token = window.localStorage.getItem("claimbridge_auth_token");
  if (!stored || !token || token.split(".").length !== 3) {
    return null;
  }

  try {
    const user = JSON.parse(stored) as UserProfile;
    if (!["claimant", "claims_officer"].includes(user.role)) {
      logoutUser();
      return null;
    }
    return { ...user, token };
  } catch {
    logoutUser();
    return null;
  }
}

export function logoutUser() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem("claimbridge_auth_token");
  window.localStorage.removeItem("claimbridge_user");
}
