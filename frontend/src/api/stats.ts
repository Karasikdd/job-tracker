import { apiRequest } from "./client";

import type { ApplicationStats } from "../types/api";

export function getStats(
  token: string,
  signal?: AbortSignal,
): Promise<ApplicationStats> {
  return apiRequest<ApplicationStats>("/stats", {
    token,
    signal,
  });
}