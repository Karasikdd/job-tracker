import { Link } from "react-router";

import type { Notification } from "../types/notifications";

type NotificationListProps = {
  items: Notification[];
  busyId: number | null;
  onMarkRead: (id: number) => void;
};

const formatter = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "Unknown date"
    : formatter.format(date);
}

export function NotificationList({
  items,
  busyId,
  onMarkRead,
}: NotificationListProps) {
  return (
    <ul className="notification-list">
      {items.map((notification) => (
        <li
          key={notification.id}
          className={
            notification.read_at === null
              ? "notification-card notification-card-unread"
              : "notification-card"
          }
        >
          <div className="notification-heading">
            <h2>{notification.title}</h2>

            <span>
              {notification.read_at === null ? "Unread" : "Read"}
            </span>
          </div>

          <p className="notification-body">{notification.body}</p>

          <p>
            <time dateTime={notification.created_at}>
              {formatDate(notification.created_at)}
            </time>
          </p>

          <div className="notification-actions">
            {notification.application_id != null && (
              <Link to={`/applications/${notification.application_id}`}>
                View application
              </Link>
            )}

            {notification.read_at === null && (
              <button
                type="button"
                disabled={busyId !== null}
                onClick={() => onMarkRead(notification.id)}
              >
                {busyId === notification.id
                  ? "Saving..."
                  : "Mark as read"}
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}