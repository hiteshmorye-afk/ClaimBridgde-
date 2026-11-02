/**
 * ClaimBridge FastAPI Client
 * Connects the frontend to the existing FastAPI backend.
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export interface ApiResponse<T = any> {
  data: T | null;
  error?: string;
  status: number;
  retryAfter?: number;
}

function buildApiUrl(endpoint: string): string {
  if (!endpoint) {
    return API_BASE_URL;
  }

  if (/^https?:\/\//i.test(endpoint)) {
    return endpoint;
  }

  const normalized = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${normalized}`;
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
    credentials: options.credentials ?? "include",
    headers,
  };

  try {
    const url = buildApiUrl(endpoint);
    const response = await fetch(url, config);

    let data: any = null;

    const contentType = response.headers.get("content-type");

    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const retryAfterHeader = response.headers.get("retry-after");
      const retryAfter = retryAfterHeader ? Number(retryAfterHeader) : undefined;
      const rawError =
        (typeof data === "object" && data?.detail) ||
        (typeof data === "object" && data?.message) ||
        `HTTP Error ${response.status}`;
      const errorMessage =
        response.status === 429 && typeof retryAfter === "number" && Number.isFinite(retryAfter)
          ? `Too many verification requests. Please wait ${retryAfter} seconds before trying again.`
          : rawError;

      return {
        data: null,
        error: errorMessage,
        status: response.status,
        retryAfter,
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
        "Network request failed. Please ensure the ClaimBridge backend is running at http://127.0.0.1:8000.",
      status: 0,
    };
  }
}
