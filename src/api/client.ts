/**
 * ClaimBridge FastAPI Client
 * Connects the frontend to the existing FastAPI backend.
 */

const API_BASE_URL =
  import.meta.env["VITE_API_BASE_URL"] || "http://localhost:8001";

export interface ApiResponse<T = any> {
  data: T | null;
  error?: string;
  status: number;
}

export async function apiFetch<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token =
    typeof window !== "undefined"
      ? window.localStorage.getItem("claimbridge_auth_token")
      : null;

  const isFormData =
    typeof FormData !== "undefined" &&
    options.body instanceof FormData;

  const headers: HeadersInit = {
    Accept: "application/json",
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const config: RequestInit = {
    ...options,
    headers,
  };

  try {
    const url = endpoint.startsWith("http")
      ? endpoint
      : `${API_BASE_URL}${endpoint}`;

    const response = await fetch(url, config);

    let data: any = null;

    const contentType = response.headers.get("content-type");

    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errorMessage =
        (typeof data === "object" && data?.detail) ||
        (typeof data === "object" && data?.message) ||
        `HTTP Error ${response.status}`;

      return {
        data: null,
        error: errorMessage,
        status: response.status,
      };
    }

    return {
      data,
      status: response.status,
    };
  } catch (error: any) {
    console.warn(
      `[ClaimBridge API] Request to ${endpoint} failed:`,
      error?.message
    );

    return {
      data: null,
      error:
        error?.message ||
        "Network request failed. Please ensure the ClaimBridge backend is running.",
      status: 0,
    };
  }
}