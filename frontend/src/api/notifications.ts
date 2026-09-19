import { apiRequest } from "./client";

import type { NotificationSettings } from "../types/notifications";

export function getNotificationSettings(
  token: string,
  signal?: AbortSignal,
): Promise<NotificationSettings> {
  return apiRequest<NotificationSettings>(
    "/users/me/notification-settings",
    { token, signal },
  );
}

export function updateNotificationSettings(
  token: string,
  emailEnabled: boolean,
  signal?: AbortSignal,
): Promise<NotificationSettings> {
  return apiRequest<NotificationSettings>(
    "/users/me/notification-settings",
    {
      method: "PATCH",
      token,
      body: { email_enabled: emailEnabled },
      signal,
    },
  );
}