export type ReminderKind = "interview" | "follow_up" | "custom";

export type ReminderStatus = "scheduled" | "fired" | "cancelled";

export type Reminder = {
  id: number;
  application_id: number;
  title: string;
  message: string | null;
  kind: ReminderKind;
  remind_at: string;
  status: ReminderStatus;
  send_email: boolean;
  created_at: string;
  fired_at: string | null;
};

export type ReminderCreate = {
  title: string;
  message: string | null;
  kind: ReminderKind;
  remind_at: string;
  send_email: boolean;
};

export type ReminderPatch = {
  title?: string;
  message?: string | null;
  remind_at?: string;
  send_email?: boolean;
};

export type Notification = {
  id: number;
  application_id: number;
  reminder_id: number;
  title: string;
  body: string;
  created_at: string;
  read_at: string | null;
};

export type NotificationSettings = {
  email_enabled: boolean;
};

export type UnreadCount = {
  count: number;
};