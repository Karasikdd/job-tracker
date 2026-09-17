import { apiRequest } from "./client";

import type {
  ApplicationCreate,
  ApplicationPatch,
  ApplicationStatus,
  JobApplication,
} from "../types/api";

export type ApplicationListParameters = {
  status?: ApplicationStatus;
  search?: string;
  limit?: number;
  offset?: number;
};

export function listApplications(
  token: string,
  parameters: ApplicationListParameters = {},
  signal?: AbortSignal,
): Promise<JobApplication[]> {
  const searchParameters = new URLSearchParams();

  if (parameters.status !== undefined) {
    searchParameters.set("status", parameters.status);
  }

  const normalizedSearch = parameters.search?.trim();

  if (normalizedSearch) {
    searchParameters.set("search", normalizedSearch);
  }

  if (parameters.limit !== undefined) {
    searchParameters.set("limit", String(parameters.limit));
  }

  if (parameters.offset !== undefined) {
    searchParameters.set("offset", String(parameters.offset));
  }

  const query = searchParameters.toString();
  const path = query.length > 0
    ? `/applications?${query}`
    : "/applications";

  return apiRequest<JobApplication[]>(path, {
    token,
    signal,
  });
}
export function getApplication(
  token: string,
  applicationId: number,
  signal?: AbortSignal,
): Promise<JobApplication> {
  return apiRequest<JobApplication>(
    `/applications/${applicationId}`,
    {
      token,
      signal,
    },
  );
}

export function createApplication(
  token: string,
  payload: ApplicationCreate,
  signal?: AbortSignal,
): Promise<JobApplication> {
  return apiRequest<JobApplication>("/applications", {
    method: "POST",
    token,
    body: payload,
    signal,
  });
}

export function updateApplication(
  token: string,
  applicationId: number,
  payload: ApplicationPatch,
  signal?: AbortSignal,
): Promise<JobApplication> {
  return apiRequest<JobApplication>(
    `/applications/${applicationId}`,
    {
      method: "PATCH",
      token,
      body: payload,
      signal,
    },
  );
}

export function deleteApplication(
  token: string,
  applicationId: number,
  signal?: AbortSignal,
): Promise<void> {
  return apiRequest<void>(
    `/applications/${applicationId}`,
    {
      method: "DELETE",
      token,
      signal,
    },
  );
}