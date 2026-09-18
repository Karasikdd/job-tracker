import { apiRequest } from "./client";
import type { TokenResponse, User } from "../types/api";

export type Credentials = {
  email: string;
  password: string;
};

export function registerUser(
  credentials: Credentials,
  signal?: AbortSignal,
): Promise<User> {
  return apiRequest<User>("/auth/register", {
    method: "POST",
    body: credentials,
    signal,
  });
}

export function loginUser(
  credentials: Credentials,
  signal?: AbortSignal,
): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: credentials,
    signal,
  });
}

export function getCurrentUser(
  token: string,
  signal?: AbortSignal,
): Promise<User> {
  return apiRequest<User>("/users/me", {
    token,
    signal,
  });
}