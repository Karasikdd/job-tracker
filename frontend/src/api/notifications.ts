import { apiRequest } from "./client";

import type {
  Notification,
  NotificationSettings,
  UnreadCount,
} from "../types/notifications";

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

export function listNotifications(
  token: string,
  unreadOnly: boolean,
  offset: number,
  signal?: AbortSignal,
): Promise<Notification[]> {
  const parameters = new URLSearchParams({
    limit: "20",
    offset: String(offset),
  });

  if (unreadOnly) {
    parameters.set("unread", "true");
  }

  return apiRequest<Notification[]>(
    `/notifications?${parameters.toString()}`,
    { token, signal },
  );
}

export function getUnreadCount(
  token: string,
  signal?: AbortSignal,
): Promise<UnreadCount> {
  return apiRequest<UnreadCount>(
    "/notifications/unread-count",
    { token, signal },
  );
}

export function markNotificationRead(
  token: string,
  notificationId: number,
  signal?: AbortSignal,
): Promise<Notification> {
  return apiRequest<Notification>(
    `/notifications/${notificationId}/read`,
    {
      method: "PATCH",
      token,
      signal,
    },
  );
}