/**
 * ClaimBridge FastAPI Client Architecture Layer
 * Base HTTP client configured to connect with existing FastAPI + SQLAlchemy + PostgreSQL backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export interface ApiResponse<T = any> {
  data: T | null;
  error?: string;
  status: number;
}

export async function apiFetch<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = localStorage.getItem("claimbridge_auth_token");

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const config: RequestInit = {
    ...options,
    headers,
  };

  try {
    const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, config);

    let data = null;
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
    console.warn(`[ClaimBridge API] Request to ${endpoint} using local fallback:`, error.message);
    return {
      data: null,
      error: error.message || "Network request failed. Operating in offline/mock mode.",
      status: 0,
    };
  }
}
