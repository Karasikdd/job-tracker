export type ApiRequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  token?: string | null;
  signal?: AbortSignal;
  headers?: HeadersInit;
};

export class ApiError extends Error {
  readonly status: number;
  readonly data: unknown;

  constructor(status: number, message: string, data: unknown = null) {
    super(message);

    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

type FastApiValidationError = {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
};

type FastApiErrorResponse = {
  detail?: string | FastApiValidationError[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function getErrorMessage(
  status: number,
  data: unknown,
  fallback: string,
): string {
  if (status >= 500) {
    return "The server encountered an error. Please try again later.";
  }

  if (!isRecord(data)) {
    return fallback;
  }

  const response = data as FastApiErrorResponse;

  if (typeof response.detail === "string") {
    return response.detail;
  }

  if (Array.isArray(response.detail)) {
    const messages = response.detail
      .map((error) => {
        if (!isRecord(error) || typeof error.msg !== "string") {
          return null;
        }

        const location = Array.isArray(error.loc)
          ? error.loc
              .filter((part) => part !== "body")
              .map(String)
              .join(".")
          : "";

        return location.length > 0
          ? `${location}: ${error.msg}`
          : error.msg;
      })
      .filter((message): message is string => message !== null);

    if (messages.length > 0) {
      return messages.join("; ");
    }
  }

  return fallback;
}

async function readResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  try {
    const text = await response.text();
    return text.length > 0 ? text : null;
  } catch {
    return null;
  }
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  if (!path.startsWith("/")) {
    throw new Error(`API path must start with "/": ${path}`);
  }

  const {
    method = "GET",
    body,
    token,
    signal,
    headers: additionalHeaders,
  } = options;

  const headers = new Headers(additionalHeaders);

  headers.set("Accept", "application/json");

  if (body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const requestInit: RequestInit = {
    method,
    headers,
  };

  if (body !== undefined) {
    requestInit.body = JSON.stringify(body);
  }

  if (signal !== undefined) {
    requestInit.signal = signal;
  }

  let response: Response;

  try {
    response = await fetch(`/api${path}`, requestInit);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }

    throw new ApiError(
      0,
      "Could not connect to the server. Check your connection and try again.",
    );
  }

  const data = await readResponseBody(response);

  if (!response.ok) {
    const fallback = `Request failed with status ${response.status}`;

    throw new ApiError(
      response.status,
      getErrorMessage(response.status, data, fallback),
      data,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return data as T;
}