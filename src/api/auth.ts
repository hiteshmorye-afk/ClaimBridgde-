import { apiFetch } from "./client";

export type AppRole =
  | "admin"
  | "claim_officer"
  | "claims_officer"
  | "claimant"
  | "hospital_coordinator"
  | "tpa_reviewer"
  | "patient";

export type AppPortal = "Admin" | "Hospital" | "TPA" | "Claimant" | "Patient";

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  phone: string;
  role: AppRole;
  canonical_role?: string;
  portal: AppPortal;
  organization: string;
  designation?: string;
  employee_id?: string;
  token: string;
}

interface AuthResponse {
  message: string;
  user_id: string;
  full_name: string;
  email: string;
  phone?: string;
  role: AppRole;
  canonical_role?: string;
  portal: AppPortal;
  organization: string;
  designation?: string;
  employee_id?: string;
  token: string;
}

export interface OtpRegistrationResult {
  message: string;
  user_id: string;
  email: string;
  challenge_id: string;
  verification_required: true;
  organization_authorization_required?: boolean;
  demo_mode?: boolean;
  demo_hint?: string;
}

export interface InvitationDetails {
  valid: boolean;
  email: string;
  role: string;
  organization_name: string;
  expires_at: string;
}

export interface AdminUserRecord {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  role: string;
  portal: string;
  organization: string;
  designation?: string;
  employee_id?: string;
  account_status: string;
  is_active: boolean;
  email_verified_at?: string | null;
  last_login_at?: string | null;
  created_at?: string | null;
}

export interface OrganizationRecord {
  id: string;
  name: string;
  org_type: string;
  registration_identifier?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

function storeUser(response: AuthResponse): UserProfile {
  if (!response.user_id || !response.token) {
    throw new Error("The backend returned an invalid active user profile.");
  }

  const canonicalRole = (response.canonical_role || response.role || "").toLowerCase();
  const user: UserProfile = {
    id: response.user_id,
    email: response.email,
    name: response.full_name,
    phone: response.phone || "",
    role: (canonicalRole || response.role) as AppRole,
    canonical_role: canonicalRole,
    portal: response.portal || "Claimant",
    organization: response.organization || "",
    designation: response.designation || "",
    employee_id: response.employee_id || "",
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
  role?: string;
  hospital_name?: string;
  organization?: string;
  designation?: string;
  employee_id?: string;
  registration_identifier?: string;
  invitation_token?: string;
}): Promise<OtpRegistrationResult> {
  const response = await apiFetch<OtpRegistrationResult>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      full_name: data.fullName.trim(),
      phone: data.phone.trim(),
      email: data.email.trim(),
      password: data.password,
      role: data.role || "patient",
      hospital_name: data.hospital_name?.trim() || undefined,
      organization: data.organization?.trim() || undefined,
      designation: data.designation?.trim() || undefined,
      employee_id: data.employee_id?.trim() || undefined,
      registration_identifier: data.registration_identifier?.trim() || undefined,
      invitation_token: data.invitation_token?.trim() || undefined,
    }),
  });
  if (response.status === 429) {
    const error = new Error(response.error || "Too many verification requests. Please wait before trying again.") as Error & { retryAfter?: number; status?: number };
    error.retryAfter = response.retryAfter;
    error.status = response.status;
    throw error;
  }
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
  designation?: string;
  employee_id?: string;
}): Promise<OtpRegistrationResult> {
  const response = await apiFetch<OtpRegistrationResult>("/auth/register/tpa", {
    method: "POST",
    body: JSON.stringify({
      full_name: data.fullName.trim(),
      phone: data.phone.trim(),
      email: data.email.trim(),
      password: data.password,
      organization: data.organization.trim(),
      designation: data.designation?.trim() || undefined,
      employee_id: data.employee_id?.trim() || undefined,
    }),
  });
  if (response.status === 429) {
    const error = new Error(response.error || "Too many verification requests. Please wait before trying again.") as Error & { retryAfter?: number; status?: number };
    error.retryAfter = response.retryAfter;
    error.status = response.status;
    throw error;
  }
  if (response.error || !response.data) {
    throw new Error(response.error || "TPA application failed.");
  }
  return response.data;
}

