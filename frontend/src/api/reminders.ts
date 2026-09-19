import { apiRequest } from "./client";

import type {
  Reminder,
  ReminderCreate,
  ReminderPatch,
} from "../types/notifications";

export function listApplicationReminders(
  token: string,
  applicationId: number,
  offset = 0,
  signal?: AbortSignal,
): Promise<Reminder[]> {
  return apiRequest<Reminder[]>(
    `/applications/${applicationId}/reminders?limit=20&offset=${offset}`,
    { token, signal },
  );
}

export function createReminder(
  token: string,
  applicationId: number,
  payload: ReminderCreate,
  signal?: AbortSignal,
): Promise<Reminder> {
  return apiRequest<Reminder>(
    `/applications/${applicationId}/reminders`,
    {
      method: "POST",
      token,
      body: payload,
      signal,
    },
  );
}

export function updateReminder(
  token: string,
  reminderId: number,
  payload: ReminderPatch,
  signal?: AbortSignal,
): Promise<Reminder> {
  return apiRequest<Reminder>(`/reminders/${reminderId}`, {
    method: "PATCH",
    token,
    body: payload,
    signal,
  });
}

export function cancelReminder(
  token: string,
  reminderId: number,
  signal?: AbortSignal,
): Promise<Reminder> {
  return apiRequest<Reminder>(`/reminders/${reminderId}/cancel`, {
    method: "POST",
    token,
    signal,
  });
}