export async function registerInvited(data: {
  invitation_token: string;
  fullName: string;
  phone: string;
  password: string;
}): Promise<UserProfile> {
  const response = await apiFetch<AuthResponse>("/auth/register/invited", {
    method: "POST",
    body: JSON.stringify({
      invitation_token: data.invitation_token.trim(),
      full_name: data.fullName.trim(),
      phone: data.phone.trim(),
      password: data.password,
    }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Onboarding failed.");
  }
  return storeUser(response.data);
}

export async function fetchInvitation(token: string): Promise<InvitationDetails> {
  const response = await apiFetch<InvitationDetails>(`/auth/invitations/${encodeURIComponent(token)}`);
  if (response.error || !response.data) {
    throw new Error(response.error || "Invalid or expired invitation token.");
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
  if (response.status === 429) {
    const error = new Error(response.error || "Too many verification requests. Please wait before trying again.") as Error & { retryAfter?: number; status?: number };
    error.retryAfter = response.retryAfter;
    error.status = response.status;
    throw error;
  }
  if (response.error) {
    throw new Error(response.error);
  }
}

export async function forgotPassword(email: string): Promise<{ message: string; challenge_id?: string }> {
  const response = await apiFetch<{ message: string; challenge_id?: string }>("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email: email.trim() }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Failed to dispatch password recovery request.");
  }
  return response.data;
}

export async function resetPassword(
  challengeId: string,
  code: string,
  newPassword: string,
): Promise<{ message: string }> {
  const response = await apiFetch<{ message: string }>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({
      challenge_id: challengeId,
      code: code.trim(),
      new_password: newPassword,
    }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Password reset failed.");
  }
  return response.data;
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ message: string }> {
  const response = await apiFetch<{ message: string }>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Password change failed.");
  }
  return response.data;
}

// Admin APIs
export async function fetchAdminUsers(filters?: {
  search?: string;
  role?: string;
  status?: string;
  organization?: string;
}): Promise<AdminUserRecord[]> {
  const params = new URLSearchParams();
  if (filters?.search) params.append("search", filters.search);
  if (filters?.role) params.append("role", filters.role);
  if (filters?.status) params.append("status_filter", filters.status);
  if (filters?.organization) params.append("organization", filters.organization);

  const query = params.toString() ? `?${params.toString()}` : "";
  const response = await apiFetch<AdminUserRecord[]>(`/auth/admin/users${query}`);
  if (response.error || !response.data) {
    throw new Error(response.error || "Failed to load user administration registry.");
  }
  return response.data;
}

export async function updateAdminUserStatus(
  userId: string,
  status: "active" | "suspended" | "deactivated",
  isActive?: boolean,
): Promise<void> {
  const response = await apiFetch(`/auth/admin/users/${encodeURIComponent(userId)}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, is_active: isActive }),
  });
  if (response.error) {
    throw new Error(response.error || "Failed to update user status.");
  }
}

export async function updateAdminUserRole(
  userId: string,
  role: string,
  organization?: string,
  designation?: string,
): Promise<void> {
  const response = await apiFetch(`/auth/admin/users/${encodeURIComponent(userId)}/role`, {
    method: "PATCH",
    body: JSON.stringify({ role, organization, designation }),
  });
  if (response.error) {
    throw new Error(response.error || "Failed to update user role.");
  }
}

export async function createAdminInvitation(data: {
  email: string;
  role: string;
  organization_name: string;
}): Promise<{ invitation_token: string; expires_at: string }> {
  const response = await apiFetch<{ invitation_token: string; expires_at: string }>("/auth/admin/invitations", {
    method: "POST",
    body: JSON.stringify({
      email: data.email.trim(),
      role: data.role,
      organization_name: data.organization_name.trim(),
    }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Failed to generate organization invitation.");
  }
  return response.data;
}

export async function fetchAdminOrganizations(orgType?: string): Promise<OrganizationRecord[]> {
  const params = orgType ? `?org_type=${encodeURIComponent(orgType)}` : "";
  const response = await apiFetch<OrganizationRecord[]>(`/auth/admin/organizations${params}`);
  if (response.error || !response.data) {
    throw new Error(response.error || "Failed to load organizations.");
  }
  return response.data;
}

export async function createAdminOrganization(data: {
  name: string;
  org_type: "hospital" | "tpa";
  registration_identifier?: string;
  contact_email?: string;
  contact_phone?: string;
}): Promise<OrganizationRecord> {
  const response = await apiFetch<OrganizationRecord>("/auth/admin/organizations", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "Failed to create organization record.");
  }
  return response.data;
}

export async function bootstrapAdmin(data: {
  fullName: string;
  email: string;
  password: string;
  phone?: string;
}): Promise<UserProfile> {
  const response = await apiFetch<AuthResponse>("/auth/admin/bootstrap", {
    method: "POST",
    body: JSON.stringify({
      full_name: data.fullName.trim(),
      email: data.email.trim(),
      password: data.password,
      phone: data.phone || "+15555550100",
    }),
  });
  if (response.error || !response.data) {
    throw new Error(response.error || "System administrator bootstrap failed.");
  }
  return storeUser(response.data);
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
    const canonicalRole = (user.canonical_role || user.role || "").toLowerCase();
    const validRoles = [
      "admin",
      "claim_officer",
      "claims_officer",
      "claimant",
      "hospital_coordinator",
      "tpa_reviewer",
      "patient",
    ];

    if (!validRoles.includes(canonicalRole)) {
      logoutUser();
      return null;
    }

    return {
      ...user,
      role: (canonicalRole || user.role) as AppRole,
      canonical_role: canonicalRole,
      portal: user.portal || "Claimant",
      token,
    };
  } catch {
    logoutUser();
    return null;
  }
}

export async function logoutUser(): Promise<void> {
  if (typeof window === "undefined") {
    return;
  }
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch {
    // Ignore network error on logout
  }
  window.localStorage.removeItem("claimbridge_auth_token");
  window.localStorage.removeItem("claimbridge_user");
}
